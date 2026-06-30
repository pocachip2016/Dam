# Plan: Dam FE P0 — 스캐폴드 (셸+인증+CORS)

> 설계 근거: `docs/fe-design/ia.md` (2026-06-30 확정)
> 저장소: Dam(BE) + mediaX/mediaX-CMS(FE)

## Context
IA 설계 승인 후 첫 구현 단계. `mediaX-CMS/apps/dam`에 셸+인증+CORS를 붙여
기존 plain HTML(index.html/admin.html)을 대체하는 최소 기능 부활 상태를 만든다.

참고 패턴: `mediaX-CMS/apps/web/` (동일 Turbo 모노레포)
- 루트 레이아웃: `app/layout.tsx` → ThemeProvider + globals.css
- 메인 레이아웃: `app/(main)/layout.tsx` → SidebarProvider + AppSidebar + SidebarInset + Header
- 사이드바: `components/layout/sidebar.tsx` (docsNav + Collapsible NavGroup)
- API client: `lib/api.ts` → NEXT_PUBLIC_API_URL + request<T>()
- Tailwind v4: postcss.config.mjs = `export { default } from "@workspace/ui/postcss.config"`

---

## Step P0.1 — Dam BE CORS + /thumb 공개

**파일**: `Dam/api/search.py`

1. `CORSMiddleware` 추가 (fastapi.middleware.cors)
   - `allow_origins`: `DAM_CORS_ORIGINS` env (기본 `http://localhost:3001`)
   - `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`
   - 반드시 `app.include_router()` **이전**에 `app.add_middleware()` 호출
2. `/thumb/{asset_id}` 에서 `Depends(require_user('viewer'))` 제거 → 무인증 공개

**verify**: `bash Dam/.claude/verify.sh P0.1`
- `/health` 200
- CORS preflight `Access-Control-Allow-Origin` 헤더 있음
- `/thumb/1` → 401 아닌 응답 (200 or 404)

---

## Step P0.2 — apps/dam 패키지 설정

**신규 파일** (`mediaX-CMS/apps/dam/`):
- `package.json` — name: `dam`, next@16.1.6, react@^19, @workspace/ui:*. dev script: `next dev -p 3001`
- `tsconfig.json` — extends `@workspace/typescript-config/nextjs.json`, paths: `@/*`→`./*`, `@workspace/ui/*`→`../../packages/ui/src/*`
- `next.config.mjs` — transpilePackages: ["@workspace/ui"]
- `postcss.config.mjs` — `export { default } from "@workspace/ui/postcss.config"`
- `.env.local.example` — `NEXT_PUBLIC_DAM_API=http://localhost:18000`

**verify**: `bash Dam/.claude/verify.sh P0.2`
- `node -e "require('.../apps/dam/package.json')"` JSON 파싱 성공
- tsconfig.json 존재

---

## Step P0.3 — 레이아웃 셸

**신규 파일** (`apps/dam/`):
- `app/layout.tsx` — Geist 폰트 + ThemeProvider + globals.css
- `app/page.tsx` — `redirect('/search')`
- `app/(main)/layout.tsx` — SidebarProvider + DamSidebar + SidebarInset + DamHeader
- `app/(main)/search/page.tsx` — placeholder h1
- `components/layout/dam-sidebar.tsx` — flat nav (Collapsible 없음):
  Search/FolderTree/Film/Link2/Tags/Workflow/Activity → /search~monitoring
  헤더 배지 "DA" (KT Red 배경)
- `components/layout/dam-header.tsx` — SidebarTrigger + 브레드크럼 + 다크모드 토글
- `config/nav.ts` — Dam nav 배열
- `lib/nav.ts` — getDamBreadcrumbs(pathname)

**verify**: `bash Dam/.claude/verify.sh P0.3`
- `cd .../apps/dam && npx tsc --noEmit` → 0 errors

---

## Step P0.4 — 인증

**신규 파일** (`apps/dam/`):
- `lib/dam-api.ts`:
  - `DAM_BASE = process.env.NEXT_PUBLIC_DAM_API ?? "http://localhost:18000"`
  - `damFetch<T>(path, init?)` — localStorage `dam_token` Bearer 자동 첨부, 401→`/login` redirect
  - `login(username, password)` → `POST /api/login` → `{token}`
- `lib/auth-context.tsx` — AuthContext + AuthProvider ("use client")
  - localStorage `dam_token` 관리
  - token 없으면 `/login` redirect
- `app/(main)/layout.tsx` — AuthProvider 추가
- `app/login/page.tsx` — username/password form + 로그인 Button
  성공 → `router.push('/search')`, 에러 표시

주의: localStorage → SSR 불가 → useEffect 안에서만 읽기

**verify**: `bash Dam/.claude/verify.sh P0.4`
- `npx tsc --noEmit` → 0 errors

---

## Step P0.5 — 통합 smoke

1. `npx tsc --noEmit` → exit 0
2. Dam BE `/health` 200
3. CORS preflight `Access-Control-Allow-Origin` 있음
4. `/thumb/1` → 401 아닌 응답

---

## 구현 순서

| step | 저장소 | 핵심 파일 | verify |
|------|--------|-----------|--------|
| P0.1 | Dam | api/search.py | CORS + /thumb 무인증 |
| P0.2 | mediaX-CMS | apps/dam 설정 4파일 | JSON/파일 존재 |
| P0.3 | mediaX-CMS | layout + sidebar + header | tsc 0 errors |
| P0.4 | mediaX-CMS | auth-context + dam-api + login | tsc 0 errors |
| P0.5 | both | smoke curl | health+CORS 통과 |
