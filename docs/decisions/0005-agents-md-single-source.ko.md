# 0005. 규칙의 단일 정본은 루트 `AGENTS.md`

- 상태: 채택
- 날짜: 2026-10-08

## 배경

같은 규칙이 `CLAUDE.md`와 `.agents/AGENTS.md`에 두 벌 있었다(빈 줄 두 개만 다름). 규칙을 바꿀 때마다 두 곳을 고쳐야 했다. 두 파일 모두 이미 삭제된 예시(`configs/config_pilot-test.yaml`)와 옛 이름(`config_paper_main.yaml`)을 가리키고 있었는데, 확인하는 장치가 없었다. 에이전트마다 읽는 파일도 다르다.

| 에이전트 | 읽는 파일 |
|---|---|
| Claude Code | `CLAUDE.md` |
| Gemini CLI | 기본 `GEMINI.md` |
| Codex, opencode, Cursor, Copilot 등 | 루트 `AGENTS.md`([agents.md](https://agents.md/) 관례) |
| Antigravity CLI | `.agents/AGENTS.md`와 루트 `AGENTS.md` 모두 (2026-10-08 확인) |

## 결정

- 규칙은 저장소 루트의 `AGENTS.md` 한 곳에 둔다. 사람도 이 파일을 규칙 문서로 읽는다.
- `CLAUDE.md`는 `@AGENTS.md`로 가져오기만 한다.
- `.gemini/settings.json`의 `context.fileName`이 Gemini CLI에게 `AGENTS.md`를 읽게 한다.
- 스킬 문서(`.agents/skills/*/SKILL.md`)는 절차와 판단 지점만 담고, 규칙은 `AGENTS.md`를 가리킨다.
- 규칙의 이유는 이 폴더(ADR)에 둔다.
- 개인 AI 메모리에 있던 설계 결정(0001, 0002)은 여기로 옮겼다. 연구 내용에 관한 메모(실험 설계, 표적 선택 기준)는 스토리라인과 데이터 요청 문서의 몫이다.

## 결과

- 규칙을 한 번만 고치면 모든 에이전트와 사람이 같은 규칙을 본다.
- 지키는 장치 `tests/test_agent_docs.py`가 다음을 확인한다.
  - `CLAUDE.md`가 `AGENTS.md`를 가져오기만 하는지
  - `AGENTS.md`와 스킬 문서가 가리키는 저장소 경로와 `fa` 명령이 실제로 있는지
  - Gemini 설정이 `AGENTS.md`를 가리키는지
- 코드 주석과 분석 스크립트의 "CLAUDE.md §x" 참조 일부는 그대로 두었다. 그림을 만드는 파일의 내용 해시가 바뀌면 그 그림들이 "낡음"으로 표시되기 때문이다. `CLAUDE.md`가 `AGENTS.md`를 가져오므로 그 참조도 같은 규칙에 닿는다.
