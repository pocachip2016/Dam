# Work Workspace — Shared Rules

> 이 파일은 `/home/ktalpha/Work` 아래 모든 프로젝트(AiNews, Dam, TabGet, mediaX, 이후 추가될 프로젝트)의 공통 규칙입니다. 각 프로젝트 `CLAUDE.md` 상단에서 `@../CLAUDE.md` 로 import 해 사용합니다. 변경 1회 = 전체 반영.

## Language & Tone
- 기본 응답 언어: 한국어. 코드/식별자/커밋 메시지는 영어 유지.
- 간결한 답변 선호. 불필요한 요약/머리말 최소화.

## Coding Discipline

> Source: [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) (verbatim). Meta-rules — apply to "how to code" decisions across all Work projects.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

> **Harness integration:** verify-loop applies *within* a single step only. Step boundaries follow the STOP rule in §Working Mode (stepwise) — never auto-advance across steps.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Working Mode (stepwise)
- **신규 개발 / 비자명한 변경** → 먼저 plan mode 로 진입. 플랜 승인 전 코드 수정 금지.
- 플랜 승인 후 **한 번에 한 단계(step)** 만 실행하고 **STOP**. 변경된 파일 + 요약을 보고한 뒤 사용자 "계속 / ok / 다음" 을 기다림.
- **각 step 종료 시 `/verify <step-id>` 호출 의무** — 프로젝트별 `.claude/verify.sh` 가 정의한 테스트를 실행하고 TODO/plan 체크박스를 토글. 문서만 바꾼 step은 `/verify --skip "사유"`.
- Stop hook 이 "코드 변경 이후 `/verify` 없음" 을 감지하면 한 번 차단 → 다시 Stop 시 통과. `Work/.claude/state/` 는 세션 상태 전용 (gitignore).
- 사소한 수정(오타, 한 줄)은 plan mode 생략 가능하지만 커밋 전 반드시 보고.
- **사용자가 명시적으로 요청하기 전까지 절대 커밋하지 않음.**

## Branch & Merge Convention
- 브랜치 네이밍: `feature/<짧은이름>`, `fix/<짧은이름>`, `chore/<짧은이름>`, `hotfix/<짧은이름>`.
- `main` 직접 커밋 금지. 반드시 브랜치에서 작업 후 머지.
- 머지는 `git merge --no-ff` — feature 이력 보존.
- 머지 후 로컬 브랜치 삭제(`git branch -d`). 필요 시 원격도 정리.
- 커밋 메시지는 Conventional Commits 권장: `feat: …`, `fix: …`, `chore: …`. 이슈 연결 시 `#번호` 포함.

## Issue Tracking
- 할 일/버그/아이디어는 각 프로젝트 **GitHub Issues** 로 일원화.
- 공통 라벨: `todo`, `in-progress`, `blocked`, `idea`.
- 프로젝트별 상세 할 일은 각 repo `TODO.md` 에 Now/Next/Later/Done 섹션으로 유지. 완료 항목 5개 초과 시 `CHANGELOG.md` 로 이동.

## File Conventions
- 프로젝트별 `CLAUDE.md` 는 `@../CLAUDE.md` import + **고유 정보만** (Purpose/Stack/Active Work/Where to look).
- 상세 설계/아키텍처는 `docs/` 아래로. CLAUDE.md 에는 경로만 언급.
- 문서/README 를 사용자 요청 없이 새로 만들지 않음.
- 개발 task 의 plan 은 `plans/<task-slug>/` 아래 → Plans Convention 참조.

## Plans Convention

task 단위 plan 을 영속 파일로 관리해 세션이 끊겨도 재시작 가능하고, 완료된 step 의 `summary` 로 다음 step 컨텍스트를 누적한다.

### 디렉토리 구조

```
plans/
└── <task-slug>/          # kebab-case (예: rss-kakao-poc, auth-flow)
    ├── index.json         # task 전체 현황 + step 상태
    └── step0.md           # 각 step 마다 1개 (step0.md, step1.md, …)
```

- mediaX 의 챕터 콘텐츠 `plans/01-*/` ~ `plans/07-*/` 는 기존 그대로 유지.
- dev task 는 반드시 `plans/dev-<slug>/` 로 분리해 공존.
- **계정 독립성**: `~/.claude_acc{N}/plans/` 는 레거시 — 신규 plan 은 반드시 프로젝트 내 `plans/` 에 저장. acc1·acc2 양쪽에서 동일하게 접근 가능.

### index.json 스키마

```json
{
  "project": "<프로젝트명>",
  "phase": "<task-slug>",
  "steps": [
    {
      "step": 0,
      "name": "project-setup",
      "status": "pending"
    }
  ]
}
```

