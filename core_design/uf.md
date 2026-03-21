# Stage 7: 단위기능(UF) 도출 (Unit Functions)

## UF-03-A: Context Volume Mounter (가장 중요)
- **UF-ID:** UF-03-A
- **Parent IF:** IF-03
- **Goal:** 호스트 머신의 UID/GID를 유지하고 지정된 작업 경로를 적절한 권한(ro/rw)으로 Docker 컨테이너에 마운트하여 컨테이너 환경의 `docker-py` HostConfig를 반환한다.
- **I/O Contract:**
    - `Input`: `workspace_path`: str (절대 경로), `mount_type`: Enum(READ_ONLY, READ_WRITE)
    - `Output`: `docker_bids`: dict (Docker SDK Volumes 인자), `uid_spec`: str (`$UID:$GID` 포맷)
- **Algorithm Summary:** 
  1. `os.getuid()`와 `os.getgid()`로 호스트 유저 식별자 추출.
  2. `mount_type` 제어문에 따라 바인드 마운트 딕셔너리(`binds`) 생성 시 `'mode': 'ro'` 또는 `'rw'` 할당.
  3. 컨테이너 내부 타겟은 항상 `/app/workspace`로 고정.
- **Edge Cases:** 
  - 윈도우(WSL 제외) 환경에서 UID/GID 추출 불가 (`os.getuid` AttributeError 에러 처리 필요 -> fallback `None`).
  - `workspace_path`가 시스템 루트(`/`)이거나 허용되지 않은 상위 디렉토리인 경우 Path Traversal 방지 로직 필요.
- **Verification Plan:** unit test (`test_volume_mounter.py`에서 권한, OS 호환성 테스트)
- **Evidence Pack Fields:** `scenario_id`, `run_id`, `mount_config`, `commit_sha`

## UF-04-B: Slack Message Updater & Throttler
- **UF-ID:** UF-04-B
- **Parent IF:** IF-04
- **Goal:** 짧은 시간에 쏟아지는 CLI 출력 로그를 Slack API Rate limit에 걸리지 않도록 디바운스(Debounce)하여 쓰레드를 갱신한다.
- **I/O Contract:**
    - `Input`: `log_chunk`: str, `job_id`: str (쓰레드 식별자 용도)
    - `Output`: `api_call_count`: int (성공 여부 반환)
- **Algorithm Summary:** 
  1. 텍스트 버퍼에 `log_chunk`를 누적하고 `last_update_time`을 확인한다.
  2. `current_time - last_update_time >= UPDATE_INTERVAL (1.0s)` 이면 슬랙 `chat.update` 호출.
  3. 전체 누적 길이가 한계치(3900자 보수적 제한)에 도달하면 파일 객체로 변환하여 `files.upload` 호환 로직(향후 구축)으로 덤프.
- **Edge Cases:** 
  - API 호출 타임아웃/Rate Limit 에러 시 Exponential Backoff로 재시도.
  - 컨테이너 종료 이벤트 시 버퍼에 남은 잔여 텍스트(flush) 누락 방지 처리.
- **Verification Plan:** 아시오(asyncio) 기반 제너레이터 시뮬레이터로 100회 동시 메시지 주입 시 update 호출이 스로틀링 되는지 검증.
- **Evidence Pack Fields:** `scenario_id`, `run_id`, `slack_api_metrics`, `environment`

## UF-05-A: Skill Metadata Parser
- **UF-ID:** UF-05-A
- **Parent IF:** IF-05
- **Goal:** 요청받은 스킬 이름 목록을 기반으로 로컬 스킬 디렉토리에서 Markdown 파일을 읽어, 에이전트에 주입할 최종 System Prompt 텍스트를 구성한다.
- **I/O Contract:**
    - `Input`: `skill_names`: list[str], `skills_base_dir`: str
    - `Output`: `merged_skill_prompt`: str
- **Algorithm Summary:** 
  1. `skill_names` 순회.
  2. `os.path.join(skills_base_dir, skill_name, "SKILL.md")` 확인.
  3. YAML Frontmatter(`---` 사이의 값) 파싱 후 로깅, 본문(Markdown)을 `merged_skill_prompt` 문자열에 누적 병합.
- **Edge Cases:** 
  - 존재하지 않는 스킬 이름 요청 시 -> ValueError 발생시켜 Orchestrator단에서 빠른 실패(Fast-fail) 유도.
  - 빈 본문이나 잘못된 YAML 형식의 스킬 파일 대응 (기본 텍스트 파싱 폴백).
- **Verification Plan:** Mock 파일 시스템으로 3개의 임의 SKILL.md 파일 생성 후 병합된 텍스트의 누락/간섭 여부 테스트.
- **Evidence Pack Fields:** `scenario_id`, `run_id`, `parsed_skills`
