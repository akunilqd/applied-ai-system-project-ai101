import json
import os

from dotenv import load_dotenv
from google import genai

from src.recommender import validate_preferences
from src.rag import retrieve_and_rank


load_dotenv(override=True)


PREFERENCES_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "genre": {
            "type": "STRING",
            "enum": [
                "blues", "classical", "country", "electronic",
                "experimental", "folk", "hip-hop", "jazz",
                "metal", "pop", "rock", "soul-rnb", "unknown",
            ],
        },
        "mood": {
            "type": "STRING",
            "enum": [
                "calm", "happy", "sad",
                "intense", "neutral", "unknown",
            ],
        },
        "energy": {
            "type": "NUMBER",
            "minimum": 0,
            "maximum": 1,
        },
        "tempo_bpm": {
            "type": "NUMBER",
            "minimum": 20,
            "maximum": 300,
        },
        "valence": {
            "type": "NUMBER",
            "minimum": 0,
            "maximum": 1,
        },
        "danceability": {
            "type": "NUMBER",
            "minimum": 0,
            "maximum": 1,
        },
        "acousticness": {
            "type": "NUMBER",
            "minimum": 0,
            "maximum": 1,
        },
        "retrieval_query": {
            "type": "STRING",
        },
        "keywords": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "maxItems": 8,
        },
    },
    "required": [
        "genre",
        "mood",
        "energy",
        "retrieval_query",
        "keywords",
    ],
}


SCORING_FIELDS = {
    "genre",
    "mood",
    "energy",
    "tempo_bpm",
    "valence",
    "danceability",
    "acousticness",
}


class GeminiQueryParser:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    def parse(self, query):
        prompt = f"""
You extract music preferences from a user's request.

Return JSON with:
- genre
- mood
- energy
- tempo_bpm
- valence
- danceability
- acousticness
- retrieval_query
- keywords

Rules:
- energy, valence, danceability, acousticness are between 0.0 and 1.0.
- tempo_bpm is between 20 and 300.
- Use "unknown" when genre or mood is unclear.
- Only provide numeric values when the user's request gives enough evidence.
- retrieval_query must be a concise expanded search query.
- keywords must contain useful music-search terms.
- Do not recommend specific songs.

User request:
{query}
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": 0.0,
                "response_mime_type": "application/json",
                "response_schema": PREFERENCES_SCHEMA,
            },
        )

        raw = json.loads(response.text)

        retrieval_query = raw.get("retrieval_query", query)
        keywords = raw.get("keywords", [])

        scoring_input = {
            field: raw[field]
            for field in SCORING_FIELDS
            if field in raw and raw[field] is not None
        }

        preferences = validate_preferences(scoring_input)

        return {
            "preferences": preferences,
            "retrieval_query": retrieval_query,
            "keywords": keywords,
        }


def recommend_from_query(query, songs, k=5, candidate_k=50):
    parser = GeminiQueryParser()
    parsed = parser.parse(query)

    expanded_query = " ".join([
        parsed["retrieval_query"],
        *parsed["keywords"],
    ])

    results = retrieve_and_rank(
        expanded_query,
        parsed["preferences"],
        songs,
        k=k,
        candidate_k=candidate_k,
    )

    return parsed, results
