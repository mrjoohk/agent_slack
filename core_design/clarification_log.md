# Stage 2: 문제 검토 & 명확화 (Clarification Log)

**Q1. Slack 채널에서 여러 개의 작업을 동시에 요청(`mcp.run` 여러 번 등)할 경우 어떻게 처리되는가?**
- **A1:** FastAPI 서버가 요청을 즉시 202 Accepted 처리 후 Redis(Celery) 큐에 적재(Enqueue)합니다. Worker 노드 수량에 따라 병렬 처리 또는 대기열 대기(Pending) 상태로 관리됩니다.

**Q2. LangGraph 기반 에이전트(Agent 1, 2, 3)가 하나의 목적을 위해 순차적으로 작업할 때, 파일 시스템 컨텍스트(Workspace)는 어떻게 공유되는가?**
- **A2:** 각 에이전트는 독립된 작업(Docker Worker)으로 실행되지만, 호스트의 **명시된 동일한 경로(Workspace 디렉토리)**를 볼륨 바인드 마운트(Volume Bind Mount)하여 사용합니다. 따라서 Agent-1이 작성한 `.md` 파일을 Agent-2가 마운트된 디렉토리 내에서 읽어 코드를 생성할 수 있습니다.

**Q3. 실행 시간이 긴 작업의 경우 Slack의 Timeout(3초) 문제는 어떻게 해결하는가?**
- **A3:** Slack Events/Command API는 수신 즉시 Acknowledgement를 반환하고, 실제 작업 진행 상황 및 스트리밍 로그는 `chat.update` 혹은 쓰레드(Thread)에 새로운 메시지를 지속적으로 추가하는 비동기 방식(Relay)으로 처리합니다.
