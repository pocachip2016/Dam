# Step M.1: mediax-content-mirror

> GitHub: 미생성 | Milestone: dev-asset-content-mapping

## 읽어야 할 파일
- `db/migrations/006_content_mapping.sql` — content_catalog_mirror, sync_cursors 스키마
- `ingest/mediax_mirror.py` — 이 step에서 신설

## 작업
mediaX `/api/meta-core/contents/since?ts=N` 를 cursor 기반으로 폴링해 `content_catalog_mirror` 에 UPSERT 하는 oneshot 워커.

**환경변수**:
- `DAM_DSN` (필수), `MEDIAX_URL` (기본: http://localhost:8000), `DAM_MEDIAX_LIMIT` (기본: 500), `DAM_MEDIAX_TIMEOUT` (기본: 30)

**cursor 진행 방식**: 성공한 페이지마다 `sync_cursors.content_mirror_next_ts` 를 mediaX 응답의 `next_ts` 로 atomic 갱신. 실패 시 이전 cursor 유지 → 다음 cron 회차에 자동 재시도.

**cron 등록** (verify 후 수동):
```bash
*/30 * * * * cd /home/ktalpha/Work/Dam && \
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
  .venv/bin/python -m ingest.mediax_mirror >> dam_data/mediax_sync.log 2>&1
```

**사전 조건**: mediaX backend 가 `/api/meta-core/contents/since` 를 노출 중이어야 함. 노출 안 될 경우 mediaX 컨테이너 재시작 필요.

## Acceptance Criteria
```bash
bash .claude/verify.sh M.1
```

## 금지사항
- 데몬/무한 루프 구현 금지 — cron이 호출하는 oneshot 방식 유지.
- changefeed webhook 수신 엔드포인트 추가 금지 — 별도 step.
