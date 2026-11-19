"""
Evaluator: the agent's self-check and confidence scoring.

After the recommender produces a ranked list, the evaluator inspects it
and answers two questions:

1. Does the result satisfy some basic correctness guardrails (right
   number of items, actually sorted, genre honored when the catalog can
   honor it)?
2. How confident should we be in it (a 0-1 score derived from how close
   the top pick is to a theoretically perfect match)?

Both the agent (to decide whether to retry) and the reliability harness
(to grade a run) call into here, so "good enough" means the same thing
everywhere.
"""

from typing import List, Tuple, Dict
from dataclasses import dataclass, field

from src.recommender import (
    UserProfile,
    GENRE_WEIGHT,
    MOOD_WEIGHT,
    ENERGY_WEIGHT,
    ACOUSTIC_WEIGHT,
)

# A run is considered confident when the top pick clears this fraction of
# the best score it could possibly have earned for this profile.
CONFIDENCE_THRESHOLD = 0.60


@dataclass
class EvalResult:
    passed: bool
    confidence: float
    issues: List[str] = field(default_factory=list)


def max_possible_score(profile: UserProfile) -> float:
    """The highest score any song could earn for this profile.

    Genre + mood + a perfect energy match, plus the acoustic bonus only
    if the user asked for acoustic. Used to normalize confidence so it is
    comparable across different profiles.
    """
    best = ENERGY_WEIGHT  # a perfect energy match is always reachable
    if profile.favorite_genre:
        best += GENRE_WEIGHT
    if profile.favorite_mood:
        best += MOOD_WEIGHT
    if profile.likes_acoustic:
        best += ACOUSTIC_WEIGHT
    return best


def confidence_for(profile: UserProfile, top_score: float) -> float:
    """Normalize the top score into a 0-1 confidence value."""
    ceiling = max_possible_score(profile)
    if ceiling <= 0:
        return 0.0
    return round(max(0.0, min(1.0, top_score / ceiling)), 2)


def evaluate(
    profile: UserProfile,
    recommendations: List[Tuple[Dict, float, str]],
    k: int,
    catalog_genres: set,
) -> EvalResult:
    """Run guardrail checks and compute confidence for one recommendation set.

    ``recommendations`` is the list of (song, score, explanation) tuples
    from recommend_songs. ``catalog_genres`` is the set of genres that
    actually exist in the catalog, so we only penalize a missing genre
    match when the catalog could have produced one.
    """
    issues: List[str] = []

    if not recommendations:
        return EvalResult(passed=False, confidence=0.0, issues=["no recommendations returned"])

    # Guardrail 1: returned the requested number of items (unless the
    # catalog is smaller than k).
    if len(recommendations) != k:
        issues.append(f"expected {k} results, got {len(recommendations)}")

    # Guardrail 2: results are actually sorted by score, descending.
    scores = [score for _, score, _ in recommendations]
    if scores != sorted(scores, reverse=True):
        issues.append("results are not sorted by score")

    # Guardrail 3: if the user named a genre the catalog contains, the top
    # pick should actually be in that genre.
    top_song = recommendations[0][0]
    if profile.favorite_genre and profile.favorite_genre in catalog_genres:
        if top_song["genre"] != profile.favorite_genre:
            issues.append(
                f"top pick genre '{top_song['genre']}' does not match "
                f"requested '{profile.favorite_genre}'"
            )

    # Confidence from the top score.
    confidence = confidence_for(profile, recommendations[0][1])
    if confidence < CONFIDENCE_THRESHOLD:
        issues.append(
            f"low confidence {confidence:.2f} (< {CONFIDENCE_THRESHOLD:.2f})"
        )

    passed = len(issues) == 0
    return EvalResult(passed=passed, confidence=confidence, issues=issues)
