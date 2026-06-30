# Dam FE 정보구조(IA) 설계서

> 상태: 설계 확정 (2026-06-30). 구현 전 합의용 문서.
> 결정 요약: Dam FE를 **mediaX와 동일 스택(Next.js + Tailwind + @workspace/ui)**으로 재구축,
> `mediaX-CMS/apps/dam`에 배치, 좌측 사이드바, mediaX OKLch 토큰(KT Red) 채택.

---

## 1. 배경 & 목표

"FE 개선"은 단순 버그 수정이 아니라 **제품 전체 화면 설계**다. 목표 비전:

| 도메인 | 설명 |
|--------|------|
| A 파이프라인 | 디자인 파일 자동 등록·삭제·검색 |
| B 트리 뷰 | 파일시스템 트리 구조 탐색 + 파일 선택 |
| C 플랫폼 맵핑 | 영화/테마 ↔ 서비스플랫폼(지니TV 등) 이미지 자동/수동 맵핑 |
| D 맵핑 검색 | 맵핑 결과로 검색 |
| E 통합 뷰 | 오버레이·배경·포스터·프로모션·폰트를 한 화면에 통합 표시 |

### 확정 결정
1. **풀스택 채택** — 기존 plain HTML(`index.html`/`admin.html`/admin 4템플릿)은 레거시 → Next.js로 대체.
2. **좌측 사이드바** — mediaX와 동일 레이아웃·icon 축소 모드.
3. **저장소 배치** — `mediaX/mediaX-CMS/apps/dam/`. `@workspace/ui` 직접 import. Dam 백엔드(FastAPI :18000)는 REST 호출.
4. **디자인 토큰** — mediaX OKLch 팔레트. primary = KT Red `oklch(0.5 0.22 25)`, 사이드바 `oklch(0.22 0.03 255)`.

---

## 2. 현실 데이터 근거 (Dam DB)

- `asset_classifications.class`: content 130,554 / branding 36,578 / unclassified 15,873 / promotion 12,663 / seasonal 2,150 / pricing 995 / ui_service 238 / composition 76. **전부 status=candidate**(검수 전).
- `content_catalog_mirror`(mediaX 콘텐츠 미러): content_id·title·content_type·production_year·status — **플랫폼 필드 없음**.
- `asset_content_link`: asset↔content(confidence·method·status) — **플랫폼 차원 없음**.
- `assets.role` 미사용.

### 핵심 갭
1. **이미지 타입 체계 불일치** — 희망 타입(포스터/배경/오버레이/프로모션/폰트) ↔ 현 `class` 9종 불일치. 표시용 매핑 레이어 필요.
2. **플랫폼 차원 부재** — 지니TV 등 맵핑할 스키마 없음. 도메인 C는 Dam BE에 `platforms` 신규 설계.
3. **교차 저장소 + CORS** — FE(mediaX repo) ↔ BE(Dam repo) 분리. Dam FastAPI에 `CORSMiddleware`로 Next.js origin 허용 필요. API base URL 환경변수화.
4. **이미지 인증** — `<img>`는 Bearer 헤더 불가 → `/thumb` 무인증 공개 권고(§7).

---

## 3. 앱 배치 & 인프라

```
mediaX/mediaX-CMS/
  apps/
    web/            (기존 mediaX CMS)
    dam/            ← 신규 Dam FE (Next.js 16, App Router)
      app/(main)/   레이아웃 셸
      config/nav.ts Dam 전용 네비 정의
  packages/ui/      ← @workspace/ui 공유 (Sidebar/Button/Badge/Card/Sheet...)

Dam repo (/home/ktalpha/Work/Dam)
  api/  FastAPI :18000  ← CORS 허용 + /thumb 공개 (FE가 호출)
```

- Dam FastAPI: `CORSMiddleware`(allow Next.js dev/prod origin), `/thumb` 공개 전환.
- FE 환경변수: `NEXT_PUBLIC_DAM_API=http://localhost:18000`.

---

## 4. 글로벌 좌측 사이드바 (mediaX SidebarGroup + Lucide 아이콘 패턴)

```
Dam
├─ 🔍 검색          /search        (Search)      CLIP+필터, index.html 대체
├─ 🗂️ 브라우즈      /browse        (FolderTree)  파일시스템 트리 뷰 (B)
├─ 🎬 콘텐츠         /content       (Film)        목록 → 상세 통합뷰 (D·E)
│   └─ 상세         /content/[id]                통합 이미지 갤러리 (E)
├─ 🔗 맵핑          /mapping       (Link2)       영화·테마 ↔ asset, 플랫폼 (C)
├─ 🏷️ 분류 검수      /review        (Tags)        asset_classifications, 4템플릿 통합
├─ ⚙️ 파이프라인     /pipeline      (Workflow)    자동 등록·삭제 상태 (A)
└─ 📊 모니터링       /monitoring    (Activity)    worker_runs, admin.html 대체
```

활성/축소/Badge·`Ctrl+B` 단축키 = mediaX `apps/web/components/layout/sidebar.tsx` 동일 패턴.

---

## 5. 도메인 ↔ 화면 ↔ 데이터

| 도메인 | 화면 | 테이블 | 비고 |
|--------|------|--------|------|
| A 파이프라인 | /pipeline | scan_runs, worker_runs, poster_ingest_log | mediaX StageNode 색상코딩 차용 |
| B 트리뷰 | /browse | assets(path,folder) | BE 폴더 집계 API 신규 |
| C 플랫폼맵핑 | /mapping | asset_content_link, **platforms(신규)** | Dam BE 스키마 추가 |
| D 맵핑검색 | /content, /search | asset_content_link, content_catalog_mirror | 기존 검색 확장 |
| E 통합뷰 | /content/[id] | asset_classifications, asset_content_link | 핵심 화면 |

