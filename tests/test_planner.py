from src.planner import parse_request


def test_parses_genre_mood_and_energy_from_words():
    plan = parse_request("upbeat pop for a workout")
    assert plan.profile.favorite_genre == "pop"
    assert plan.profile.favorite_mood == "happy"
    assert plan.profile.target_energy == 0.9   # "workout" implies high energy
    assert plan.recognized


def test_detects_acoustic_preference():
    plan = parse_request("calm acoustic study music")
    assert plan.profile.likes_acoustic is True
    assert plan.profile.favorite_mood == "relaxed"


def test_empty_input_is_handled_not_crashed():
    plan = parse_request("")
    assert plan.recognized is False
    assert plan.profile.favorite_genre == ""     # neutral fallback
    assert plan.k == 5


def test_unrecognized_input_flagged():
    plan = parse_request("qwerty zxcvb")
    assert plan.recognized is False
