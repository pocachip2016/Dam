"""Folder tree API tests."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import api.search as search_mod
from api.auth import User

_viewer = User(id=1, username="testviewer", role="viewer")

def _override_viewer():
    return _viewer

app = search_mod.app
app.dependency_overrides[search_mod._folders_user.dependency] = _override_viewer

client = TestClient(app, raise_server_exceptions=False)


def _mock_folder_rows():
    """Mock result from folders query."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__  = MagicMock(return_value=False)
    cur = MagicMock()
    cur.__enter__  = MagicMock(return_value=cur)
    cur.__exit__   = MagicMock(return_value=False)

    row1 = MagicMock()
    row1.__getitem__ = lambda self, k: {
        'top_folder': '디자인파트',
        'sub_folder': '포스터',
        'count': 20
    }[k]

    row2 = MagicMock()
    row2.__getitem__ = lambda self, k: {
        'top_folder': '디자인파트',
        'sub_folder': '썸네일',
        'count': 15
    }[k]

    row3 = MagicMock()
    row3.__getitem__ = lambda self, k: {
        'top_folder': '영상파트',
        'sub_folder': '2024',
        'count': 30
    }[k]

    cur.fetchall.return_value = [row1, row2, row3]
    conn.cursor.return_value = cur
    return conn


class TestListFolders:
    def test_list_folders_200(self):
        with patch("api.search.get_conn", return_value=_mock_folder_rows()):
            r = client.get("/folders?realm=poc_sample")
            assert r.status_code == 200
            data = r.json()
            assert data['realm'] == 'poc_sample'
            assert 'nodes' in data
            assert len(data['nodes']) == 2  # 2 top folders

            # Check structure
            top_nodes = {n['name']: n for n in data['nodes']}
            assert '디자인파트' in top_nodes
            assert '영상파트' in top_nodes

            design = top_nodes['디자인파트']
            assert design['count'] == 35  # 20 + 15
            assert len(design['children']) == 2

            video = top_nodes['영상파트']
            assert video['count'] == 30
            assert len(video['children']) == 1
            assert video['children'][0]['name'] == '2024'

    def test_list_folders_no_auth(self):
        app.dependency_overrides.clear()
        r = client.get("/folders")
        assert r.status_code in [401, 403, 500]  # 인증 실패


class TestSearchWithSubFolder:
    def test_search_with_sub_filter(self):
        """GET /search?top=<val>&sub=<val> 필터 동작 확인."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__  = MagicMock(return_value=False)
        cur = MagicMock()
        cur.__enter__  = MagicMock(return_value=cur)
        cur.__exit__   = MagicMock(return_value=False)

        asset_row = MagicMock()
        asset_row.__getitem__ = lambda self, k: {
            'id': 1,
            'filename': 'test.jpg',
            'primary_ext': '.jpg',
            'size_bytes': 1024,
            'width': 1920,
            'height': 1080,
            'top_folder': '디자인파트',
            'sub_folder': '포스터',
            'physical_path': '/mnt/d/poc/디자인파트/포스터/test.jpg',
            'realm': 'poc_sample'
        }[k]

        cur.fetchall.return_value = [asset_row]
        cur.fetchone.return_value = (1,)  # count
        conn.cursor.return_value = cur

        app.dependency_overrides[search_mod._user_viewer.dependency] = _override_viewer
        with patch("api.search.get_conn", return_value=conn):
            r = client.get("/search?realm=poc_sample&top=디자인파트&sub=포스터")
            assert r.status_code == 200
            data = r.json()
            assert 'results' in data
            # Query should have passed both filters
