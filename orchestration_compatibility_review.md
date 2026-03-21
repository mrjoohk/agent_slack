# AI CLI 기반 Agent Orchestration 통합 검토서

## 1. 검토 목적 및 결론
본 문서는 `ai_cli_orchestration_design.md`(Slack, Relay Bot, CLI Worker 중심)를 메인 아키텍처로 삼고, 그 위에 `agent_orchestration_design.md`(LangGraph 기반 Multi-Agent Supervisor)를 구현할 수 있는지 검토한 결과입니다.

**결론: 충분히 구현 가능하며, 두 설계는 매우 훌륭한 상호 보완적(Synergistic) 구조를 가집니다.** 
AI CLI 구조가 인프라 및 실행 환경(Infrastructure & Execution Layer)을 담당하고, Agent Orchestration 구조가 그 위에서 동작하는 애플리케이션 및 워크플로우 로직(Workflow Logic Layer)을 담당하게 됩니다.

---

## 2. 아키텍처 매핑 (Architecture Mapping)

두 설계안의 핵심 컴포넌트를 매핑하면 다음과 같이 자연스럽게 결합됩니다.

| `ai_cli_orchestration_design.md` (제어/실행 인프라) | `agent_orchestration_design.md` (에이전트 워크플로우) | 통합 역할 |
| :--- | :--- | :--- |
| **Slack / Relay Bot** | (UI 역할 부재) | 사용자와 시스템 간의 인증, 트리거, 결과 스트리밍 및 승인/거절 UI 제공 |
| **Orchestrator API (FastAPI)** | **Orchestrator (Supervisor)** | LangGraph 엔진을 구동하는 진입점. Handoff Payload 검증 및 에이전트간 라우팅 상태 관리 주체 |
| **Docker Worker / Sandbox** | **Agent-1, Agent-2, Agent-3** | 각 에이전트(Architect, Builder, Verifier)가 격리된 환경에서 안전하게 작업을 수행하는 런타임 환경 |
| **CLI Adapter Layer** | **Tools (MCP)** | 에이전트가 코드를 작성하고 검증할 때 단순히 `mcp.shell`을 넘어서 Cursor CLI, Claude CLI 등을 Adapter를 통해 직접 호출하여 품질 극대화 |

---

## 3. 통합 아키텍처 (Integrated Architecture)

```mermaid
graph TD
    User([User in Slack]) -->|/ai run (Command)| SlackBot[Slack Relay Bot]
    SlackBot --> API[FastAPI Orchestrator]
    
    subgraph "LangGraph Supervisor Engine (Agent Orchestration)"
    API --> Supervisor[Supervisor Orchestrator Node]
    Supervisor <-->|HandoffPayload| Agent1[Agent-1: Architect]
    Supervisor <-->|HandoffPayload| Agent2[Agent-2: Builder]
    Supervisor <-->|HandoffPayload| Agent3[Agent-3: Verifier]
    end
    
    subgraph "Relay-Based Execution (AI CLI Infrastructure)"
    Agent1 -.->|Task queue| RQ[Redis Queue]
    Agent2 -.->|Task queue| RQ
    Agent3 -.->|Task queue| RQ
    
    RQ --> W1[Docker Worker]
    RQ --> W2[Docker Worker]
    RQ --> W3[Docker Worker]
    end
    
    W1 --> CLI_A1[Claude CLI Adapter]
    W2 --> CLI_A2[Cursor CLI Adapter]
    W3 --> CLI_A3[Codex/Tests CLI Adapter]
```

---

## 4. 시너지 및 기대 효과

1. **안전성 (Safe-by-default):** 
   Agent-2(Builder)나 Agent-3(Verifier)가 생성형 AI로 코드를 실행하거나 시스템을 조작할 때, AI CLI 설계의 **Docker Worker / Local Sandbox**를 활용하므로 호스트 시스템(Host OS)의 손상을 원천적으로 방지할 수 있습니다.
2. **코드 생성 품질 향상:** 
   Agent-2(Builder)가 단순히 LLM API로 코드를 짜는 것보다, 내부적으로 **CLI Adapter (Cursor 등)**를 사용하여 대형 코드베이스를 수정하도록 지시하면 훨씬 더 뛰어난 성능을 발휘합니다.
3. **가시성 (Observability):** 
   LangGraph의 각 노드 전환(Handoff) 및 Agent의 작업 상태를 Slack Thread를 통해 실시간으로 사용자에게 스트리밍(`ai_cli_orchestration`의 원칙)할 수 있어 디버깅 및 사용자 경험이 극대화됩니다.

---

## 5. 구현 시 해결해야 할 과제 (Challenges)

- **상태(State) 및 워크스페이스 공유:** Docker Worker 간에 작업을 이어가기 위해(예: Agent-1의 명세서를 바탕으로 Agent-2가 구현), 컨테이너 간에 공유되는 볼륨(Shared Volume)이나 분산 파일 시스템 기반의 마운트 전략이 필요합니다.
- **스트리밍 노말라이제이션 (Streaming Normalization):** LangGraph에서 뿜어져 나오는 이벤트와 각 CLI Adapter의 표준 출력(stdout)을 취합하여 하나의 Slack Thread로 매끄럽게 포맷팅(Debounce & Chunking)하는 브릿지 로직 구현이 핵심 난이도입니다.