- `steps[].status`: `"pending"` | `"completed"` | `"error"` | `"blocked"`
- `/verify` 통과 시 Claude 가 해당 step 에 `"status": "completed"`, `"summary": "한 줄 요약"`, `"completed_at": "ISO8601 KST"` 기록
- `"error"` 시 `"error_message"`, `"blocked"` 시 `"blocked_reason"` 기록
- **자동 실행 없음** — index.json 은 진행 가시성 + 재시작 시 컨텍스트 복원 용도

### step{N}.md 표준 형식

```markdown
# Step N: <이름>

> GitHub: #N | Milestone: <phase>   ← 최초 작성 시 "미생성", n8n back-write 후 실제 번호로 채워짐

## 읽어야 할 파일
- docs/ARCHITECTURE.md
- {이전 step 생성 파일}

## 작업
{구현 지시. 시그니처 수준만 제시, 구현은 에이전트 재량.
핵심 불변 규칙은 명시.}

## Acceptance Criteria
\`\`\`bash
bash .claude/verify.sh <id>
\`\`\`

## 금지사항
- X 하지 마라. 이유: Y
```

### 운용 원칙
- `summary` 누적이 다음 step 프롬프트 품질을 결정한다. `/verify` 통과 후 summary 한 줄을 반드시 기록.
- Step 설계는 `/stepwise` 슬래시 커맨드의 **7원칙** 을 따른다.
- 세션 재개 시: `plans/<task>/index.json` + `plans/<task>/step{N}.md` 를 읽으면 이전 컨텍스트 복원.

## Tooling
- 워크스페이스 현황: `bash /home/ktalpha/Work/status.sh` 또는 alias `ws`.
- 신규 프로젝트: `bash /home/ktalpha/Work/new-project.sh <이름>` 또는 `/new-project <이름>` — `docs/{PRD,ARCHITECTURE,ADR}.md` 스켈레톤 포함.
- 공용 슬래시 커맨드: `/ws`, `/switch`, `/sync`, `/wrap`, `/stepwise`, `/new-project`, `/verify`, `/followups`, `/step-status`, `/push`.
  - 소스: `.claude/commands/*.md` — `~/.claude_acc{1,2}/commands` 가 이 디렉토리로 향하는 symlink 라 새 `.md` 추가 시 양 계정에 즉시 노출됨 (다음 세션부터 인식). 신규 머신에서는 `bash install-commands.sh` 한 번 실행해 디렉토리 symlink 를 건다.
- `/verify <step-id>` 통과 시: plans/<task>/index.json 이 있으면 해당 step 에 summary 한 줄 캡처 → 다음 step 컨텍스트로 누적됨. verify 실패 메시지는 다음 UserPromptSubmit 에 자동 주입.

## Sync Convention

로컬(`TODO.md`, `plans/<task>/index.json`) ↔ GitHub(Issues, Projects v2) 양방향 동기화 규칙.

### SSOT (단일 진실 원천)

| 데이터 | 권위 | 미러 |
|---|---|---|
| Issue 상태 (open/closed) | **GitHub Issue** | `index.json.steps[].status`, TODO.md `[ ]/[x]` |
| Step 설명·AC | **`step{N}.md`** | Issue 본문 |
| Step summary | **`index.json.steps[].summary`** | Issue close comment |
| 라벨 (todo/in-progress/blocked) | **GitHub Issue label** | TODO.md 섹션 |

### ID 링크 규칙

- `index.json` step 에 `"github_issue": <N>` 필드로 Issue 번호 연결
- TODO.md 형식: `- [ ] [#42] description` (n8n back-write 후 자동 추가)
- step{N}.md 헤더: `> GitHub: #42 | Milestone: <phase>`

### 루프 차단

- Bot 자동 커밋 message 에 `[bot-sync]` 마커 필수
- n8n Trigger 에서 `[bot-sync]` 포함 push 는 skip (무한 loop 방지)
- `bot-managed` 라벨이 있는 Issue 는 issue-sync 워크플로우에서 skip

### n8n 워크플로우

harness 연동 워크플로우 JSON은 `.claude/n8n-workflows/` 에서 관리 (n8n 런타임은 `Work/FlowHub/`).

| 워크플로우 | Trigger | 역할 |
|---|---|---|
| `plan-to-issue` | push (plans/**/index.json) | step → GitHub Issue 자동 생성 + back-write |
| `issue-sync` | issues.opened/closed | GitHub Issue → TODO.md·index.json 역방향 |
| `notify-router` | POST /webhook/notify | urgent→ntfy / phase-complete→Kakao / else→Slack |

상세: `docs/sync-architecture.md` | 인벤토리: `.claude/n8n-workflows/README.md`

## Memory vs Docs 경계
- **사용자 선호/피드백** → Claude 메모리 (`~/.claude_acc1/.../memory/`).
- **프로젝트 사실/현재 상태** → 해당 프로젝트 `CLAUDE.md` / `TODO.md`.
- 겹치지 않게 유지.
