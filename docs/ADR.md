# Architecture Decision Records: Dam

## 철학

원본을 건드리지 않는다. DB 손실은 재복구 가능해야 한다. 과도한 자동화는 금물.

---

### ADR-001: 원본 NAS 불변 원칙 (Dual Store)

**결정**: DAM 은 NAS 를 읽기 전용으로만 스캔·인덱싱한다. 파일 이동·수정·삭제 금지.

**이유**: PSD/INDD 의 Placed Smart Object·링크 파일은 경로 변경 시 전부 Missing Link 오류 발생. 80 TB 물리 이동은 다운타임·데이터 손실·링크 깨짐의 삼중 리스크. DAM 장애가 발생해도 기존 워크플로우 100% 유지.

**결과**: Source Realm (원본, 불변) + Derivative Realm (AI 생성물) 으로 이원화. `asset_edges` 그래프로 관계 표현.

---

### ADR-002: PostgreSQL + pgvector (Qdrant 대신)

**결정**: 벡터 스토어로 Qdrant/Milvus 대신 pgvector + HNSW 인덱스 사용.

**이유**: 현재 파일 수 208만 개 (pgvector HNSW 500만 이하 기준 충분). 별도 벡터 DB 운영 없이 단일 PostgreSQL 로 메타데이터 + 벡터를 함께 관리 → 운영 단순화. 파일 수가 500만 초과 시 Qdrant 분리 재검토.

**조건**: HNSW `m=16, ef_construction=64` 기본값. 정밀도 부족 시 파라미터 튜닝.

---

### ADR-003: CLIP 모델 선택 (RTX 4060 8GB VRAM 제약)

**결정**: 1차 PoC 는 `openai/clip-vit-base-patch32` (ViT-B/32, ~150MB, VRAM ~1GB). 품질 부족 시 ViT-L/14 (~4GB VRAM) 로 업그레이드.

**이유**: VRAM 8GB 제약. ViT-B/32 로 파이프라인 검증 후 품질 실측치 기반으로 결정. 한글 텍스트 쿼리 필요 시 `clip-ViT-B-32-multilingual-v1` 검토.

---

### ADR-004: n8n 역할 축소 (오케스트레이션 전용)

**결정**: n8n 은 트리거·상태관리·알림만 담당. AI 인퍼런스(CLIP·OCR)는 별도 Python 워커로 분리.

**이유**: n8n 내부에서 CLIP 실행 시 워커 재시작/큐 관리/재시도 제어가 번거로움. 대량 배치에서 n8n 실행 로그·큐 폭주. 현재 Phase 에서는 n8n 미사용, 추후 증분 인덱싱 도입 시 재검토.

---

### ADR-005: 썸네일 생성 — Pillow 우선, ImageMagick 보조

**결정**: Pillow 로 JPG/PNG/TIFF 처리. PSD 는 `psd-tools` 시도, 실패 시 ImageMagick 폴백.

**이유**: Pillow 는 Python 네이티브라 의존성 단순. PSD 대형 파일(레이어 수천 개)은 수십 초 소요 허용. INDD 는 썸네일 추출 불가 — PDF export 의무화로 대응.

---

### ADR-006: 서버 이관 전략 (2026-04-27)

**결정**: 이전 PC (pocachip, GTX 750) 데이터는 복구 불가. 새 PC (ktalpha, RTX 4060, DESIGNFS1 SMB 직결) 에서 NAS 재적재로 Phase 2 환경 재구축.

**이유**: 이전 PC 접근 불가. 새 PC 가 DESIGNFS1 에 직접 연결되어 인벤토리·poc_sample 재적재 가능. RTX 4060 으로 이후 CLIP 워커 실행 가능.

---

### ADR-007: CLIP 모델 운영 전략 (2026-05-05)

**결정**: API 기본 모델은 `clip-vit-b32` (open_clip). `cn-clip-vitb16` 은 `?model=cn-clip-vitb16` 파라미터로 선택 가능하게 유지. 단일 기본 모델 운영.

**이유**: `docs/clip-comparison.md` 실측 결과 요약:
- 영문 쿼리 시맨틱 이해: open_clip 명확 우위 ("kid character" 등)
- 한국어 쿼리: 두 모델 모두 그래픽 디자인 도메인에서 유의미한 차이 없음
- Latency: p50 동일, p95 cn_clip 9ms 낮으나 실용 차이 미미
- 이미지-이미지 유사도: 두 모델 overlap 12% → 서로 다른 시각 공간, 교체 불가

**보류**: 한국어 정확도 개선은 도메인 특화 fine-tuning 또는 multilingual CLIP 모델 도입으로 Phase 3+에서 재검토. 현재는 open_clip을 기본으로 사용자가 cn_clip을 선택적으로 활용.
