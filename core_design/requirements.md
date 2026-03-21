# Stage 4: 요구사항 도출 (Requirements)

## REQ-001: Slack Command Trigger & Acknowledgement
- **ID:** REQ-001
- **Context:** 사용자가 Slack 채널에서 메신저처럼 자연스럽게 AI 작업을 지시(`/스킬명 [프롬프트]`)하고, 서버가 이를 수신하여 인증 및 라우팅함.
- **Inputs:** Slack Webhook Event 형태 (명령어: `/{skill_name}`, 프롬프트 텍스트: `~해서 ~해줘`, 유저 정보)
- **Outputs:** Slack Ephemeral Message ("작업 배정 중...") 및 HTTP 200 OK.
- **Constraints:** 응답 시간이 3초를 초과하면 안 됨 (Slack Timeout 회피). Slack API 한계상 정의되지 않은 명령어는 에러를 뱉으므로, 사용 가능한 스킬들은 앱 매니페스트에 사전 등록되거나 Catch-all 라우터(`/ai [skill_name] [prompt]`)가 필요할 수 있음.
- **Acceptance Criteria:** Given 사용자가 `/core-engineering 로그인 기능 설계해줘` 또는 `/ai core-engineering 로그인 기능 설계해줘`를 입력, When Slack Bolt 앱이 파싱, Then 명령어 텍스트 원본 그대로를 프롬프트로 삼고 큐에 태스크를 적재한 뒤 "Job ID 할당됨" 임시 메시지를 반환한다.
- **Tests:** unit (Bolt HTTP 핸들러 테스트), e2e (Slack 봇 모의 테스트)
- **Evidence:** `evidence_pack/req_001_slack_ack.log`

## REQ-002: LangGraph Orchestrator Job Dispatch
- **ID:** REQ-002
- **Context:** API 레이어가 Redis 작업 큐로 HandoffPayload 기반의 에이전트 작업을 위임 및 라우팅함.
- **Inputs:** `HandoffPayload` JSON (from_agent, to_agent, objective 등)
- **Outputs:** Redis Task Enqueue Status 및 생성된 `job_id` (str)
- **Constraints:** 타겟 에이전트 설정(to_agent)이 잘못되거나 존재하지 않는 CLI 모드일 경우 즉각 검증 에러를 슬랙 쓰레드에 던져야 함.
- **Acceptance Criteria:** Given LangGraph State 반환, When `to_agent="Agent-2"`로 지정, Then Task Broker가 정확히 Builder 작업 큐로 메시지를 발송(`task_id` 반환 성공)한다.
- **Tests:** integration (Redis Enqueue 및 Handoff payload parse)
- **Evidence:** `evidence_pack/req_002_dispatch.log`

## REQ-003: Docker Sandbox Mount & UID Binding
- **ID:** REQ-003
- **Context:** Worker가 작업을 할당받고, 격리된 컨테이너 환경에서 실제 명령어를 실행하기 위해 볼륨 마운트와 권한을 설정한다.
- **Inputs:** `job_id`, `workspace_path` (호스트의 절대경로 절대경로), `write_permission` (boolean)
- **Outputs:** 구동된 Docker 컨테이너의 `container_id` 및 생성된 실행 환경.
- **Constraints:** UID 바인딩을 통해 호스트 파일 권한 손상 방지. `write_permission=False` 시 `-v path:/app/workspace:ro` 적용.
- **Acceptance Criteria:** Given `write_permission=False`, When 워커가 컨테이너를 구동하고 그 안에서 `touch /app/workspace/test.txt`를 실행, Then 실행 실패(Permission Denied)하고 에러 코드가 리턴되어야 한다.
- **Tests:** integration (Docker SDK mount validation)
- **Evidence:** `evidence_pack/req_003_mount_auth.log`

## REQ-004: CLI Adapter Output Streaming
- **ID:** REQ-004
- **Context:** 구동된 컨테이너에서 실행되는 CLI 앱(Claude/Cursor)의 stdout/stderr를 슬랙 쓰레드로 실시간 중계한다.
- **Inputs:** `container` stdout stream.
- **Outputs:** Slack API `chat.postMessage` 및 `chat.update` Call.
- **Constraints:** Debouncing 간격 = 최소 1초. 1회의 Slack update 시 텍스트 한도가 4000자를 초과하면 잘라내고 파일을 첨부해야 함.
- **Acceptance Criteria:** Given 1초 동안 50개의 로그 줄이 stdout으로 쏟아질 때, When Adapter의 스트리밍 브릿지가 작동, Then Slack API 호출(`chat.update`)은 1회만 발생하며 누락된 텍스트는 없어야 한다.
- **Tests:** unit (Debounce generator test)
- **Evidence:** `evidence_pack/req_004_streaming.log`

## REQ-005: Dynamic Skill Injection
- **ID:** REQ-005
- **Context:** 슬랙 명령어(`/스킬명`) 호출 시 지정된 Engineering/Automation 스킬 문서를 파싱하여 프롬프트의 기초 컨텍스트로 주입함.
- **Inputs:** 슬랙에서 입력받은 `skill_name` (예: `core-engineering`) 및 유저의 원본 `prompt` 텍스트.
- **Outputs:** 파싱된 Markdown 스킬 프롬프트 텍스트와 원본 `prompt`가 결합된 최종 Agent System Message.
- **Constraints:** 스킬 파일(`.md`)이 누락되었거나 파싱 실패 시, 작업 시작 전 즉각 오류 반환.
- **Acceptance Criteria:** Given `/core-engineering 로그인 백엔드 설계해줘` 명령, When Orchestrator가 작업을 준비, Then `core-engineering` 스킬 문서 전체 내용과 사용자의 지시문(`로그인 백엔드 설계해줘`)을 병합하여 첫 번째 Agent(Architect)에게 전달한다.
- **Tests:** unit (Skill 파일 로더 파서 테스트)
- **Evidence:** `evidence_pack/req_005_skill_injection.log`
