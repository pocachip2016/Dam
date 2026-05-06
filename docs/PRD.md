# PRD: Dam — 80TB 디자인 에셋 AI 관리 시스템

## 목표

디자인파트 NAS (DESIGNFS1, 81 TB / 208만 파일) 를 AI 기반으로 인덱싱·검색·관리하는 DAM 시스템 구축. 파일을 이동하지 않고 논리 레이어로 관리한다 (원본 NAS 불변 원칙).

## 사용자

디자인파트 (3인). 주요 페인포인트: 과거 유사 시안 탐색 어려움, 중복 파일 난립.

## 핵심 기능

1. 파일 메타데이터 수집 및 DB 적재 (경로·크기·mtime·해시)
2. 썸네일 생성 (PSD·JPG·PNG·AI·FONT 등 확장자별 워커)
3. CLIP 임베딩 + pgvector HNSW 유사도 검색
4. FastAPI 기반 검색 UI (파일명·확장자·유사도)
5. SHA-256 중복 탐지 + 시각적 유사 중복 플래그

## 5-Phase 계획

| Phase | 목적 | 규모 | 상태 |
|---|---|---|---|
| 1 | 메타데이터 DB + 전량 선적재 | 208만 행 / 81 TB | ✅ 완료 |
| 2 | 로컬 PoC 파이프라인 검증 (썸네일·CLIP·검색API·웹UI) | 161k / 58 GB 샘플 | ✅ 완료 |
| 3 | MVP 기능 완성 (poc_sample 기반, 로컬 only) | 161k / 58 GB | 대기 |
| 4 | 운영 준비 (auth · monitoring · backup · deployment) | — | 대기 |
| 5 | 실데이터 이관 (단방향 push, NAS 직결 X) | ~1.48 TB | 대기 |

### Phase 3 — MVP 기능 (`plans/dev-mvp-features/`, 7 step)
1. archive-and-branch — 이전 SMB-기반 plan archive, `feature/mvp-features`
2. metadata-and-tokens — EXIF/IPTC/XMP + folder/filename tokens + year/role hint
3. hash-dedup — sha256, asset_edges duplicate, dedup-report
4. search-filters — `/search_text` 에 ext/folder/role/year/size/mtime 필터
5. tags-collections — 다중 사용자 태그·컬렉션 (X-User placeholder, Phase 4 auth 가 교체)
6. ocr-pipeline — PaddleOCR ko+en, ocr_text + tsvector, 검색 통합
7. wrap

### Phase 4 — 운영 준비 (`plans/dev-ops-readiness/`, 6 step)
1. branch-and-scaffold — `deploy/` 디렉토리, dev/prod compose 분리
2. auth — users/api_tokens, role (viewer/editor/admin), Bearer token, login UI
3. monitoring — worker_runs, `/admin/workers`, 대시보드, `/health`
4. backup — pg_dump 일일, 썸네일 rsync 주간, 복원 리허설
5. deployment — docker-compose.prod, systemd, Caddy, deployment.md
6. wrap

### Phase 5 — 실데이터 이관 (outline, 별도 plan 작성 시점에 결정)
- **방식**: 단방향 push (DESIGNFS1 → DAM 서버 로컬 mirror dir). DAM 은 NAS 직접 마운트 X.
- **수단 후보**: rsync (Linux scheduled) 또는 robocopy (Windows scheduled task) — 인프라/보안 협의 결과로 결정.
- **DAM 동작 변화 없음**: 기존 워커가 로컬 path 만 보면 됨 (Phase 3 에서 이미 로컬 path 기준).
- **트리거**: Phase 4 완료 + 인프라/스토리지 결정 후 별도 `plans/dev-real-data-migration/` 작성.

### 향후 step 후보 (Phase 미할당)
- **title-entity** — `titles / seasons / episodes / asset_titles` 스키마 + 자동 링킹 (folder_tokens · filename_tokens · ocr_text · tags 신호 결합). Phase 3 의 신호 컬럼이 입력.
- **tmdb-iptv-sync** — TMDB / KT 내부 작품 마스터 연동, 외부 ID 채움. title-entity 다음.
- **psd-thumbnail** — psd-tools / ImageMagick fallback (ADR-005). poc_sample 은 PSD 제외라 Phase 5 실데이터 도입 시 처리.
- **inotify 증분** — 로컬 mirror dir 변경 감지 (Phase 5 인프라 결정 후).

## 데이터 규모 (확정)

| 확장자 | 파일 수 | 용량 |
|---|---|---|
| .psd | 416,159 | 74 TB |
| .psb | 3,065 | 5.7 TB |
| .jpg | 808,904 | 566 GB |
| .zip | 24,523 | 412 GB |
| .png | 467,410 | 96 GB |
| .ai | 6,024 | 86 GB |
| **합계** | **2,080,379** | **81.22 TB** |

PSD 비중 98.1% → PSD 제외 복사 대상 1.48 TB (Phase 3 실제 이관량).

## 불문율

- 원본 NAS (DESIGNFS1) 는 읽기 전용 마운트, 절대 수정 금지.
- 자동 삭제 금지 — 중복 탐지 결과는 플래그 후 사람이 판단.
- DB 손실 시 원본에서 재복구 가능하도록 ingest 스크립트 상시 유지.
