# 아키텍처: Dam

## 디렉토리 구조

```
Dam/
├── api/
│   └── search.py          # FastAPI 검색 API (포트 18000)
├── ingest/
│   ├── ingest_inventory.py # UTF-16 인벤토리 파서 → DB 적재 (Phase 1)
│   ├── ingest_local.py     # 로컬 파일 스캔 → DB 적재 (Phase 2)
│   ├── thumbnail_worker.py # 썸네일 생성 워커
│   └── hash_worker.py      # SHA-256 중복 탐지 (Phase 3 직전 실행)
├── db/
│   └── migrations/
│       ├── 001_init.sql    # 초기 스키마 (assets, asset_storage, ...)
│       └── 002_embeddings.sql # vector(512) + HNSW 인덱스
├── scripts/
│   └── phase2_robocopy.ps1 # Windows robocopy 스크립트 (Phase 2 샘플 복사)
├── docs/                   # 설계 문서
├── plans/                  # task 별 step plan
└── docker-compose.yml      # PostgreSQL (pgvector) + Redis
```

## Dual Store + Unified Graph 아키텍처

핵심 결정: 파일을 이동하지 않고 논리 레이어로 관리.

```
Source Realm (원본 NAS, 읽기 전용)
  \\designfs.ktalpha.com\DESIGNFS\디자인파트\
    └── 원본 파일 (81 TB) — 경로 불변, 절대 수정 금지

Derivative Realm (AI 생성·분해물, hash-addressed)
  dam_cas/ (content-addressable storage)
    └── 썸네일, CLIP 임베딩, OCR 결과

Graph (asset_edges)
  duplicate_of / variant_of / derived_from / version_of
  → 물리 재구조화 없이 관계를 논리적으로 표현

Virtual Views
  asset_tags (다축 태그)
  views (저장 쿼리)
  v_source_files (원본 파일 통합 뷰)
```

## 스택

| 계층 | 기술 |
|---|---|
| DB | PostgreSQL 16 + pgvector (Docker) |
| 벡터 인덱스 | HNSW (002_embeddings.sql) |
| 캐시 | Redis 7 (Docker) |
| API | FastAPI + uvicorn (Python 3.12) |
| 임베딩 | CLIP ViT-B/32 (Phase 4, RTX 4060) |
| 썸네일 | Pillow (Python) |
| 환경 | WSL2 + Docker Desktop |

## 인프라 현황 (새 PC, 2026-04-27)

| 항목 | 값 |
|---|---|
| 사용자 | ktalpha |
| GPU | RTX 4060 8GB VRAM |
| OS | WSL2 Ubuntu (6.6.87) |
| Docker | 28.3.2 |
| Python | 3.12.3 |
| 코드 경로 | `/home/ktalpha/Work/Dam/` |
| DB 볼륨 | `/home/ktalpha/dam_data/` (ext4) |
| NAS 마운트 | `/mnt/designfs1/` (CIFS) |
| 포트 | PostgreSQL 15432 / Redis 16379 / API 18000 |

## 포트 격리 (타 프로젝트 충돌 방지)

PostgreSQL: **15432** (기본 5432 대신)
Redis: **16379**
FastAPI: **18000**
컨테이너 prefix: `dam_*`
Docker 네트워크: `dam_net`
