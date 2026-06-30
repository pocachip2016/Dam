"""
M.2 mapping API 엔드포인트 200 응답 테스트.
DB 없이 mock으로 검증.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import api.mapping as _mapping_mod
from api.mapping import router
from api.auth import User

app = FastAPI()
app.include_router(router)

_admin_user = User(id=1, username="testadmin", role="admin")

def _override_admin():
    return _admin_user

app.dependency_overrides[_mapping_mod._admin.dependency] = _override_admin

client = TestClient(app, raise_server_exceptions=False)


def _mock_conn(rows_by_query: dict | None = None):
    """psycopg.connect context manager mock."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


class TestMappingStats:
    def test_stats_200(self):
        conn, cur = _mock_conn()
        cur.fetchall.side_effect = [
            [{"class": "content", "status": "candidate", "cnt": 95000}],
            [],
            [{"method": "filename", "cnt": 70000}],
        ]
        cur.fetchone.return_value = {"content_total": 95000, "mapped_total": 72000}
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/stats")
        assert r.status_code == 200
        data = r.json()
        assert "mapping_hit_rate" in data
        assert "class_distribution" in data


class TestByContent:
    def test_by_content_found(self):
        conn, cur = _mock_conn()
        cur.fetchall.return_value = [
            {"asset_id": 1, "filename": "poster.jpg", "folder_path": "/f/",
             "confidence": 0.95, "method": "filename", "status": "candidate"}
        ]
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/by-content/100")
        assert r.status_code == 200
        assert r.json()["content_id"] == 100

    def test_by_content_not_found(self):
        conn, cur = _mock_conn()
        cur.fetchall.return_value = []
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/by-content/9999")
        assert r.status_code == 404


class TestByClass:
    def test_by_class_content_200(self):
        conn, cur = _mock_conn()
        cur.fetchone.return_value = {"cnt": 95000}
        cur.fetchall.return_value = []
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/by-class/content")
        assert r.status_code == 200
        assert r.json()["class"] == "content"

    def test_by_class_invalid(self):
        r = client.get("/api/mapping/by-class/nonexistent")
        assert r.status_code == 400

    def test_by_class_with_status_filter(self):
        conn, cur = _mock_conn()
        cur.fetchone.return_value = {"cnt": 10}
        cur.fetchall.return_value = []
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/by-class/promotion?status=candidate")
        assert r.status_code == 200


class TestSearchContents:
    def test_search_with_q(self):
        conn, cur = _mock_conn()
        cur.fetchall.return_value = [
            {"content_id": 1, "title": "기생충", "original_title": "Parasite",
             "content_type": "movie", "production_year": 2019}
        ]
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/contents?q=기생충")
        assert r.status_code == 200
        data = r.json()
        assert data["q"] == "기생충"
        assert len(data["results"]) == 1
        assert data["results"][0]["content_id"] == 1

    def test_search_empty_result(self):
        conn, cur = _mock_conn()
        cur.fetchall.return_value = []
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/contents?q=없는제목XYZ")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_search_no_q_returns_list(self):
        conn, cur = _mock_conn()
        cur.fetchall.return_value = [
            {"content_id": 2, "title": "더 글로리", "original_title": None,
             "content_type": "series", "production_year": 2022}
        ]
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/contents?limit=1")
        assert r.status_code == 200
        assert r.json()["q"] is None
        assert len(r.json()["results"]) == 1

    def test_search_limit_out_of_range(self):
        r = client.get("/api/mapping/contents?limit=999")
        assert r.status_code == 422


class TestAssetDetail:
    def test_asset_detail_200(self):
        conn, cur = _mock_conn()
        cur.fetchall.side_effect = [
            [{"class": "content", "sub_class": None, "confidence": 0.95,
              "method": "filename", "matched_signal": "조선", "status": "candidate"}],
            [{"content_id": 1, "title": "조선 정신과", "confidence": 0.95,
              "method": "filename", "status": "candidate"}],
        ]
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/asset/42")
        assert r.status_code == 200
        assert r.json()["asset_id"] == 42

    def test_asset_detail_not_found(self):
        conn, cur = _mock_conn()
        cur.fetchall.side_effect = [[], []]
        with patch("api.mapping.psycopg.connect", return_value=conn):
            r = client.get("/api/mapping/asset/0")
        assert r.status_code == 404
