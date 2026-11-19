"""
Command-line entry point for the VibeFinder Agent.

Usage:
    python -m src.main "chill lofi for studying"   # answer one request
    python -m src.main                             # run a few sample requests

The agent parses your words into a taste profile, recommends songs,
checks its own work, and prints the result with a confidence score and a
short trace of what it did.
"""

import sys

from src.agent import RecommenderAgent

# Requests used when no query is passed on the command line.
SAMPLE_QUERIES = [
    "upbeat pop for a workout",
    "chill lofi for studying",
    "some jazz",
    "",  # shows the vague-input guardrail
]


def print_result(result) -> None:
    print("=" * 64)
    print(f'Request: "{result.query}"')
    print(
        f"  understood as: genre={result.profile.favorite_genre or '-'}, "
        f"mood={result.profile.favorite_mood or '-'}, "
        f"energy={result.profile.target_energy}, "
        f"acoustic={result.profile.likes_acoustic}"
    )
    print(f"  confidence: {result.confidence:.2f}   "
          f"attempts: {result.attempts}   passed checks: {result.passed}")
    if result.advisory:
        print(f"  note: {result.advisory}")
    print("-" * 64)
    for rank, (song, score, explanation) in enumerate(result.recommendations, start=1):
        print(f"{rank}. {song['title']} by {song['artist']}  (score {score:.2f})")
        print(f"   because: {explanation}")
    print("  trace:")
    for step in result.trace:
        print(f"    - {step}")
    print()


def main() -> None:
    agent = RecommenderAgent()
    queries = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else SAMPLE_QUERIES
    for query in queries:
        print_result(agent.run(query))


if __name__ == "__main__":
    main()
