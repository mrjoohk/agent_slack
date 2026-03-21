# AI CLI Orchestration - TODO 적용 설계도

본 문서는 `ai_cli_orchestration_design.md`의 구조적 요구사항을 바탕으로, `todo.md`에 명시된 3가지 항목(Slack 명령어 스펙, Python MVP 코드 구조, CLI Adapter 인터페이스 설계)을 구체화한 설계안입니다.

---

## 1. Slack 명령어 스펙 (.md)

Slack은 AI 오케스트레이션 시스템의 유일한 트리거 및 UI 채널입니다. (Direct SSH 불가 원칙 적용)

### 1.1 기본 명령어 목록
- `/ai run [옵션] [프롬프트]` : 새로운 AI 작업 지시
- `/ai status [job_id]` : 진행 중인 작업 상태 확인
- `/ai cancel [job_id]` : 진행 중인 작업 강제 종료
- `/ai collect [job_id]` : 작업 결과물 파일(Artifact) 다운로드 링크 생성

### 1.2 `/ai run` 상세 스펙
멀티 CLI 혼합 오케스트레이션(Phase 2) 또는 단일 CLI(MVP)를 지원하기 위한 키워드 인자를 포함합니다.

* **사용 예시 (MVP - 단일 CLI):**
  - `/ai run --mode=claude src/ 에러 고쳐줘`
  - `/ai run --mode=cursor --repo=my-project 로그인 기능 PR 검토해`
* **사용 예시 (Advanced - 멀티 에이전트):**
  - `/ai run --mode=auto README.md 기반으로 파이썬 서버 구축부터 테스트까지 해줘` (이 경우 LangGraph 기반의 Orchestrator가 개입)

### 1.3 Slack UI/UX 흐름 (Socket Mode)
1. 사용자가 `/ai run` 명령어 입력
2. Relay Bot이 접수 완료 (Ephemeral Message 응답: *"작업 생성 중... Job ID: 12345"*)
3. API 서버에서 Worker로 작업 할당 후, 원본 메시지에 **쓰레드(Thread)**를 생성하여 각 단계(Phase)의 로그 및 Streaming Event를 실시간으로 업데이트.

---

## 2. Python MVP 코드 구조 (.md)

FastAPI, Celery/Redis, Docker 데몬을 제어하는 파이썬 기반의 백엔드 모듈 구조입니다.

```text
ai_cli_relay/
├── app/
│   ├── bot/                 # Slack Bolt 앱 핸들러 (UI 레이어)
│   │   ├── commands.py      # /ai run, /ai status 등 라우팅
│   │   └── events.py        # 버튼 클릭, 스레드 메시지 반응 핸들러
│   ├── api/                 # FastAPI (Orchestrator) 
│   │   ├── routes.py        # Webhook 및 내부 API 엔드포인트
│   │   └── langgraph_core/  # (통합시) Supervisor 및 Handoff State 정의
│   ├── worker/              # 비동기 작업 큐 핸들러 (Celery)
│   │   ├── tasks.py         # 큐에서 작업을 꺼내 Docker Sandbox 또는 로컬에서 실행
│   │   └── sandbox.py       # Docker SDK를 통한 컨테이너 생성 및 볼륨 마운트 제어
│   ├── adapters/            # CLI Adapter Layer (다양한 AI CLI 추상화)
│   │   ├── base.py          # BaseCLIAdapter (인터페이스)
│   │   ├── cursor.py        # Cursor CLI 제어 로직
│   │   └── claude.py        # Claude CLI 제어 로직
│   └── main.py              # FastAPI 및 Slack Socket Mode 시작 엔트리포인트
├── docker/
│   ├── Dockerfile.worker    # 안전하게 격리된 실행 환경 이미지
├── docker-compose.yml       # API, Redis, Slack Bot 실행 환경 세팅
└── requirements.txt
```

---

## 3. CLI Adapter 인터페이스 설계 (.md)

AI CLI 도구의 파편화를 막기 위해 `worker` 하위에 공통 CLI 인터페이스 클래스를 설계합니다.

### 3.1 Base Interface (`base.py`)

모든 CLI Wrapper가 구현해야 하는 순수 추상 클래스(ABC)입니다.

```python
from abc import ABC, abstractmethod
from typing import Iterator

class JobSpec:
    job_id: str
    prompt: str
    workspace_path: str
    env_vars: dict

class BaseCLIAdapter(ABC):
    
    @abstractmethod
    def submit(self, spec: JobSpec) -> str:
        """
        CLI 작업을 백그라운드 형태로 제출합니다.
        Returns: 내부 프로세스 ID 또는 컨테이너 Task ID
        """
        pass
        
    @abstractmethod
    def stream(self, job_id: str) -> Iterator[str]:
        """
        CLI의 표준 출력(stdout/stderr)을 제너레이터 형태로 반환하여 
        Slack으로 스트리밍하기 위한 엔드포인트입니다.
        """
        pass
        
    @abstractmethod
    def status(self, job_id: str) -> str:
        """
        현재 프로세스 상태를 반환합니다. (RUNNING, COMPLETED, FAILED)
        """
        pass
        
    @abstractmethod
    def cancel(self, job_id: str) -> bool:
        """
        해당 진행 중인 작업을 중단시킵니다. (SIGINT 또는 docker kill)
        """
        pass
```

### 3.2 구현 포인트 (Implementation Notes)
- `stream` 메서드는 Python `subprocess.Popen` 등을 통해 생성된 프로세스의 출력을 비동기 제너레이터로 감싸(yield) 상위 Worker Task로 전달합니다.
- Worker Task는 이 Yield 된 텍스트 청크(Chunk)들을 모아(Debouncing), 1~2초마다 Slack Thread에 업데이트(Slack API: `chat.update`)하여 과도한 API 호출(Rate Limit)을 피합니다.
