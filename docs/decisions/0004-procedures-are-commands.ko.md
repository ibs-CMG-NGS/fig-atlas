# 0004. 절차는 결정적 명령으로, AI는 같은 명령을 MCP로 부른다

- 상태: 채택
- 날짜: 2026-10-08

## 배경

프로젝트 생성, 번들 반입, 승격, 은퇴 절차는 CLAUDE.md와 에이전트 스킬 문서의 산문으로만 있었다. AI가 그 문서를 읽고 파일을 직접 편집해 수행했다. 그래서 AI 없이는 수행하기 어려웠고, AI마다 결과가 달라질 수 있었으며, 사람이 결과를 검증하기도 어려웠다. 사용자는 Claude Code 외에 Gemini CLI, Antigravity CLI, opencode도 쓴다(게이트 G4).

## 결정

- 기계적인 절차는 `fa` 명령으로 만든다: `fa new project|renderer`, `fa ingest bundle`, `fa promote`, `fa retire`.
- 변경 명령의 공통 규약:
  - `--dry-run`: 바뀔 파일과 diff만 보여 준다.
  - `--json`: 기계가 읽는 결과를 낸다.
  - 멱등: 결과가 이미 있으면 아무것도 바꾸지 않는다.
  - 예상하지 못한 파일은 덮어쓰지 않고 충돌로 보고한다.
  - 이동은 `git mv`로 한다.
  - 실행 뒤 빌드로 확인한다.
- AI는 같은 명령을 **MCP 도구**로 부른다(`fa mcp`).
  - 도구 정의는 CLI 파서에서 만든다.
  - 변경 도구는 `apply: true` 없이는 dry run이며, 에이전트는 diff를 사용자에게 보여 주고 동의를 받은 뒤 적용한다.
  - 서버는 표준 라이브러리만 쓴다(공식 `mcp` 패키지는 2.x로 API가 빠르게 바뀌는 중).
- 판단이 필요한 일은 명령으로 만들지 않는다: Case C 의도 해석, 스토리라인 서술, 개편 사유, 그림 검토.

## 결과

- 사람·Claude Code·다른 에이전트가 같은 결과를 낸다. 같은 과제를 CLI, opencode, Antigravity로 수행했을 때 파일이 같았고 그림은 바이트 단위로 같았다(2026-10-08, `docs/howto/ai_agents.md`).
- 스킬 문서는 "어떤 명령을 언제 + 판단 지점"만 남기고 줄인다.
- 지키는 장치:
  - `tests/test_repo_commands.py`: 멱등, 충돌, 골격의 전체 빌드
  - `tests/test_mcp_server.py`: 모든 도구 호출이 올바른 `fa` 명령인지
