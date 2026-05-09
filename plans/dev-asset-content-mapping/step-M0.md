# Step M.0: mapping-schema

> GitHub: 미생성 | Milestone: dev-asset-content-mapping

## 읽어야 할 파일
- `db/migrations/001_init.sql` — assets, asset_edges, trigger_set_updated_at
- `db/migrations/006_content_mapping.sql` — 이 step에서 신설

## 작업
mediaX ↔ Dam 연결 파이프라인의 기반 테이블 3개 신설.

**content_catalog_mirror** — mediaX ContentSummary 로컬 미러.
M.1 폴링 워커가 `/contents/since?ts=...` 로 UPSERT.

**asset_content_link** — Dam 자산 ↔ mediaX 콘텐츠 매핑.
- `confidence`: CLIP/OCR 유사도 (임계값 0.85)
- `method`: clip_similarity | ocr_text | manual | web_search
- `status`: candidate | confirmed | rejected

**sync_cursors** — 폴링 커서 저장. 시드: `('content_mirror_next_ts', '0')`.

마이그레이션 적용:
```bash
docker exec dam_postgres psql -U dam -d dam \
  -f /migrations/006_content_mapping.sql
```

## Acceptance Criteria
```bash
bash .claude/verify.sh M.0
```

## 금지사항
- asset_content_link에 application-level cascade 로직 추가 금지. DB FK ON DELETE CASCADE로 충분.
- confidence CHECK 제약 추가 금지 — 0~1 범위 강제는 M.2 워커에서 처리.
