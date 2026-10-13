# How-to: AI 에이전트에 fig-atlas 연결하기 (`fa mcp`)

fig-atlas의 절차(새 프로젝트, 번들 반입, 빌드, 검사, 승격, 은퇴)는 모두 `fa` 명령입니다. 사람은 명령을 직접 실행하고, AI 에이전트는 같은 명령을 **MCP(Model Context Protocol) 도구**로 호출합니다. MCP는 에이전트가 외부 도구를 부르는 공통 규약이라, 서버 하나로 Claude Code, Gemini CLI, opencode, Antigravity, Cursor, Codex 등 여러 에이전트가 같은 도구를 씁니다.

```bash
fa mcp                     # 또는: python -m fig_atlas mcp [--root <저장소>]
```

에이전트가 이 명령을 자식 프로세스로 띄우고 표준 입출력으로 대화합니다. 추가로 설치할 패키지는 없습니다.

## 1. 도구 목록

| 도구 | 하는 일 | 파일을 바꾸나 |
|---|---|---|
| `fa_list`, `fa_renderers`, `fa_bundle_contracts` | 프로젝트, 그릴 수 있는 그림, 번들 계약 목록 | 아니오 |
| `fa_bundle_check` | 번들을 계약으로 검사 | 아니오 |
| `fa_status`, `fa_impact`, `fa_lineage` | 낡은 그림, 파일의 영향 범위, 그림의 출처 | 아니오 |
| `fa_lint`, `fa_claims` | 안 읽힌 config 키·오타, 손으로 쓴 수치 | 아니오 |
| `fa_build`, `fa_verify` | 빌드(preflight 포함)와 검증 | `outputs/`만 |
| `fa_figure_images` | 빌드된 그림과 preflight 오버레이를 이미지로 돌려줌 | 아니오 |
| `fa_new_project`, `fa_new_renderer`, `fa_ingest_bundle`, `fa_promote`, `fa_retire` | 프로젝트·렌더러 생성, 번들 반입, 승격, 은퇴 | **예** (아래 2절) |

도구 이름·인자·설명은 `fa` 명령의 도움말에서 자동으로 만들어지므로 CLI와 어긋나지 않습니다(`tests/test_mcp_server.py`가 모든 도구 호출이 올바른 `fa` 명령이 되는지 확인합니다). 결과는 각 명령의 `--json` 출력입니다.

## 2. 파일을 바꾸는 도구의 안전장치

- `apply`를 주지 않으면 **dry run**입니다. 아무것도 쓰지 않고 바뀔 파일과 diff만 돌려줍니다.
- 에이전트는 그 diff를 사용자에게 보여 주고, 사용자가 동의한 뒤에만 `apply: true`로 다시 부릅니다.
- 이 도구들은 MCP에서 "파괴적(destructive)"으로 표시되므로, 대부분의 에이전트는 실행 전에 사용자 승인을 묻습니다.
- 명령 자체의 규칙도 그대로입니다. 결과가 이미 있으면 아무것도 바꾸지 않고(멱등), 예상하지 못한 파일은 덮어쓰지 않고 충돌로 보고합니다.

## 3. 에이전트별 설정

아래 예시의 `<python>`은 fig-atlas가 설치된 Python입니다. conda 환경이면 `conda env list`가 보여 주는 `fig-atlas` 환경 폴더의 python (예: Windows `C:\Users\<사용자>\miniconda3\envs\fig-atlas\python.exe`; 환경을 켠 셸에서 `python -c "import sys; print(sys.executable)"`로도 확인)입니다. `fa`가 PATH에 있으면 `<python> -m fig_atlas` 대신 `fa`를 써도 됩니다. Windows conda 환경의 DLL 경로(`Library/bin`)는 서버가 자식 프로세스에 넣어 주므로 따로 설정하지 않아도 됩니다. 에이전트를 저장소 밖에서 시작한다면 `--root <저장소 경로>`를 `mcp` 앞에 넣습니다.

