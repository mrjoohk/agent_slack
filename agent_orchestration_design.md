# Generalized Agent Orchestration Pipeline Design

## 1. Overview
이 문서는 `agent-orchestration` 스킬을 기반으로 다중 에이전트(Multi-Agent) 워크플로우를 구축하기 위한 LangGraph 아키텍처 설계서입니다. 특정 프로젝트에 종속되지 않고, 역할 정의서(`.md`)와 핸드오프 규정(`.md`)을 동적으로 읽어 파이프라인을 구축하는 **일반화된 오케스트레이션(Generalized Orchestration)**을 목표로 합니다.

## 2. Core Architecture (Supervisor Pattern)
LangGraph의 Supervisor 패턴을 차용하여 중앙의 오케스트레이터가 흐름을 제어하고, 워커 에이전트가 실제 태스크를 수행합니다.

### 2.1 Nodes (Agents)
각 노드는 초기화 시점에 각자의 역할 정의서(`agentN.md` 등)를 System Prompt로 주입받습니다.

1. **Orchestrator (Supervisor)**
   - **역할:** 전체 흐름 제어, 에이전트 라우팅, `HandoffPayload` 규격 검증.
   - **권한/도구 (MCP):** `mcp.webhook` (상태 알림).
2. **Agent-1 (Architect 👷)**
   - **역할:** 요구사항 분석, 설계 문서화, 단위 기능(UF) 분해, 인수 조건(Acceptance criteria) 작성.
   - **권한/도구 (MCP):** `mcp.github` (이슈/PR 컨텍스트 확인), `mcp.filesystem`(Read Only).
3. **Agent-2 (Builder 🛠️)**
   - **역할:** Agent-1의 설계(최소 파일 컨텍스트 `context_links`)를 바탕으로 코드 구현 로직 작성 (Minimal Diffs).
   - **권한/도구 (MCP):** `mcp.filesystem` (Write/Edit), `mcp.shell` (제한된 코드 포맷팅 및 실행).
4. **Agent-3 (Verifier 🕵️)**
   - **역할:** CI 테스트 실행, 벤치마크, 검증 수행 및 Evidence Pack 생성.
   - **권한/도구 (MCP):** `mcp.shell` (테스트 환경 제어), `mcp.filesystem` (리포트/증거 출력), `mcp.github` (검증 결과 PR 커멘트).

### 2.2 Routing Logic (Edges)
- 에이전트 1, 2, 3은 작업이 완료되면 반드시 **Orchestrator**로 제어권을 반환합니다.
- Orchestrator는 State의 `current_handoff.to_agent` 값을 읽고, 동적 조건부 엣지(Conditional Edge)를 통해 다음 라우팅 타겟을 스위칭합니다. 작업이 최종 완료(성공 혹은 중단) 판단 시 `FINISH` 노드로 이동하여 파이프라인을 종료합니다.

## 3. Structural Handoff (State Management)
텍스트 뭉치로 지시사항을 넘기면 데이터 누락 및 할루시네이션(Hallucination)이 발생할 수 있습니다. 이를 방지하기 위해 스킬 명세의 Handoff Template을 **Pydantic 스키마(Model)**로 변환하여 LangGraph의 **State**로 강제 구성합니다.

```python
from pydantic import BaseModel, Field
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class HandoffPayload(BaseModel):
    from_agent: str = Field(description="핸드오프 발신 에이전트")
    to_agent: str = Field(description="명시적인 다음 라우팅 대상 에이전트 이름 지정 (예: Agent-2, FINISH)")
    objective: str = Field(description="이관되는 핵심 목표")
    context_links: list[str] = Field(description="토큰 절약을 위해 이 작업에만 필요한 최소한의 연관 파일 경로 및 링크")
    deliverables: str = Field(description="다음 에이전트가 도출해야 할 구체적인 산출물 명세")
    constraints: str = Field(description="기타 제약 사항들 (금지 라이브러리, 특정 패턴 사용 등)")
    acceptance_tests: list[str] = Field(description="해당 기능의 인수 테스트(단위/E2E) 조건")
    evidence_outputs: str = Field(description="생성해야 할 증거(Evidence Pack) 포맷 및 경로 명시")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]  # 에이전트 및 사용자 간의 순차적 메시지 기록
    current_handoff: HandoffPayload                           # 직전 에이전트가 다음 타겟에게 쓴 구조화된 작업 지시서
```

## 4. Generalization Tips (일반화 핵심 전략)
이 설계를 향후 코드베이스로 옮길 때 반드시 지켜야 할 사항입니다.

1. **Dynamic Configuration Loading:** 
   `agent1.md`와 같은 파일이나 `config.yaml` 팩토리에서 동적으로 `allowed-tools` 및 역할 정의를 읽고 `make_worker_node()` 팩토리 함수를 통해 런타임에 에이전트를 조립해야 합니다. 이렇게 설계해야 프로젝트가 달라져도 엔진 코드 수정 없이 파이프라인을 재사용할 수 있습니다.
2. **Token Saving Constraints 강제화:**
   Agent-2(Builder)가 과도하게 방대한 컨텍스트를 읽는 것을 방지해야 합니다. Orchestrator 노드는 `HandoffPayload.context_links`에 명시된 파일 이외의 시스템 접근에 페널티 또는 차제 제어를 구비하여 Agent-2에게 넘겨지는 토큰(Token) 사용량을 방어해야 합니다.
