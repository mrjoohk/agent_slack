# AI CLI Relay Orchestrator 운영 및 확장 매뉴얼

이 문서는 전체 시스템의 통합 테스트(E2E), 외부 모바일 환경(Slack) 연동, 신규 LangGraph 에이전트 추가, 그리고 다중 CLI 어댑터에 대한 확장 가이드라인을 제공합니다.

---

## 1. 전체 시스템 통합 테스트 (E2E Testing) 방법
로컬 환경 (Mac/Linux 및 **특히 Windows 11**) 상에서 에이전트 큐와 Slack 릴레이가 정상 연동되는지 패키지 충돌 없이 확인하는 표준 시나리오입니다.

1. **필수 패키지 설치 (최초 1회):**
   - 개발 장비의 터미널에서 모듈을 설치합니다: `python -m pip install fastapi uvicorn celery redis slack_bolt slack_sdk langgraph pydantic`
2. **서비스 인프라 전체 기동 (명령어 오류 완벽 타파):**
   - **탭 1 (Redis 브로커 - 필수):** Windows에는 Redis가 네이티브로 제공되지 않으므로, Docker Desktop을 기동한 뒤 컨테이너로 띄웁니다.
     `docker run -d -p 6379:6379 --name redis_broker redis:latest`
   - **탭 2 (Celery 워커):** 윈도우 PATH 오류를 피하기 위해 파이썬 모듈 모드(`-m`)로 스크립트를 감싸 실행하고, 윈도우 한정 프로세스 데드락 방지를 위해 `--pool=solo` 옵션을 붙여야 워커가 응답합니다.
     `python -m celery -A ai_cli_relay.app.worker.tasks worker --loglevel=info --pool=solo`
   - **탭 3 (FastAPI 서버 연결):**
     `python -m uvicorn ai_cli_relay.app.main:app --host 0.0.0.0 --port 8000`
3. **슬랙 앱 이벤트 트리거 기능 검증:**
   - 슬랙 테스트 채널에서 봇을 멘션하여 `@bot claude` (또는 `skill[core-engineering] 리팩토링해줘`) 명령어 입력.
3. **가시성 검증 항목:**
   - (서버 탭) Slack Event가 200 OK로 수신되고 Handoff 워커 태스크가 발행되는지 확인.
   - (워커 탭) `task_id`를 받고 워커가 해당 디렉토리 위치에서 서브프로세스를 생성하는지 로그 확인.
   - (슬랙 UI) 샌드박스의 stdout 출력(로그)이 쓰레드에 페이지네이션스트리밍(Pagination-streaming) 방식으로 갱신되는지 확인.
   - (파일시스템) 지정된 `workspace_path` 경로에 실제로 파일이 생성/변경되었는지 확인.

---

## 2. 모바일 사용을 위한 외부 환경 및 포트포워딩 구축
로컬 백엔드 서버(FastAPI)의 웹훅 포트를 뚫어 모바일 Slack 앱에서도 AI CLI를 트리거할 수 있게 하는 환경 설정법입니다.

1. **Ngrok 활용 (가장 빠름):**
   - 개발 장비에서 `ngrok http 8000` (또는 `cloudflared tunnel`) 명령어 실행
   - 할당받은 Public URL (예: `https://abcd.ngrok.io`) 복사.
2. **Slack 앱 매니페스트 업데이트:**
   - [Slack API Dashboard] -> Features -> Event Subscriptions 로 이동.
   - **Request URL** 란에 `https://abcd.ngrok.io/slack/events` 형태로 입력하여 검증(Verified) 체크를 받습니다.
3. **모바일 릴레이 검증:**
   - 스마트폰에서 슬랙 앱 실행 후 채널에 `@bot claude`를 입력하여 즉각 모달이 뜨면 완벽하게 연결된 것입니다.

---

## 3. 추가 에이전트 구현 방법 (LangGraph 확장)
기존의 Agent-1, 2, 3 외에 특정 스킬(예: 보안 QA 봇)을 파이프라인의 신규 노드로 확장 투입하는 방법입니다.

