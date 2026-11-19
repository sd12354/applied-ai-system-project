"""
Agent: the plan -> act -> check -> revise loop.

This is the agentic core that ties the Module 3 recommender together with
the new planner and evaluator into something that can take a messy
natural-language request and *check its own work* before answering.

The loop:

  1. PLAN   - parse the request into a profile (planner).
  2. ACT    - produce recommendations (Module 3 recommender).
  3. CHECK  - run guardrails + confidence scoring (evaluator).
  4. REVISE - if the check fails, adjust the plan and try again.

Every step is logged, there is a hard cap on retries, and unrecognized or
empty input is handled gracefully rather than crashing. Those are the
reliability guardrails the final-project rubric asks for.
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
import logging
import os
import statistics

from src.recommender import load_songs, recommend_songs, UserProfile
from src.planner import parse_request, Plan
from src.evaluator import evaluate, EvalResult, CONFIDENCE_THRESHOLD
from src.connectors.apple_music import parse_library
from src.profile_builder import build_plan_from_library

MAX_ATTEMPTS = 3
DEFAULT_CSV = "data/songs.csv"
LOG_PATH = os.path.join("logs", "agent.log")


def _get_logger() -> logging.Logger:
    """A logger that writes a structured trail to logs/agent.log."""
    logger = logging.getLogger("vibefinder.agent")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(handler)
    return logger


def _profile_to_prefs(profile: UserProfile) -> Dict:
    """Convert a UserProfile into the dict the functional recommender uses."""
    return {
        "genre": profile.favorite_genre or None,
        "mood": profile.favorite_mood or None,
        "energy": profile.target_energy,
        "likes_acoustic": profile.likes_acoustic,
    }


@dataclass
class AgentResult:
    query: str
    profile: UserProfile
    recommendations: List[Tuple[Dict, float, str]]
    confidence: float
    passed: bool
    attempts: int
    trace: List[str] = field(default_factory=list)
    advisory: Optional[str] = None


class RecommenderAgent:
    """Runs the self-checking recommendation loop over a song catalog."""

    def __init__(self, csv_path: str = DEFAULT_CSV):
        self.songs = load_songs(csv_path)
        self.catalog_genres = {s["genre"] for s in self.songs}
        self.log = _get_logger()

    def _recenter_energy(self, profile: UserProfile) -> Optional[float]:
        """Return the mean energy of songs matching the profile's genre/mood.

        Used to revise the plan when the user named a genre or mood but gave
        no energy cue: aiming at the real energy of those songs improves the
        match instead of guessing the default 0.6.
        """
        matches = [
            s for s in self.songs
            if (not profile.favorite_genre or s["genre"] == profile.favorite_genre)
            and (not profile.favorite_mood or s["mood"] == profile.favorite_mood)
        ]
        if not matches:
            return None
        return round(statistics.mean(s["energy"] for s in matches), 2)

    def run(self, query: str, k: int = 5) -> AgentResult:
        """Answer a natural-language request."""
        plan: Plan = parse_request(query, k)
        return self._execute(plan, label=query)

    def run_from_library(self, xml_path: str, k: int = 5) -> AgentResult:
        """Answer from an Apple Music library export instead of a text query.

        Parses the exported Library.xml, infers a taste profile from the
        listening history, then runs the same self-checking loop.
        """
        tracks = parse_library(xml_path)
        plan: Plan = build_plan_from_library(tracks, self.songs, k)
        label = f"Apple Music library ({os.path.basename(xml_path)}, {len(tracks)} tracks)"
        return self._execute(plan, label=label)

    def _execute(self, plan: Plan, label: str) -> AgentResult:
        query = label
        k = plan.k
        profile = plan.profile
        self.log.info("PLAN   source=%r -> profile=%s", label, profile)
        for line in plan.trace:
            self.log.info("PLAN     %s", line)

        trace: List[str] = ["Plan: " + "; ".join(plan.trace)]
        advisory: Optional[str] = None
        if not plan.recognized:
            advisory = (
                "Your request was vague, so this is a neutral mix. "
                "Name a genre, mood, or vibe (e.g. 'chill lofi for studying') for a sharper match."
            )
            trace.append("Guardrail: request not recognized -> neutral profile, advisory attached.")

        result: Optional[EvalResult] = None
        recs: List[Tuple[Dict, float, str]] = []
        attempts = 0
        tried_recenter = False

        while attempts < MAX_ATTEMPTS:
            attempts += 1
            prefs = _profile_to_prefs(profile)
            recs = recommend_songs(prefs, self.songs, k)
            result = evaluate(profile, recs, k, self.catalog_genres)
            self.log.info(
                "ACT    attempt=%d top=%r score=%.2f conf=%.2f passed=%s issues=%s",
                attempts,
                recs[0][0]["title"] if recs else None,
                recs[0][1] if recs else 0.0,
                result.confidence,
                result.passed,
                result.issues,
            )
            trace.append(
                f"Attempt {attempts}: top='{recs[0][0]['title']}' "
                f"confidence={result.confidence:.2f} passed={result.passed}"
                + (f" issues={result.issues}" if result.issues else "")
            )

            if result.passed:
                break

            # REVISE: try to fix the plan and loop again.
            if (not plan.energy_specified) and (not tried_recenter) \
                    and (profile.favorite_genre or profile.favorite_mood):
                new_energy = self._recenter_energy(profile)
                tried_recenter = True
                if new_energy is not None and abs(new_energy - profile.target_energy) > 0.01:
                    old = profile.target_energy
                    profile = UserProfile(
                        favorite_genre=profile.favorite_genre,
                        favorite_mood=profile.favorite_mood,
                        target_energy=new_energy,
                        likes_acoustic=profile.likes_acoustic,
                    )
                    msg = (f"Revise: no energy given, re-centering target energy "
                           f"{old} -> {new_energy} (mean of matching songs) and retrying.")
                    self.log.info("REVISE   %s", msg)
                    trace.append(msg)
                    continue

            # Nothing left to revise: stop and report best effort honestly.
            self.log.info("STOP   no further revision available; returning best effort.")
            trace.append("Revise: no further revision available -> returning best effort.")
            break

        confidence = result.confidence if result else 0.0
        if result and not result.passed and advisory is None:
            advisory = (
                f"Low confidence ({confidence:.2f}). Best effort shown — "
                "try naming a genre and mood, or a different vibe."
            )

        self.log.info(
            "DONE   query=%r attempts=%d confidence=%.2f passed=%s",
            query, attempts, confidence, result.passed if result else False,
        )
        return AgentResult(
            query=query,
            profile=profile,
            recommendations=recs,
            confidence=confidence,
            passed=result.passed if result else False,
            attempts=attempts,
            trace=trace,
            advisory=advisory,
        )
