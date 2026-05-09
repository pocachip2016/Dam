"""M.5 search_filters 신규 필터 단위 테스트."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.search_filters import build_filters


class TestClassFilter:
    def test_class_filter_adds_clause(self):
        clauses, params = build_filters({'class_filter': 'content', 'hide_draft': False})
        sql = ' '.join(clauses)
        assert 'asset_classifications' in sql
        assert params['class_filter'] == 'content'

    def test_class_filter_absent(self):
        clauses, params = build_filters({'hide_draft': False})
        sql = ' '.join(clauses)
        assert 'class_filter' not in params
        assert 'ac_cf' not in sql


class TestContentIdFilter:
    def test_content_id_adds_clause(self):
        clauses, params = build_filters({'content_id': 42, 'hide_draft': False})
        sql = ' '.join(clauses)
        assert 'asset_content_link' in sql
        assert params['content_id_f'] == 42

    def test_content_id_none_no_clause(self):
        clauses, params = build_filters({'content_id': None, 'hide_draft': False})
        sql = ' '.join(clauses)
        assert 'acl_cf' not in sql


class TestTopFolderFilter:
    def test_top_folder_adds_clause(self):
        clauses, params = build_filters({'top_folder': '장희진', 'hide_draft': False})
        sql = ' '.join(clauses)
        assert 's.top_folder' in sql
        assert params['top_folder'] == '장희진'

    def test_top_folder_empty_no_clause(self):
        clauses, params = build_filters({'top_folder': None, 'hide_draft': False})
        assert 'top_folder' not in params


class TestHideDraft:
    def test_hide_draft_true_adds_exclusion(self):
        clauses, params = build_filters({'hide_draft': True})
        sql = ' '.join(clauses)
        assert 'draft' in sql
        assert 'composition' in sql
        assert 'ac_hd' in sql

    def test_hide_draft_false_no_exclusion(self):
        clauses, params = build_filters({'hide_draft': False})
        sql = ' '.join(clauses)
        assert 'ac_hd' not in sql

    def test_hide_draft_default_true(self):
        # hide_draft 키 없으면 기본 True
        clauses, params = build_filters({})
        sql = ' '.join(clauses)
        assert 'ac_hd' in sql

    def test_hide_draft_with_class_filter_combined(self):
        # class=draft 명시 + hide_draft=True 가 공존 가능 (논리는 caller 책임)
        clauses, params = build_filters({'class_filter': 'draft', 'hide_draft': True})
        sql = ' '.join(clauses)
        assert 'ac_cf' in sql
        assert 'ac_hd' in sql


class TestCombinedFilters:
    def test_all_m5_filters_together(self):
        clauses, params = build_filters({
            'class_filter': 'content',
            'content_id': 10,
            'top_folder': '영화',
            'hide_draft': True,
        })
        assert params['class_filter'] == 'content'
        assert params['content_id_f'] == 10
        assert params['top_folder'] == '영화'
        sql = ' '.join(clauses)
        assert 'ac_hd' in sql
