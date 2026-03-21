# 사용자 결정이 필요한 미정의 제약사항 (Unresolved Constraints & Decisions)

이 문서는 설계 및 기초 코드 구현 단계에서 결정되지 않은 비즈니스/시스템 로직들에 대한 결정 리스트입니다.
본격적인 파이프라인 연동 전에 다음 항목들에 대한 리뷰와 확정이 필요합니다.

## 1. Slack 동적 슬래시 명령어 (`/{skill_name}`) 처리 정책
Slack 앱은 매니페스트(App Manifest)에 명시된 Slash Command 외의 임의의 명령어(예: `/core-engineering`)를 허용하지 않습니다. 어떻게 우회할지 결정해야 합니다.
- **[옵션 A]** 모든 스킬 이름(예: `core-engineering`, `rag-data-quality`)을 매니페스트에 수동 기입하여 정적 라우팅 지원.
- **[옵션 B]** 단일 글로벌 명령어(`/ai [skill_name] [prompt]`) 적용.
- **[옵션 C]** Slack Bot을 채널에 초대하고 멘션하는 방식(`@AI-Relay core-engineering [prompt]`)으로 전환.

## 2. Docker 이미지 및 컨테이너 워커 실행 환경
Agent를 구동할 Docker 내부 환경(베이스 이미지) 셋업 방식입니다.
- **[이슈]** Cursor, Claude 등의 CLI는 데스크탑에 깔려있을 수 있지만 리눅스 컨테이너 안에는 설치파일이나 인증 체계가 다를 수 있습니다.
- **[결정 필요]** 에이전트 용도로 어떤 Docker Base Image를 사용할 것인가? (예: `ubuntu:22.04` 베이스에 Node.js 설치 후 npm AI CLI들을 번들링한 자체 빌드 이미지 사용 여부)

## 3. 마운트 대상 호스트 Workspace 관리
Worker가 호스트 볼륨을 읽거나 쓸 때 타겟 디렉토리를 지정해야 합니다.
- **[이슈]** 보안 상 사용자가 임의의 절대경로(예: `/etc/passwd`)를 던지면 안 됩니다.
- **[결정 필요]** 서버가 허용하는(Allowed) `BASE_WORKSPACE_DIR` 리스트를 `.env` 파일 등에 하드코딩할 것인지, 혹은 동적으로 DB에서 가져올 것인지 결정 필요.

## 4. 4,000자 초과 채팅 출력 로그 (Message Length Limit) 대응
현재 1초 디바운스로 로깅 시 Slack 제한인 문자열 4000자를 넘길 때 단순 잘라내기(Truncate `-3900:` 로직)만 구현되어 있습니다.
- **[옵션 A]** 초과분 폐기 (MVP 권장)
- **[옵션 B]** Slack `files.upload` API를 호출해 `stdout_chunk.txt` 형태로 첨부. (코드 복잡도 증가)

## 5. LangGraph State 데이터베이스 저장
Supervisor에서 진행되는 복잡한 Multi-Agent State Handoff 로직을 추적할 때 상태를 어디에 저장할지.
- **[결정 필요]** 단순히 Redis 메모리에 올릴 것인지(휘발성), Postgres(Sqlite) 통계를 남겨 대시보드로 볼 것인지. MVP에서는 Redis 권장.

---
**[Action Required]** 위 항목들을 검토하시고 피드백을 주시면, `BaseCLIAdapter` 상속 구현이나 `Orchestrator(main.py)` 코드의 분기 로직에 최종 반영됩니다.
