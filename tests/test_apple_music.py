from src.connectors.apple_music import parse_library
from src.profile_builder import map_genre, build_plan_from_library
from src.recommender import load_songs

SAMPLE = "data/sample_library.xml"


def test_parse_library_reads_tracks_and_play_counts():
    tracks = parse_library(SAMPLE)
    assert len(tracks) == 8
    first = tracks[0]
    assert set(first.keys()) == {"title", "artist", "genre", "play_count"}
    assert all(isinstance(t["play_count"], int) for t in tracks)


def test_genre_mapping_normalizes_apple_labels():
    assert map_genre("Hip-Hop/Rap") == "hip hop"
    assert map_genre("R&B/Soul") == "r&b"
    assert map_genre("Alternative") == "indie pop"
    assert map_genre("Pop") == "pop"
    assert map_genre("Polka") is None  # unknown genre maps to nothing


def test_profile_is_built_from_most_played_genre():
    songs = load_songs("data/songs.csv")
    tracks = parse_library(SAMPLE)
    plan = build_plan_from_library(tracks, songs)
    # Pop has by far the most plays in the sample library.
    assert plan.profile.favorite_genre == "pop"
    assert plan.recognized is True
    # Target energy should be inferred from the catalog, not left at default.
    assert plan.energy_specified is True


def test_empty_library_falls_back_gracefully():
    songs = load_songs("data/songs.csv")
    plan = build_plan_from_library([], songs)
    assert plan.recognized is False
    assert plan.profile.favorite_genre == ""
