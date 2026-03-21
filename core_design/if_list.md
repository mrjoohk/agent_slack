# Stage 5: 통합기능(IF) 도출 (IF List)

## IF-01: Slack Command UI Interface
- **IF-ID:** IF-01
- **Description:** 사용자가 입력한 동적 직관적 명령어(`/{skill_name} [프롬프트 텍스트]`)를 수신하고, 쓰레드(Thread)를 초기화하여 사용자에게 응답함.
- **Producer:** User (via Slack Client)
- **Consumer:** Bot API Layer
- **Input Contract:** `SlackEvent` (type: dict, Slash Command: `/{skill_name}`, Argument: `prompt_text`)
- **Output Contract:** `JobRequest` (type: pydantic.BaseModel, `skill_name` 및 원본 `prompt_text` 포함)
- **Constraints:** 응답 시간이 3초를 초과하면 안 됨. 매니페스트에 등록되지 않은 동적 슬래시 명령어의 한계를 우회하기 위한 래퍼(Wrapper) 봇 검토 필요.
- **Linked REQs:** REQ-001

## IF-02: Orchestrator Engine (LangGraph Supervisor)
- **IF-ID:** IF-02
- **Description:** 전달받은 `JobRequest`를 바탕으로 멀티 에이전트(Architect, Builder, Verifier) 작업 큐를 생성하고 상태 전이를 관리함.
- **Producer:** Bot API Layer
- **Consumer:** Task Queue (Redis Broker)
- **Input Contract:** `JobRequest` (단일/멀티 모드 명시)
- **Output Contract:** `HandoffPayload` (type: JSON, next_agent 지정)
- **Constraints:** 상태 전이(State Edge) 평가 시 무한 루프 차단(Max iterations) 설정 필요.
- **Linked REQs:** REQ-002

## IF-03: Sandbox Worker & Mount Manager
- **IF-ID:** IF-03
- **Description:** 큐에서 작업을 꺼내어, 호스트 타겟 디렉토리를 Docker 컨테이너에 안전하게 바인드 마운트 한 뒤 실행함.
- **Producer:** Task Queue (Redis Broker)
- **Consumer:** Docker Engine API
- **Input Contract:** `HandoffPayload`, `workspace_path` (absolute path str), `write_permission` (bool)
- **Output Contract:** `ContainerExecutionResult` (exit_code: int, logs: stream)
- **Constraints:** 반드시 UID/GID 바인딩 수행, 마운트 시 `ro` vs `rw` 구분 필수.
- **Failure Modes:** 권한 오류(UID mismatch), 디렉토리 마운트 불가(Invalid host path).
- **Linked REQs:** REQ-003

## IF-04: CLI Adapter Stream Bridge
- **IF-ID:** IF-04
- **Description:** 컨테이너 내부 CLI 도구의 표준 출력(stdout)을 구독하고, 이를 청크 단위(Debounce)로 묶어 Slack Thread에 갱신함.
- **Producer:** Docker Container Stdout
- **Consumer:** Slack API (`chat.update`)
- **Input Contract:** `LogChunk` (type: bytes/str, continuous stream)
- **Output Contract:** `SlackUpdatePayload` (type: dict)
- **Constraints:** Slack API Rate Limit 준수 (Debounce >= 1s).
- **Failure Modes:** 스트림 중단(Broken pipe), Slack 메시지 길이(4000자) 초과 잘림 현상.
- **Linked REQs:** REQ-004

## IF-05: Skill Profile & Configuration Loader
- **IF-ID:** IF-05
- **Description:** `.gemini/antigravity/skills/` 등 지정된 스킬 저장소에서 스킬 정의서(`SKILL.md`)를 파싱하여 CLI 에이전트의 System Prompt 또는 Context에 주입함.
- **Producer:** Orchestrator / Worker
- **Consumer:** CLI Adapter (Claude/Cursor System Prompt)
- **Input Contract:** `SkillRequest` (list of skill names)
- **Output Contract:** `SkillContext` (type: str, merged markdown content)
- **Constraints:** 여러 스킬 로드 시 토큰 리밋(Context window) 초과 방지 필터링 필요.
- **Failure Modes:** 지정된 스킬 경로 없음(FileNotFound).
- **Linked REQs:** REQ-005
