"""B.2.0.2 — tmdb-image ingest 엔드포인트 테스트. DB/네트워크 mock 기반."""
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

import api.ingest_tmdb_image as mod
from api.auth import User

app = FastAPI()
app.include_router(mod.router)
app.dependency_overrides[mod._admin.dependency] = lambda: User(id=1, username="test", role="admin")
client = TestClient(app, raise_server_exceptions=False)

_FAKE_DEST = Path("/fake/ab/deadbeef.jpg")

_REQ = {
    "entity_type": "movie",
    "tmdb_id": 496243,
    "image_kind": "poster",
    "file_path": "/abc123.jpg",
    "image_url": "https://image.tmdb.org/t/p/w500/abc123.jpg",
}


def _mock_conn():
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


class TestIngestNew:
    def test_ingest_ok(self):
        conn, cur = _mock_conn()
        cur.fetchone.side_effect = [
            None,        # 1. 자연키 기준 기존 로그 없음
            {"id": 1},   # 2. 신규 로그 INSERT RETURNING id
            None,        # 5. sha256 매칭 asset 없음
            {"id": 42},  # 6. 신규 asset INSERT RETURNING id
        ]
        with patch("api.ingest_tmdb_image.psycopg.connect", return_value=conn), \
             patch("api.ingest_tmdb_image._download", return_value=b"fake-image-bytes"), \
             patch("api.ingest_tmdb_image._save_file", return_value=_FAKE_DEST):
            r = client.post("/api/ingest/tmdb-image", json=_REQ)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["asset_id"] == 42


class TestIngestIdempotent:
    def test_skip_when_already_downloaded(self):
        conn, cur = _mock_conn()
        cur.fetchone.side_effect = [
            {"id": 1, "status": "downloaded", "asset_id": 42},  # 자연키 기존 로그 = downloaded
        ]
        with patch("api.ingest_tmdb_image.psycopg.connect", return_value=conn):
            r = client.post("/api/ingest/tmdb-image", json=_REQ)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "skipped"
        assert body["asset_id"] == 42


class TestCasDedup:
    def test_same_sha256_reuses_asset(self):
        """entity_type/tmdb_id가 달라도 sha256이 같으면 같은 asset_id를 재사용한다."""
        conn, cur = _mock_conn()
        cur.fetchone.side_effect = [
            None,        # 1. 이 자연키로는 기존 로그 없음
            {"id": 2},   # 2. 신규 로그 INSERT RETURNING id
            {"id": 42},  # 5. sha256 매칭 asset 이미 존재 -> 재사용
        ]
        req2 = {**_REQ, "tmdb_id": 999888, "file_path": "/xyz999.jpg"}
        with patch("api.ingest_tmdb_image.psycopg.connect", return_value=conn), \
             patch("api.ingest_tmdb_image._download", return_value=b"fake-image-bytes"), \
             patch("api.ingest_tmdb_image._save_file", return_value=_FAKE_DEST):
            r = client.post("/api/ingest/tmdb-image", json=req2)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["asset_id"] == 42


class TestValidation:
    def test_invalid_entity_type_400(self):
        r = client.post("/api/ingest/tmdb-image", json={**_REQ, "entity_type": "invalid"})
        assert r.status_code == 400

    def test_invalid_image_kind_400(self):
        r = client.post("/api/ingest/tmdb-image", json={**_REQ, "image_kind": "invalid"})
        assert r.status_code == 400


class TestStatus:
    def test_status_not_found_404(self):
        conn, cur = _mock_conn()
        cur.fetchone.return_value = None
        with patch("api.ingest_tmdb_image.psycopg.connect", return_value=conn):
            r = client.get("/api/ingest/tmdb-image/status", params={
                "entity_type": "movie", "tmdb_id": 1, "image_kind": "poster", "file_path": "/x.jpg",
            })
        assert r.status_code == 404
