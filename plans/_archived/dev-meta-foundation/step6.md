# Step M.6: mapping-admin

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `plans/dev-meta-foundation/step0.md` — asset_title_links 스키마 (confirmed, threshold_used)
- `plans/dev-meta-foundation/step2.md` — AssetMapper.threshold 구조
- `plans/dev-meta-foundation/index.json` → decisions.mapping_threshold_adjustable

## 배경
threshold 0.85는 기본값이지만 컨텐츠 유형·촬영 스타일에 따라 조정이 필요할 수 있다. 관리자가 런타임에 threshold를 변경하고, 오매핑을 수동으로 수정할 수 있는 API가 필요하다.

## 작업

### 신규 엔드포인트 모음 (`api/admin.py` 또는 `api/main.py` 내)

#### threshold 조회/변경
```
GET  /admin/mapping/threshold
→ { "current": 0.85, "default": 0.85 }

POST /admin/mapping/threshold
body: { "threshold": 0.80 }
→ { "updated": 0.80, "affected_future_runs": true }
```
- 변경값은 Redis에 저장 (재기동 시 환경변수 기본값으로 복귀)
- 변경 이력 로그 출력

#### 매핑 수동 수정
```
POST /admin/mapping/confirm
body: { "asset_id": 123, "title_id": 456 }
→ asset_title_links.confirmed = TRUE

DELETE /admin/mapping
body: { "asset_id": 123, "title_id": 456 }
→ asset_title_links 해당 행 삭제

POST /admin/mapping/manual
body: { "asset_id": 123, "title_id": 456, "note": "수동 확인" }
→ INSERT with match_method='manual', confidence=1.0, confirmed=TRUE
```

#### 재매핑 트리거
```
POST /admin/mapping/remap
body: { "threshold": 0.80, "realm": "poc_sample" }
→ 새 threshold로 AssetMapper 재실행 (백그라운드)
→ { "job_id": "...", "status": "started" }
```

### 인증
이 step에서는 단순 API Key 헤더로 제한 (`X-Admin-Key: <env:DAM_ADMIN_KEY>`). JWT/OAuth는 Phase 4 auth step에서.

### 웹 UI 최소 추가
`/admin` 페이지: threshold 슬라이더(0.5~1.0) + 현재값 표시 + 저장 버튼

## Acceptance Criteria
```bash
bash .claude/verify.sh M.6
```
- `POST /admin/mapping/threshold` `{"threshold": 0.80}` → 200
- `GET /admin/mapping/threshold` → `{"current": 0.80, ...}`
- `POST /admin/mapping/confirm` → asset_title_links.confirmed = TRUE 확인
- 인증 없이 호출 시 401 반환

## 금지사항
- admin 엔드포인트를 인증 없이 노출 금지
- threshold 범위 [0.5, 1.0] 밖의 값 수용 금지
- 재매핑 중 기존 confirmed=TRUE 매핑 덮어쓰기 금지
