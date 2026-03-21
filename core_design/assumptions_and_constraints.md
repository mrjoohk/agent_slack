# Stage 3: 문제 상세화 (Assumptions and Constraints)

## 1. 제약 조건 (Constraints)

- **보안/실행 공간 제약 (Safe-by-default):**
  - 시스템 조작 명령어 및 모델이 생성한 코드 실행은 **절대** API 서버(호스트) 운영 환경에서 직접 실행되지 않아야 합니다. 반드시 Docker 기반의 샌드박스 컨테이너 또는 완전히 격리된 환경에서 실행되어야 합니다.
  
- **Docker / Sandbox 마운트 설계 제약 (CRITICAL):**
  - **공유 작업 공간(Shared Workspace):** 에이전트 간 연속적인 파일 시스템 수정을 위해, 호스트 머신에 위치한 특정 타겟 프로젝트 디렉토리를 구동되는 모든 Worker 컨테이너 내부의 `/app/workspace` 경로에 바인드 마운트(`-v /host/path:/app/workspace`) 해야 합니다.
  - **권한 매핑(Permission Mapping):** 컨테이너 내부에서 생성된 파일이 `root` 권한으로 생성되어 호스트에서 접근/수정이 불가능해지는 문제를 막기 위해, Docker 실행 시 호스트의 UID/GID를 주입(`--user $UID:$GID`)하여 컨테이너를 구동해야 합니다. 
  - **ReadOnly 분리 마운트:** 코드 작성과 무관한 분석 에이전트(Agent-1 Architect)의 경우 실수로 소스코드를 훼손하지 않기 위해 볼륨을 ReadOnly 옵션으로 마운트 (`-v /host/path:/app/workspace:ro`) 해야 합니다. Builder나 Verifier 에이전트만 Write 권한을 부여받습니다.

- **성능 및 갱신 제약 (Rate Limiting):**
  - Slack API를 통한 스트리밍 갱신은 Too Many Requests 에러 방지를 위해 최소 1~1.5초 이상의 Debouncing 처리를 통해 텍스트 청크를 묶어서(`chat.update`) 전송해야 합니다.

## 2. 경계 조건 (Boundary Conditions)
- CLI Adapter가 반환하는 스트림 로그가 과도하게 길어질 경우(Slack 한계 4000자 초과), 초과분을 파일로 저장하거나 메시지를 잘라서(Truncate) 스크롤 스니펫(Snippet)으로 업로드해야 합니다.
- Docker Sandbox가 무한 반복/대기 상태에 빠지는 것을 막기 위해 모든 Worker Task(Adapter run)에는 Hard Timeout(예: 600초)이 설정되어야 합니다.

## 3. 가정 (Assumptions)
- 호스트 머신(API 서버/Worker 노드가 구동되는 곳)에는 `docker` 데몬과 `docker-py` 또는 CLI 제어가 가능한 환경이 세팅되어 있다.
- Redis 서버가 구동 중이며, 워커는 이를 브로커로 활용할 수 있다.
