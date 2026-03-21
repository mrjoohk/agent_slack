# Stage 1: 문제 정의 (Problem Statement)

- **문제 배경 및 동기:**
  AI CLI (Cursor, Claude, Codex 등)를 활용하여 코드를 자동 생성 및 검증하는 과정에서, 터미널 환경에 직접(SSH 등) 접근하여 명령을 실행하는 것은 보안 위험과 이력 추적의 부재를 초래합니다. 또한, 여러 종류의 CLI 툴을 유기적으로 조합(LangGraph 기반 Multi-Agent)하여 복잡한 태스크를 수행하는 통합 파이프라인이 부재한 상황입니다.
- **해결하고자 하는 문제:** 
  외부 UI 채널인 Slack을 통해 접수된 트리거를 FastAPI 기반의 Orchestrator(Supervisor)로 넘기고, 이를 안전하게 격리된 환경(Docker Sandbox)에서 CLI Adapter를 사용하여 실행 및 스트리밍하는 "Relay-Based AI CLI Orchestrator" 백엔드 및 인터페이스를 통합 설계해야 합니다.
- **영향 범위:**
  애플리케이션 코드를 자동 작성, 검증, 배포하는 사내/개인 개발 파이프라인 전체. Infra(Docker, Redis)와 App(FastAPI, Slack Bolt) 전반.
