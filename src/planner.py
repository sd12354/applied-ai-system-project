"""
Planner: turn a natural-language request into a structured UserProfile.

This is the "reasoning" front end of the agent. A user types something
like "upbeat pop for a workout" or "calm acoustic study music", and the
planner parses that free text into the same `UserProfile` the Module 3
recommender already understands (favorite_genre, favorite_mood,
target_energy, likes_acoustic).

It is deliberately rule-based rather than an LLM call, so the whole
system is reproducible and free to run — anyone with Python can get the
same result, with no API key. The trade-off (it only understands the
vocabulary below) is documented in the model card.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.recommender import UserProfile


# ---------------------------------------------------------------------------
# Vocabulary: the words the planner knows, mapped onto catalog values.
# Keys are matched as substrings of the lowercased query.
# ---------------------------------------------------------------------------
GENRE_WORDS = {
    "pop": "pop",
    "lofi": "lofi", "lo-fi": "lofi", "lo fi": "lofi",
    "rock": "rock",
    "ambient": "ambient",
    "jazz": "jazz",
    "synthwave": "synthwave", "synth": "synthwave", "retrowave": "synthwave",
    "indie": "indie pop",
    "hip hop": "hip hop", "hiphop": "hip hop", "rap": "hip hop",
    "r&b": "r&b", "rnb": "r&b", "soul": "r&b",
    "country": "country",
    "metal": "metal",
}

MOOD_WORDS = {
    "happy": "happy", "upbeat": "happy", "cheerful": "happy", "feel good": "happy",
    "chill": "chill", "mellow": "chill", "lofi": "chill",
    "intense": "intense", "aggressive": "intense", "hard": "intense", "hype": "intense",
    "relaxed": "relaxed", "relaxing": "relaxed", "calm": "relaxed", "peaceful": "relaxed",
    "focus": "focused", "focused": "focused", "study": "focused", "concentrate": "focused",
    "moody": "moody", "dark": "moody", "melancholy": "moody",
    "romantic": "romantic", "love": "romantic", "date": "romantic",
}

# Context words that imply an energy level, checked in order.
ENERGY_WORDS = [
    (("workout", "gym", "run", "running", "party", "hype", "high energy", "pump"), 0.9),
    (("drive", "driving", "roadtrip", "road trip", "moderate", "medium"), 0.6),
    (("study", "focus", "sleep", "calm", "relax", "chill", "low energy", "quiet", "mellow"), 0.3),
]

ACOUSTIC_WORDS = ("acoustic", "unplugged", "organic", "stripped")

DEFAULT_ENERGY = 0.6  # used when no energy cue is found


@dataclass
class Plan:
    """What the planner decided, plus a trace of how it got there."""
    profile: UserProfile
    k: int
    trace: List[str]
    recognized: bool  # False when the query gave the planner nothing to work with


def _first_match(query: str, mapping) -> Optional[str]:
    """Return the mapped value of the first vocabulary word found in query."""
    for word, value in mapping.items():
        if word in query:
            return value
    return None


def parse_request(query: str, k: int = 5) -> Plan:
    """Parse a free-text request into a Plan.

    Always returns a usable Plan — even for empty or unrecognized input it
    falls back to a neutral profile and flags ``recognized = False`` so the
    agent can react (this is one of the system's guardrails).
    """
    text = (query or "").lower().strip()
    trace: List[str] = []

    genre = _first_match(text, GENRE_WORDS)
    if genre:
        trace.append(f"genre -> '{genre}' (matched a genre word)")

    mood = _first_match(text, MOOD_WORDS)
    if mood:
        trace.append(f"mood -> '{mood}' (matched a mood word)")

    energy = None
    for words, value in ENERGY_WORDS:
        if any(w in text for w in words):
            energy = value
            trace.append(f"energy -> {value} (context word implied this)")
            break
    if energy is None:
        energy = DEFAULT_ENERGY
        trace.append(f"energy -> {energy} (default, no energy cue found)")

    likes_acoustic = any(w in text for w in ACOUSTIC_WORDS)
    if likes_acoustic:
        trace.append("likes_acoustic -> True (asked for acoustic)")

    recognized = bool(genre or mood or likes_acoustic or energy != DEFAULT_ENERGY)
    if not recognized:
        trace.append("no genre/mood/energy cues recognized -> using a neutral profile")

    profile = UserProfile(
        favorite_genre=genre or "",
        favorite_mood=mood or "",
        target_energy=energy,
        likes_acoustic=likes_acoustic,
    )
    return Plan(profile=profile, k=k, trace=trace, recognized=recognized)
