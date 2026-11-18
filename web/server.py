"""Small standard-library web server for the VibeFinder prototype."""

from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
CATALOG = ROOT / "data" / "songs_fma.csv"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.query_parser import recommend_from_query
from src.recommender import load_songs


SONGS = load_songs(CATALOG)


class VibeFinderHandler(SimpleHTTPRequestHandler):
    """Serve the browser app and the recommendation endpoint."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/recommend":
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            query = payload.get("query", "")
            if not isinstance(query, str) or not query.strip():
                self._send_json({"error": "Please enter a music request."}, status=400)
                return

            parsed, results = recommend_from_query(
                query.strip(),
                SONGS,
                k=6,
                candidate_k=50,
            )
            self._send_json({
                "preferences": parsed["preferences"],
                "retrieval_query": parsed["retrieval_query"],
                "keywords": parsed["keywords"],
                "results": [
                    {
                        "id": song["id"],
                        "title": song["title"],
                        "artist": song["artist"],
                        "genre": song["genre"],
                        "score": round(score, 3),
                        "reason": reason,
                        "audio_url": song.get("audio_url"),
                    }
                    for song, score, reason in results
                ],
            })
        except json.JSONDecodeError:
            self._send_json({"error": "Request body must be valid JSON."}, status=400)
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), VibeFinderHandler)
    print("VibeFinder is running at http://127.0.0.1:8000")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping VibeFinder.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
