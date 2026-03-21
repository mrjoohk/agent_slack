# Stage 8: 검증 & 증거 계획 (Verification Plan)

## 1. 개요
AI CLI + Agent Orchestration 결합 시, 가장 리스크가 큰 부분은 **Docker Volume 바인드 소유권 강탈(권한 이슈)**과 **Slack API 밴스(Rate Limit 중지)**입니다. 따라서 이 항목들에 대해 철저한 테스트를 구성합니다.

## 2. 단위 테스트 (Unit Tests)

### 2.1 UF-03-A (마운트 권한 생성기) 테스트
- **명령:** `pytest -v tests/test_sandbox_mount.py`
- **검증 케이스:**
  1. `READ_ONLY` 모드로 전달 시 반환되는 딕셔너리 모드가 `'ro'`인지 확인.
  2. UID/GID 텍스트 조합(`1000:1000`)이 정상적으로 포매팅되는지 확인 (윈도우 Mock 처리 포함).
  3. Path Traversal 시도(예: `workspace_path="../../etc"`) 처리 시 ValueError 발생 확인.

### 2.2 UF-04-B (디바운스 업데이트) 테스트
- **명령:** `pytest -v --asyncio-mode=auto tests/test_slack_throttler.py`
- **검증 케이스:**
  1. 0.1초 간격으로 10개의 로그를 주입할 때 `chat.update` Mock 호출 수가 1회(또는 설정 간격 비례)인지 확인.
  2. 버퍼 닫힘(Flush) 이벤트 시 남은 잔여 메시지가 정상적으로 최종 업데이트되는지 확인.

## 3. 통합 테스트 (Integration Tests)

### 3.1 Docker Sandbox e2e 마운트 검증
- **명령:** `python scripts/verify_docker_mount.py`
- **검증 시나리오:**
  1. 테스트용 더미 볼륨을 생성 (`/tmp/ai_test_workspace`)
  2. 파이썬 스크립트 모듈(`worker.sandbox`)을 사용하여 `write_permission=False`로 Alpine 리눅스 컨테이너 실행.
  3. 컨테이너 내부에서 파일 생성 명령(`touch /app/workspace/test_file`) 시도.
  4. 로그에 Permission Denied 가 찍히고 종료 코드(Exit code)가 0이 아님을 `증거 팩`에 기록(Assertion).
  5. `write_permission=True`로 실행 후 파일 생성 -> 성공 시 호스트에서 생성된 파일 소유자를 확인하여 사용자 UID와 일치하는지 `증거 팩`에 기록.

## 4. 증거 팩 (Evidence Pack) 구조
CI(GitHub Actions) 환경이나 수작업 검증 구동 시 다음 구조에 테스트 결과 및 로그를 남겨 `ci-evidence-automation` 스킬이 참고할 수 있도록 합니다.

```
/evidence_pack/
  ├── unit/
  │   ├── req_004_streaming.log
  │   └── test_sandbox_mount.xml
  ├── integration/
  │   ├── req_003_mount_auth.log (중요: 실제 Docker 권한 제어 성공 로그)
  │   └── test_dispatch.json
  └── run_metadata.json (Commit SHA, 파이썬/OS 환경, 타임스탬프)
```
