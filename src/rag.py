"""TF-IDF song retrieval for the FMA catalog."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .recommender import recommend_songs
from .reliability import check_output


def song_to_document(song):
    """Convert one song into searchable text."""
    fields = [
        song.get("title", ""),
        song.get("artist", ""),
        song.get("genre", ""),
        song.get("tags", ""),
        song.get("mood", ""),
    ]
    return " ".join(str(value) for value in fields if value)


class SongRetriever:
    """Retrieve songs by TF-IDF and cosine similarity."""

    def __init__(self, songs):
        if not songs:
            raise ValueError("song catalog is empty")

        self.songs = list(songs)
        self.documents = [song_to_document(song) for song in self.songs]

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )
        self.matrix = self.vectorizer.fit_transform(self.documents)

    def retrieve(self, query, k=20):
        """Return the k most textually similar songs."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be nonempty text")
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("k must be a positive integer")

        query_vector = self.vectorizer.transform([query.strip()])
        scores = cosine_similarity(query_vector, self.matrix)[0]

        indexes = sorted(
            range(len(self.songs)),
            key=lambda index: (-scores[index], self.songs[index]["id"]),
        )

        results = []
        for index in indexes:
            similarity = float(scores[index])
            if similarity <= 0:
                continue

            results.append({
                "song": self.songs[index],
                "similarity": similarity,
            })

            if len(results) == k:
                break

        return results


def retrieve_songs(query, songs, k=20):
    """Convenience function for one retrieval operation."""
    return SongRetriever(songs).retrieve(query, k=k)

def retrieve_and_rank(
    query,
    preferences,
    songs,
    k=5,
    candidate_k=20,
    mode="genre-first",
    artist_penalty=0.75,
):
    """Retrieve candidates first, then rank them with the main scorer."""
    retrieved = SongRetriever(songs).retrieve(query, k=candidate_k)

    candidate_songs = [
        item["song"]
        for item in retrieved
    ]

    results = recommend_songs(
        preferences,
        candidate_songs,
        k=k,
        mode=mode,
        artist_penalty=artist_penalty,
    )
    check_output(
        results,
        candidate_songs,
        preferences,
        k,
        mode,
        artist_penalty,
    )
    return results
