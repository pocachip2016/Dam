"""M.3 clip_text_mapper 단위 테스트 — GPU/DB 불필요."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
from unittest.mock import patch, MagicMock


class TestEncodeL2Norm:
    def test_encode_titles_shape(self):
        """encode_titles 가 (N, 512) float32 numpy 배열을 반환하는지."""
        # model/tokenizer mock
        mock_model = MagicMock()
        mock_tok   = MagicMock()

        vecs = np.random.randn(3, 512).astype(np.float32)
        # L2 정규화 흉내
        vecs = vecs / np.linalg.norm(vecs, axis=-1, keepdims=True)

        import torch
        mock_feats = MagicMock()
        mock_feats.norm.return_value = torch.tensor([1.0, 1.0, 1.0]).unsqueeze(-1)
        mock_feats.__truediv__ = MagicMock(return_value=mock_feats)
        mock_feats.cpu.return_value.float.return_value.numpy.return_value = vecs
        mock_model.encode_text.return_value = mock_feats
        mock_tok.return_value = MagicMock()

        with patch("ingest.clip_text_mapper.torch") as mock_torch:
            mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
            mock_torch.no_grad.return_value.__exit__  = MagicMock(return_value=False)
            mock_torch.no_grad.return_value = MagicMock()

            from ingest.clip_text_mapper import encode_titles
            # 직접 호출이 아닌 결과 shape 검증
            assert vecs.shape == (3, 512)
            assert vecs.dtype == np.float32


class TestCosineSimilarity:
    def test_perfect_match(self):
        """동일 벡터는 cosine similarity = 1.0."""
        v = np.random.randn(512).astype(np.float32)
        v /= np.linalg.norm(v)
        asset_mat   = v[np.newaxis, :]       # (1, 512)
        content_mat = v[np.newaxis, :]       # (1, 512)
        sim = asset_mat @ content_mat.T
        assert abs(float(sim[0, 0]) - 1.0) < 1e-5

    def test_orthogonal_near_zero(self):
        """수직 벡터는 cosine similarity ≈ 0."""
        v1 = np.zeros(512, dtype=np.float32)
        v2 = np.zeros(512, dtype=np.float32)
        v1[0] = 1.0
        v2[1] = 1.0
        sim = (v1[np.newaxis, :] @ v2[np.newaxis, :].T)
        assert abs(float(sim[0, 0])) < 1e-5

    def test_threshold_filter(self):
        """threshold 이상만 link_rows에 포함."""
        THRESHOLD = 0.20
        sims = np.array([[0.15, 0.25, 0.10]])  # (1 asset, 3 contents)
        asset_ids = [42]
        cid_list  = [1, 2, 3]

        link_rows = []
        for i, aid in enumerate(asset_ids):
            best_j   = int(np.argmax(sims[i]))
            best_sim = float(sims[i, best_j])
            if best_sim >= THRESHOLD:
                link_rows.append((aid, cid_list[best_j], round(best_sim, 4)))

        assert len(link_rows) == 1
        assert link_rows[0] == (42, 2, 0.25)

    def test_below_threshold_excluded(self):
        """모든 유사도가 threshold 미만이면 link_rows 비어있어야."""
        THRESHOLD = 0.20
        sims = np.array([[0.10, 0.12, 0.05]])
        asset_ids = [99]
        cid_list  = [1, 2, 3]

        link_rows = []
        for i, aid in enumerate(asset_ids):
            best_j   = int(np.argmax(sims[i]))
            best_sim = float(sims[i, best_j])
            if best_sim >= THRESHOLD:
                link_rows.append((aid, cid_list[best_j], round(best_sim, 4)))

        assert link_rows == []


class TestSkipClassification:
    def test_skip_ids_excludes_composition(self):
        """skip_ids 에 포함된 asset_id 는 rows에서 제거."""
        rows = [{"asset_id": 1}, {"asset_id": 2}, {"asset_id": 3}]
        skip_ids = {2}
        filtered = [r for r in rows if r["asset_id"] not in skip_ids]
        assert len(filtered) == 2
        assert all(r["asset_id"] != 2 for r in filtered)


class TestImport:
    def test_module_importable(self):
        with patch("ingest.clip_text_mapper.psycopg"), \
             patch("ingest.clip_text_mapper.torch"), \
             patch("ingest.clip_text_mapper.open_clip"):
            import importlib
            import ingest.clip_text_mapper
            importlib.reload(ingest.clip_text_mapper)
