"""M.6 admin write API 테스트 — DB mock 기반."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from api.admin import router

app = FastAPI()
app.include_router(router)
client = TestClient(app, raise_server_exceptions=False)


def _mock_conn(rowcount=1):
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__  = MagicMock(return_value=False)
    cur = MagicMock()
    cur.__enter__  = MagicMock(return_value=cur)
    cur.__exit__   = MagicMock(return_value=False)
    cur.rowcount   = rowcount
    conn.cursor.return_value = cur
    return conn


class TestConfirmClassification:
    def test_confirm_200(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/classification/1/content/confirm")
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_invalid_class_400(self):
        r = client.post("/api/admin/classification/1/INVALID/confirm")
        assert r.status_code == 400

    def test_not_found_404(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn(rowcount=0)):
            r = client.post("/api/admin/classification/9999/content/confirm")
        assert r.status_code == 404


class TestRejectClassification:
    def test_reject_200(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/classification/1/promotion/reject")
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"


class TestReclass:
    def test_reclass_200(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/classification/reclass", json={
                "asset_id": 1, "old_class": "draft", "new_class": "content"
            })
        assert r.status_code == 200
        assert r.json()["new_class"] == "content"

    def test_invalid_new_class(self):
        r = client.post("/api/admin/classification/reclass", json={
            "asset_id": 1, "old_class": "draft", "new_class": "INVALID"
        })
        assert r.status_code == 400


class TestConfirmMapping:
    def test_confirm_200(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/mapping/1/100/confirm")
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_not_found_404(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn(rowcount=0)):
            r = client.post("/api/admin/mapping/9999/9999/confirm")
        assert r.status_code == 404


class TestRejectMapping:
    def test_reject_200(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/mapping/1/100/reject")
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"


class TestAddMapping:
    def test_add_200(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/mapping/add", json={"asset_id": 1, "content_id": 5})
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_add_manual_method(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/mapping/add", json={"asset_id": 2, "content_id": 10, "note": "큐레이터 확인"})
        assert r.status_code == 200


class TestBulkClassify:
    def test_bulk_200(self):
        with patch("api.admin.psycopg.connect", return_value=_mock_conn()):
            r = client.post("/api/admin/unclassified/bulk-classify", json={
                "asset_ids": [1, 2, 3], "cls": "promotion"
            })
        assert r.status_code == 200
        assert r.json()["classified"] == 3

    def test_invalid_class_400(self):
        r = client.post("/api/admin/unclassified/bulk-classify", json={
            "asset_ids": [1], "cls": "INVALID"
        })
        assert r.status_code == 400

    def test_empty_ids_400(self):
        r = client.post("/api/admin/unclassified/bulk-classify", json={
            "asset_ids": [], "cls": "content"
        })
        assert r.status_code == 400

    def test_too_many_ids_400(self):
        r = client.post("/api/admin/unclassified/bulk-classify", json={
            "asset_ids": list(range(501)), "cls": "content"
        })
        assert r.status_code == 400
