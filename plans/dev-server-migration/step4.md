# Step 4: infra-up

> GitHub: 미생성 | Milestone: server-migration

## 읽어야 할 파일
- `docker-compose.yml` (step 3 수정 후)
- `db/migrations/001_init.sql`, `db/migrations/002_embeddings.sql`
- `plans/dev-server-migration/index.json`

## 작업
- `docker compose up -d`
- `docker compose ps` 로 healthy 대기 (최대 60초)
- 마이그레이션 자동 적용 확인 — 빈 볼륨이면 `/docker-entrypoint-initdb.d:ro` 의 SQL 자동 실행
- `psql -h localhost -p 15432 -U dam -d dam` 으로 검증:
  - 6+ 테이블: assets, asset_storage, asset_tags, scan_runs, embeddings, asset_edges
  - `v_source_files` 뷰
  - `vector` 확장 활성

## Acceptance Criteria
```bash
bash .claude/verify.sh 1.4
```

## 금지사항
- 마이그레이션 SQL 을 수동으로 재적용하지 마라. 이유: 빈 볼륨에서만 자동 실행됨; 수동 재적용은 중복/에러 야기.
- `docker compose down -v` (볼륨 삭제) 는 사용자 승인 없이 실행하지 마라. 이유: 데이터 손실 위험.
