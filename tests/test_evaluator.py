from src.recommender import UserProfile
from src.evaluator import evaluate, confidence_for, FULL_MATCH_SCORE, CONFIDENCE_THRESHOLD

CATALOG_GENRES = {"pop", "lofi", "rock"}


def test_confidence_is_fraction_of_perfect_match():
    profile = UserProfile("pop", "happy", 0.8, False)
    assert confidence_for(profile, FULL_MATCH_SCORE) == 1.0
    assert confidence_for(profile, 0.0) == 0.0
    assert confidence_for(profile, FULL_MATCH_SCORE / 2) == 0.5


def test_flags_unsorted_results():
    profile = UserProfile("pop", "happy", 0.8, False)
    # deliberately out of order
    recs = [
        ({"genre": "pop"}, 1.0, ""),
        ({"genre": "pop"}, 4.0, ""),
    ]
    result = evaluate(profile, recs, k=2, catalog_genres=CATALOG_GENRES)
    assert result.passed is False
    assert any("sorted" in issue for issue in result.issues)


def test_passes_a_clean_high_confidence_result():
    profile = UserProfile("pop", "happy", 0.8, False)
    recs = [
        ({"genre": "pop"}, 4.5, ""),
        ({"genre": "pop"}, 3.0, ""),
    ]
    result = evaluate(profile, recs, k=2, catalog_genres=CATALOG_GENRES)
    assert result.passed is True
    assert result.confidence >= CONFIDENCE_THRESHOLD


def test_empty_recommendations_fail():
    profile = UserProfile("pop", "happy", 0.8, False)
    result = evaluate(profile, [], k=5, catalog_genres=CATALOG_GENRES)
    assert result.passed is False
    assert result.confidence == 0.0
