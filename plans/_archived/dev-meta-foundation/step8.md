# Step M.8: wrap

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `plans/dev-meta-foundation/index.json` — 전 step completed 여부 확인
- `CLAUDE.md`, `TODO.md`, `docs/ARCHITECTURE.md`

## 작업

### 1. 검증
- 전 step (M.0~M.7) index.json status 모두 `completed` 확인
- `bash .claude/verify.sh M.8` — 전체 회귀 테스트

### 2. 문서 갱신
- `docs/ARCHITECTURE.md` — content_titles, asset_title_links, web_search_cache 테이블 추가
- `docs/ADR.md` — 주요 결정 기록:
  - ADR-00X: KOBIS 우선 + TMDB 드라마 보완 (IPTV 보류)
  - ADR-00X: 매핑 threshold 0.85 기본, 런타임 조정 가능
  - ADR-00X: 웹서치 캐시 전략 (내부 DB → 캐시 → 쿼터)
- `CLAUDE.md` Active Work 섹션 업데이트

### 3. TODO.md 갱신
- Phase M(dev-meta-foundation) 항목 `[x]` 처리
- Phase 5(실데이터 이관) Next로 이동
- IPTV bulk 데이터 Later에 유지

### 4. 브랜치 머지
```bash
git checkout main
git merge --no-ff feature/meta-foundation
git branch -d feature/meta-foundation
```

### 5. 다음 단계 제안
- Phase 4 ops-readiness 잔여: auth·monitoring
- Phase 5: 실데이터 이관 (~1.48 TB) — 인프라 협의 선행
- IPTV bulk 데이터 — 데이터 확보 시 별도 plan

## Acceptance Criteria
```bash
bash .claude/verify.sh M.8
```
- `GET /stats` → 정상 응답
- `GET /search_meta?title=기생충` → 정상 응답
- `GET /admin/mapping/threshold` → 정상 응답
- 영상 자산 `/search_text` 검색 가능 확인

## 금지사항
- M.0~M.7 중 status가 `error`/`blocked`인 step 있으면 머지 금지
- CHANGELOG.md 없으면 작성 금지 (기존 Done 섹션 유지)