1. **라우팅 멤버 등록 (`state.py`, `supervisor.py`):**
   - `HandoffPayload` 스키마 및 `supervisor.py` 내부 `self.members` 에 `"Agent-4"` 등의 역할을 추가합니다.
2. **신규 에이전트 로직 팩토리 작성 (`agent_4.py`):**
   - 아래와 같이 Pydantic State를 이어받아 로직을 처리하는 단순 파이썬 함수 생성.
   ```python
   def agent_4_node(state: AgentState):
       # [보안 검토] 역할 로직 수행
       return {"messages": [HumanMessage(content="보안검토 이상무")]}
   ```
3. **그래프(Graph) 엣지 마운트 (`supervisor.py`):**
   - `build_graph()` 함수 안에서 명시적 바인딩을 수행합니다.
   ```python
   workflow.add_node("Agent-4", agent_4_node)
   workflow.add_edge("Agent-4", "Orchestrator") # 완료되면 다시 지휘자에게 권한 회수
   ```

---

## 4. 다중 CLI (Cursor, Codex, Gemini) 어댑터 추가 및 사용량 연동 방법
Claude 뿐만 아니라 다양한 CLI를 스위칭 가능하게 확장하는 방법입니다.

1. **새로운 어댑터 상속 및 구현 (`app/adapters/gemini.py` 등):**
   - `BaseCLIAdapter`를 상속받은 하위 클래스를 만듭니다.
   ```python
   from .base import BaseCLIAdapter, JobSpec

   class GeminiCLIAdapter(BaseCLIAdapter):
       async def submit(self, spec: JobSpec) -> str:
           cmd = ["gemini", "run", "--model", spec.model_name, spec.prompt]
           self.process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE)
           return str(self.process.pid)
   ```
2. **라우터 (Worker Task) 에서의 스위칭 (`app/worker/tasks.py`):**
   - 슬랙 팝업 선택창(모달)에서 넘어온 변수에 따라 인스턴스를 동적으로 찍어냅니다.
   ```python
   if selected_cli == "gemini":
       adapter = GeminiCLIAdapter()
   elif selected_cli == "cursor":
       adapter = CursorCLIAdapter()
   ```

### 💡 [중요] 사용 가능 모델 및 한도(Quota %) 수집 지침 (CLI 커맨드 활용 설계)
CLI 도구가 업데이트 되어도 절대 깨지지 않도록, CLI 자사에서 공식 제공하는 터미널 커맨드(예: `/cost`)를 이용하여 한도를 가져옵니다.
1. **모델 리스트 정의:** 서버 내부의 `config.yaml`이나 `Dict` 등에 각 CLI가 공식 제공 중인 스펙트럼(예: `claude: [Sonnet 4.6, Opus 4.6, Haiku 4.5]`)을 하드코딩 매핑해 둡니다. 슬랙 드롭다운의 기본 모델 리스트로 사용됩니다.
2. **단발성 커맨드 실행을 통한 잔여량(%) 파싱 기법:**
   - 봇이 슬랙에서 모델 선택 창(모달)을 띄우기 직전, `BaseCLIAdapter` 공통 인터페이스 내의 `get_usage_limits()` 함수가 백그라운드로 호출됩니다.
   - 해당 어댑터는 터미널 시스템에 `claude --print "/cost"` 혹은 시스템 별도 잔여량 조회 전용 예약어(예: `gemini usage`, `/balance` 등)를 서브프로세스 단위에서 짧게 실행합니다. (One-off Execution)
   - CLI 도구들이 출력해주는 인간 친화적 로그 텍스트(`stdout`)의 문장 형태 결과물(예: "You have 15% remaining tokens")을 받아와서, 서버 단에서 **정규 표현식(Regex) 또는 가벼운 구문 분석 파서**를 돌려 숫자 퍼센티지만 추출해 냅니다.
   - 이렇게 뽑은 `15%`, `$4.50` 등의 값을 슬랙의 모달창 텍스트 라벨에 조립(`Claude 3.5 Sonnet (남은 량: 15%)`)하여 깔끔하게 사용자에게 표출합니다. 이 방식을 통해 안정적인 한도 모니터링이 완벽하게 지원됩니다.