**opencode** (검증함, 2026-10-08) — 저장소의 `opencode.json` 또는 `OPENCODE_CONFIG`가 가리키는 파일:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "fig-atlas": {
      "type": "local",
      "command": ["<python>", "-m", "fig_atlas", "mcp"],
      "enabled": true
    }
  }
}
```

**Antigravity CLI** (검증함, 2026-10-08):

```bash
agy mcp add fig-atlas -- <python> -m fig_atlas mcp
```

**Claude Code** (검증함, 2026-10-13 — `--mcp-config` 파일로):

```bash
claude mcp add fig-atlas -- <python> -m fig_atlas mcp
```

**Gemini CLI** — `~/.gemini/settings.json` 또는 저장소의 `.gemini/settings.json`:

```json
{ "mcpServers": { "fig-atlas": { "command": "<python>", "args": ["-m", "fig_atlas", "mcp"] } } }
```

**Cursor** — `.cursor/mcp.json`: Gemini CLI와 같은 `mcpServers` 형식입니다.

**Codex CLI** — `~/.codex/config.toml` (Windows: `C:\Users\<사용자>\.codex\config.toml`, 없으면 새로 만듭니다):

```toml
# fig-atlas 도구를 Codex에 연결합니다.
[mcp_servers.fig-atlas]
# fig-atlas가 설치된 Python. Windows 경로는 슬래시(/)로 쓰거나 작은따옴표로 감쌉니다
# (큰따옴표 안의 \ 는 TOML에서 특수 문자입니다).
command = 'C:\Users\<사용자>\miniconda3\envs\fig-atlas\python.exe'
args = ["-m", "fig_atlas", "mcp"]
# 빌드(fa_build)는 그림에 따라 1분을 넘길 수 있습니다. 도구 하나가 기다리는 최대 시간(초)을 늘려 둡니다.
tool_timeout_sec = 600
```

Codex는 저장소의 `AGENTS.md`를 스스로 읽으므로 규칙 파일은 따로 연결하지 않습니다. 저장소 폴더에서 `codex`를 시작한 뒤 `/mcp`로 `fig-atlas`가 보이는지 확인하고, "fig-atlas 도구로 프로젝트 목록을 보여 줘"라고 해 봅니다(4절). 이 설정은 Codex 문서의 형식을 따른 것으로, 이 저장소에서는 아직 실행해 보지 않았습니다(사용성 시험에서 확인 예정).

"검증함"이 없는 항목은 각 에이전트 문서의 형식을 따른 것이고, 이 저장소에서 직접 실행해 보지는 않았습니다.

## 4. 연결 확인

에이전트에게 "fig-atlas 도구로 프로젝트 목록을 보여 줘"라고 하면 `fa_list`가 호출되어야 합니다. 에이전트의 MCP 목록 명령(`opencode mcp list`, `agy mcp list`, `claude mcp list` 등)에서 `fig-atlas`가 연결됨으로 보이는지도 확인합니다.

## 5. 에이전트가 따르는 규칙

서버는 연결할 때 짧은 안내를 보내고, 자세한 규칙은 저장소의 [`AGENTS.md`](../../AGENTS.md)(원본 데이터는 읽기 전용, 시각 값은 모두 주석 달린 config에)를 가리킵니다. 판단이 필요한 일, 즉 목업에서 그림 의도 해석하기(Case C), 스토리라인 서술, 개편 사유 쓰기는 명령이 대신하지 않습니다. 그 부분은 에이전트와 사람의 몫입니다.

## 6. 교차 에이전트 시험 (2026-10-08)

같은 과제(새 탐색 프로젝트 → 번들 검사 → 반입 → preflight 빌드 → 그림 보기 → 논문 Figure 1로 승격)를 세 가지로 수행했습니다.

- (a) 사람이 `fa` 명령으로
- (b) opencode가 MCP 도구만으로(셸·파일 편집 도구는 끔)
- (c) Antigravity CLI가 MCP 도구만으로

세 결과의 config·분석 스크립트·figure spec·`.vscode/tasks.json`이 모두 같았고, 빌드된 PDF·PNG도 바이트 단위로 같았습니다. opencode의 호출 기록에서는 파일을 바꾸는 단계마다 dry run이 먼저 오고 그다음 `apply: true`가 왔습니다. 두 에이전트 모두 `fa_figure_images`로 받은 그림에서 Venn 숫자(A만 18, B만 15, 공통 12)를 읽어 냈습니다.

2026-10-13에는 같은 과제를 Claude Code(claude-sonnet-5)로 다시 했습니다. 셸·파일 도구를 끄고(`--strict-mcp-config --disallowedTools ...`) MCP 도구만 썼고, 프롬프트에서 미리 승인하지 않았습니다. 에이전트는 바꾸는 세 단계마다 dry run 결과를 보여 주고 사람에게 물었으며, 사람이 승인한 뒤에만 `apply: true`로 다시 불렀습니다. 그날 코드로 다시 한 사람(CLI) 실행과 비교해 여섯 파일이 모두 바이트 단위로 같았습니다.
