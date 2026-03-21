# Stage 6: 통합기능 분해 (IF Decomposition)

## 의존성 그래프 (Dependency Graph)

```mermaid
graph TD
    UI[IF-01: Slack UI Interface] --> ORCH[IF-02: Orchestrator Engine]
    ORCH --> |Handoff| SB[IF-03: Sandbox Worker Manager]
    SB --> |Container SDK| UF_03_A[UF-03-A: Context Volume Mounter]
    SB --> |Exec| UF_03_B[UF-03-B: CLI Execution Controller]
    UF_03_B --> |Stream| BRIDGE[IF-04: CLI Adapter Stream Bridge]
    BRIDGE --> |Debounce| UF_04_A[UF-04-A: Log Aggregator (Buffer)]
    UF_04_A --> |Rate Limit| UF_04_B[UF-04-B: Slack Message Updater]
    ORCH --> |Load Skills| SKILL[IF-05: Skill Loader]
    SKILL --> UF_05_A[UF-05-A: Skill Metadata Parser]
```

## 분해된 단위기능 (Unit Function 후보)

1. **UF-03-A: Context Volume Mounter**
   - **역할:** 호스트 `workspace_path`와 현재 사용자의 UID/GID를 읽어 Docker Run 설정(Volumes, User옵션)을 생성한다. `write_permission`에 따라 읽기전용 옵션을 부여한다.
2. **UF-03-B: CLI Execution Controller**
   - **역할:** 특정 CLI 모드(Cursor, Claude 등)에 특화된 엔트리포인트 명령어를 샌드박스 내부에서 기동한다. (예: `claude run --workspace ...`)
3. **UF-04-A: Log Aggregator (Buffer)**
   - **역할:** Popen/Docker Stream에서 나오는 raw bytes를 받아 줄바꿈(`\n`) 단위로 파싱하여 큐(Buffer)에 누적한다.
4. **UF-04-B: Slack Message Updater & Throttler**
   - **역할:** Buffer에 누적된 텍스트를 최소 X초 간격(Debounce)으로 Slack API에 통신(`chat.update`)하여 업데이트하며 4,000자 제한을 초과하는 텍스트는 Truncate하거나 별도 파일 업로드 큐로 뺀다.
5. **UF-05-A: Skill Metadata Parser**
   - **역할:** 로컬의 `skills/{skill_name}/SKILL.md` 파일들을 읽어 Frontmatter를 제외한 핵심 Prompt Rule을 추출, 병합 텍스트로 반환한다.