---

## 6. 통합 콘텐츠 뷰 (E) — 제품의 심장

```
┌──────────────────────────────────────────────────────────────┐
│ ← 콘텐츠 목록   기생충 (2019) #1234   플랫폼:[지니TV ▾]       │
│                                        [자동맵핑][수동추가]   │
├──────────────────────────────────────────────────────────────┤
│ 타입:[포스터 12][배경 8][오버레이 5][프로모션 7][폰트 3]      │ ← Badge 탭
├──────────────────────────────────────────────────────────────┤
│ 포스터 (12)                                    [전체보기 ▾]   │
│  ▢ ▢ ▢ ▢ ▢ ▢   썸네일 클릭=상세 / 체크=맵핑확정             │
│ 배경/아트 (8)   ▢ ▢ ▢ ▢                                      │
│ 오버레이 (5)    체커보드 배경 미리보기  ▢ ▢ ▢                │
│ 폰트 (3)        샘플 텍스트 렌더  Aa Aa Aa                    │
└──────────────────────────────────────────────────────────────┘
```

### 이미지 타입 매핑 권고 (갭 1 해소)
`class` 9종을 사용자 5표시타입으로 묶는 **표시용 매핑 레이어**:

| 표시 타입 | 출처 class | 비고 |
|-----------|-----------|------|
| 포스터 | content (키비주얼) | 가장 많음(13만) |
| 배경/아트 | composition, branding | 배경 이미지 |
| 오버레이 | (신규 sub_class) | 배경투명 PNG, 체커보드 미리보기 |
| 프로모션 | promotion | 기존 일치 |
| 폰트 | (신규) | 샘플 렌더 미리보기 |

> status=candidate 다수 → 통합뷰에서 검수(확정/반려) 흐름 연계.

---

## 7. 인증 / 이미지 ADR

- **메타·검색·맵핑 API** → Bearer 토큰. fetch 래퍼가 자동 첨부, 401 → 로그인 리다이렉트.
- **`/thumb` 이미지** → **무인증 공개** (img 태그는 헤더 첨부 불가). 썸네일 민감도 낮음. 최소 변경.
  - 대안: 쿠키 세션(BE 인증 구조 변경) / `?token=`(로그 노출 위험) — 채택 안 함.
- Next.js 토큰 저장: Context + localStorage 또는 쿠키. mediaX 인증 방식과 정합 여부는 P0에서 확인.

---

## 8. 컴포넌트 전략 (@workspace/ui 재사용)

| 용도 | mediaX 컴포넌트 |
|------|----------------|
| 셸 | SidebarProvider / AppSidebar / SidebarInset + Header |
| 액션 | Button (CVA variants) |
| 상태 | Badge (default/secondary/destructive/outline) |
| 카드 | Card |
| 드로어 | Sheet (상세·맵핑 패널) |
| 모달 | Dialog / AlertDialog (alert() 대체) |
| 로딩 | Skeleton |
| 테이블 | data-table 패턴 (분류·맵핑 검수) |

Dam 고유 신규: `asset-card`(썸네일+유사도+선택), `asset-grid`(auto-fill), `type-section`(E), `tree-node`(B).

---

## 9. 파이프라인 (A) — mediaX StageNode 정합

- Dam 파이프라인 단계를 mediaX 색상코딩(blue→violet→amber→orange→green) 카드 strip으로 표현.
- Dam 단계: scan → ingest → thumbnail → embed(clip) → classify → map → publish.
- `worker_runs` 진행률/heartbeat를 카드 건수·상태 dot로 시각화.

---

## 10. 단계적 구현 로드맵

IA 승인 후 각 P를 독립 stepwise 플랜으로 상세화한다.

```
P0 스캐폴드  apps/dam 생성 + 셸(좌측 사이드바/헤더/테마) + auth(로그인+fetch 래퍼)
             + Dam BE CORS + /thumb 공개 + API base 설정       → 기능 부활
P1 검색      /search (CLIP+필터+상세 Sheet)                     → index.html 대체
P2 통합뷰    /content 목록 + /content/[id] (E)
P3 검수      /review(분류) + /mapping(맵핑)                     → admin 4템플릿 대체
P4 확장      /browse 트리(B) + /pipeline(A, StageNode)
P5 플랫폼    Dam BE platforms 스키마 + /mapping 플랫폼 차원(C)
```

- 첫 구현 후보 = **P0 스캐폴드**(셸+인증+CORS, 기능 부활).
- 교차 저장소이므로 P0 착수 시 mediaX repo·CLAUDE.md·git 전략 정리 동반.

---

## 11. 결정 기록 (2026-06-30 확정)

- **썸네일 `/thumb` 인증** → **보류**. P0 스캐폴드 착수 시점에 재결정 (§7). 일단 현 require_user 구조 유지.
- **오버레이·폰트 타입 분류** → **신규 `sub_class` 추가**. `asset_classifications.sub_class`에 `overlay`/`font` 값 추가하고 분류 워커가 채움. DB 기반 일관 처리 (§6). P2/P3에서 워커·마이그레이션 동반.
- **git 전략** → **mediaX repo 통합**. `apps/dam` 커밋은 mediaX 저장소에. Dam 저장소는 백엔드만 유지. 모노레포 표준.
- **인증 공유** → **독립 로그인**. Dam 자체 `users`/`api_tokens` 유지, 별도 로그인. SSO 미채택 (§7).
