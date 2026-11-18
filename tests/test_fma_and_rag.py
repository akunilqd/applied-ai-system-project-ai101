import pytest

from scripts.prepare_fma import filter_tracks, is_music_track
from src.rag import SongRetriever, song_to_document


def make_song(song_id, title, genre="folk", tags="acoustic calm"):
    return {
        "id": song_id,
        "title": title,
        "artist": "Test Artist",
        "genre": genre,
        "tags": tags,
        "mood": "calm",
    }


def test_spoken_word_filter_removes_obvious_non_music_records():
    assert not is_music_track(make_song(1, "Interview with the artist", "spoken"))
    assert not is_music_track(make_song(2, "Late Night Podcast", "folk"))
    assert is_music_track(make_song(3, "Speechless", "rock"))


def test_filter_tracks_applies_filter_genre_limit_and_id_order():
    rows = [
        make_song(4, "Folk Song", "folk"),
        make_song(2, "Interview 1", "folk"),
        make_song(3, "Rock Song", "rock"),
        make_song(1, "Folk Song 2", "folk"),
    ]

    filtered = filter_tracks(rows, allowed_genres=["folk"], limit=1)

    assert [row["id"] for row in filtered] == [1]


def test_song_to_document_combines_searchable_fields():
    song = make_song(1, "Acoustic Morning", tags="guitar study")

    document = song_to_document(song)

    assert document == "Acoustic Morning Test Artist folk guitar study calm"


def test_retriever_returns_relevant_positive_results_in_deterministic_order():
    songs = [
        make_song(2, "Acoustic Study", tags="guitar focus"),
        make_song(1, "Acoustic Study", tags="guitar focus"),
        make_song(3, "Heavy Distortion", genre="metal", tags="loud guitar"),
    ]

    results = SongRetriever(songs).retrieve("calm acoustic guitar for studying", k=2)

    assert len(results) == 2
    assert [result["song"]["id"] for result in results] == [1, 2]
    assert all(result["similarity"] > 0 for result in results)


@pytest.mark.parametrize("query", ["", "   ", None])
def test_retriever_rejects_empty_query(query):
    with pytest.raises(ValueError, match="query"):
        SongRetriever([make_song(1, "A Song")]).retrieve(query)
