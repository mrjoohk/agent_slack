# 제약사항 해결 및 Orchestrator 설계 분석 (260319_2250)

이전 단계에서 사용자의 승인을 받은 Orchestrator 및 Task Queue(Celery) 연동 구현에 대한 세부 기능 분석 내역입니다.

## 1. LangGraph State.py 스키마 설정 설계
- **판단 근거:** 멀티 에이전트 환경에서 각 에이전트 간 릴레이 시, LLM은 자연어로 대화하려는 습성이 있어 핵심 파일 경로나 산출물 리스트가 휩쓸려 누락되는 문제(Halucination)가 잦습니다. 이를 방지하고자 `Pydantic BaseModel`을 상속받은 `HandoffPayload` 규격을 정의하여 `AgentState.current_handoff` 객체에 바인딩함으로써 명확한 목표와 파라미터를 넘겨주도록 구조적 강제(Structured Output)를 수행합니다.

## 2. Supervisor Node 로직 구현
- **판단 근거:** 상태 그래프(StateGraph) 내에서 각 워커 노드를 조건부 엣지(Conditional Edge)로 스위칭하는 '중앙 지휘자' 역할입니다. `current_handoff.to_agent` 값을 파싱해 타당한 워커 노드(`Agent-1/2/3`) 또는 종료 조건(`END`)으로 분기시켜 비정상적인 무한 루프 핑퐁을 방지합니다. 

## 3. Skill Loader 파서 구축 (UX 대응)
- **판단 근거:** `skill[core-engineering]` 처럼 Slack을 타고 온 키워드에서 동적으로 `SKILL.md`를 열고 마크다운 파일 상단의 YAML Frontmatter(`---`) 메타데이터를 제외한 규칙 텍스트만을 파싱하여 추출합니다. 이를 통해 시스템 오염 없이 순수한 명령어만 에이전트 프롬프트에 주입할 수 있습니다.

## 4. 백엔드 워커 태스크(tasks.py) 큐 엔트리포인트
- **판단 근거:** FastAPI 애플리케이션의 이벤트 스레드가 차단(Blocking)되어 연쇄 타임아웃 오류가 발생하지 않도록, `run_langgraph_pipeline` 이라는 별개 스레드의 진입점을 만들었습니다. MVP에서는 `Celery` 대신 asyncio Task로 시뮬레이션 스코프를 제공하되 이후 쉽게 확장 가능한 구조 배치를 채택했습니다.
