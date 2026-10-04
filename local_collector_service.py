"""Local-only bridge from the Collector browser to the validated ingestion pipeline."""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import duckdb

from run_ingestion_pipeline import ROOT, ingest_batch, source_key


MAX_BODY_BYTES = 5 * 1024 * 1024


class CollectorService:
    def __init__(self, db: Path, runtime: Path):
        self.db = db.expanduser().resolve()
        self.runtime = runtime.expanduser().resolve()
        self.incoming = self.runtime / "incoming"
        self.processed = self.runtime / "processed"
        self.rejected = self.runtime / "rejected"
        self.raw = self.runtime / "raw_collector"
        self.log = self.runtime / "collector_service_log.jsonl"
        self.lock = threading.Lock()
        for directory in (self.incoming, self.processed, self.rejected, self.raw):
            directory.mkdir(parents=True, exist_ok=True)

    def receive(self, payload: dict) -> dict:
        """Persist the exact received V1.1 document, then delegate all work to Phase 3."""
        with self.lock:
            try:
                digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
                try:
                    _, match_id = source_key(payload)
                    raw_name = f"collector_{match_id}.json"
                except Exception:
                    match_id = None
                    raw_name = f"collector_invalid_{digest}.json"
                raw_path = self.raw / raw_name
                if not raw_path.exists():
                    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                queued = self.incoming / raw_name
                queued.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                result = ingest_batch(self.db, self.incoming, self.processed, self.rejected, self.log)
                if match_id is None:
                    item = next((x for x in result["details"] if x.get("file") == raw_name), None)
                    return {"status":"error", "message": item.get("reason", "JSON inválido") if item else "JSON inválido", "duplicate":False}
                item = next((x for x in result["details"] if x.get("match_id") == match_id), None)
                return self._response(result, item, match_id)
            except Exception as exc:
                return {"status": "error", "message": str(exc), "duplicate": False}

    def _response(self, batch: dict, item: dict | None, match_id: str) -> dict:
        if item is None:
            return {"status": "error", "message": "El partido no llegó a importarse.", "duplicate": False}
        if item["status"] == "rejected":
            return {"status": "error", "message": item["reason"], "duplicate": False}
        ratings = expert = players = 0
        try:
            with duckdb.connect(str(self.db), read_only=True) as con:
                players = con.execute("select count(*) from player_match where match_id=?", [match_id]).fetchone()[0]
                ratings = con.execute("select count(*) from player_match_rating where match_id=?", [match_id]).fetchone()[0]
                expert = con.execute("select count(*) from decision_results where match_id=?", [match_id]).fetchone()[0]
        except Exception:
            pass
        duplicate = item["status"] == "duplicate"
        return {
            "status": "completed", "message": "Partido ya procesado correctamente." if duplicate else "Partido procesado correctamente.",
            "match_id": match_id, "players": players, "ratings_generated": ratings,
            "expert_rows": expert, "expert_status": "evidencia materializada" if expert else "sin evidencia materializada",
            "duplicate": duplicate, "gps": "GPS_NOT_AVAILABLE / EXPECTED_ABSTENTION",
            "raw_evidence": str(self.raw / f"collector_{match_id}.json"),
        }


def handler_for(service: CollectorService):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, value: dict) -> None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in {"/", "/collector", "/collector/"}:
                data = (ROOT / "collector" / "data_collector_futbol_v1.html").read_bytes()
                self.send_response(HTTPStatus.OK); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            elif path == "/health":
                self._json(HTTPStatus.OK, {"status": "ok", "db": str(service.db)})
            else:
                self._json(HTTPStatus.NOT_FOUND, {"status": "error", "message": "Ruta no disponible"})

        def do_POST(self):
            if urlparse(self.path).path != "/api/finalize-match":
                self._json(HTTPStatus.NOT_FOUND, {"status": "error", "message": "Ruta no disponible"}); return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY_BYTES: raise ValueError("El JSON debe tener entre 1 byte y 5 MB")
                payload = json.loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(payload, dict): raise ValueError("El cuerpo debe ser un objeto JSON")
                result = service.receive(payload)
                self._json(HTTPStatus.OK if result["status"] == "completed" else HTTPStatus.BAD_REQUEST, result)
            except Exception as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": str(exc), "duplicate": False})

        def log_message(self, format, *args):
            return
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Collector and local ingestion API on localhost only")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "football_performance.duckdb")
    parser.add_argument("--runtime", type=Path, default=ROOT / "data" / "local_collector_runtime")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    service = CollectorService(args.db, args.runtime)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(service))
    print(f"Collector local service: http://127.0.0.1:{args.port}/", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__":
    main()
