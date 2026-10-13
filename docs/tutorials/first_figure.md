# 튜토리얼: 첫 그림 (15분)

저장소에 들어 있는 예제 데이터로 2패널 그림 하나를 처음부터 끝까지 만듭니다. 코드는 한 줄도 쓰지 않습니다. 명령으로 프로젝트를 만들고, 데이터 번들을 붙이고, 빌드하고, 인쇄 검사(preflight)가 알려 준 문제를 **config만 고쳐서** 해결합니다.

이 문서의 명령과 config 수정은 `tests/test_tutorials.py`가 CI에서 그대로 실행합니다. 그래서 이 문서대로 하면 같은 결과가 나옵니다.

## 준비

[README의 설치 절차](../../README.md)대로 환경을 만들고 활성화한 뒤(`conda activate fig-atlas`), 저장소 루트에서 시작합니다. `fa --help`가 명령 목록을 보여 주면 준비가 된 것입니다.

예제 데이터는 [`examples/`](../../examples/README.md)에 있습니다. 시뮬레이션으로 만든 두 번들입니다(실측값이 아님).

| 번들 | 내용 | 그림 모양 (`plot_type`) |
|---|---|---|
| `examples/dose_response` | 화합물 3종 × 용량 7단계 × 반복 4회의 세포 생존율 | 선 + 오차 띠 (`line_band`) |
| `examples/screen_hits` | 400개 항목의 효과 크기와 보정 P | 효과 대 유의성 산점도 (`threshold_scatter`) |

## 1. 프로젝트 만들기

먼저 무엇이 생길지 봅니다(`--dry-run`은 아무것도 쓰지 않습니다).

<!-- run -->
```bash
fa new project first-figure --dry-run
```

config, 분석 스크립트, figure spec 세 파일이 생긴다고 나옵니다(VS Code 빌드 목록 `.vscode/tasks.json`이 있는 저장소라면 그 목록의 한 줄도). 이제 실제로 만듭니다.

<!-- run -->
```bash
fa new project first-figure
```

`--domain lab --category exploratory`처럼 연구 단위를 주면 `configs/lab/exploratory/` 아래에 만들어집니다. 이 튜토리얼은 연습용이라 루트에 둡니다.

## 2. 데이터 번들 검사

번들은 `inputs/data.csv`(표)와 `metadata/metadata.yaml`(어떤 그림인지, `plot_params`)로 이루어진 폴더입니다. 그리기 전에 계약(필요한 열이 있는지)을 검사합니다.

<!-- run -->
```bash
fa bundle check examples/dose_response examples/screen_hits
```

번들마다 결과와 함께 어떤 그림인지(`plot_type`), 맞는 계약, 그릴 렌더러, 행 수가 나옵니다.

```text
ok           examples/dose_response
    plot_type line_band -> contract core.line_band, renderer fig_atlas.renderers:render_line_band, 84 rows
ok           examples/screen_hits
    plot_type threshold_scatter -> contract core.threshold_scatter, renderer fig_atlas.renderers:render_threshold_scatter, 400 rows
```

두 번들 모두 `ok`이고 계약 `core.line_band`, `core.threshold_scatter`에 맞습니다. 문제가 있으면 `ok` 자리에 오류·경고 수가, 그 아래에 무엇이 빠졌는지가 나옵니다. 범용 그림은 열 이름을 `plot_params`에서 지정합니다(예: `x_col: dose_uM`). 검사기는 지정된 열이 실제로 있는지 봅니다([표 번들 계약서](../contracts/table_bundle_contract.md)).

## 3. 번들을 패널로 붙이기

<!-- run -->
```bash
fa ingest bundle examples/dose_response --project first-figure
fa ingest bundle examples/screen_hits --project first-figure
```

각 명령은 `configs/config_first-figure.yaml`의 `plots:` 아래에 블록 하나를 쓰고 빌드합니다. 블록에는 렌더러가 읽는 **모든** 파라미터가 설명 주석과 함께 들어갑니다. 번들에서 온 값에는 "(from the bundle)" 표시가 붙습니다. 이제 이 파일이 그림을 조정하는 곳입니다. 파이썬 코드는 열 필요가 없습니다.

## 4. 빌드하고 확인하기

<!-- run -->
```bash
fa build first-figure --preflight
```

그림은 `outputs/first-figure/figures/figure_01_main/figure_01.png`(PDF·SVG도)에 있습니다. A4 본문 폭(184.6 mm)에 **실제 인쇄 크기로** 그려졌고, 패널 a·b의 태그는 각 패널의 바깥 경계(눈금 글자·축 제목 포함)에 맞춰져 있습니다.

`--preflight`는 인쇄 전 검사입니다. 결과에 경고가 하나 있습니다.

```
warn  cvd_indistinct  legend of axes[0] 'Viability after 48 h': #ff7f0e and #2ca02c look alike with protanomaly
```

패널 a의 주황과 초록이 적색약 독자에게는 거의 같은 색으로 보인다는 뜻입니다. 문제 위치는 `outputs/preflight/first-figure/`의 오버레이 그림에 번호로 표시됩니다.

## 5. config로 고치기

`configs/config_first-figure.yaml`에서 `dose_response` 블록의 `group_colors` 줄을 찾습니다. 주석이 이 키의 역할을 알려 줍니다("Colour per group"). 색각이상에 안전한 Okabe–Ito 팔레트로 바꿉니다.

<!-- replace: configs/config_first-figure.yaml | group_colors: {} -->
```yaml
    group_colors:                      # Colour per group: Okabe-Ito, safe for colour-blind readers
      "compound A": "#0072B2"
      "compound B": "#E69F00"
      vehicle: "#999999"
```

다시 빌드합니다.

<!-- run -->
```bash
fa build first-figure --preflight
```

이번에는 경고 없이 통과합니다(`0 error(s), 0 warning(s)`). 글자 크기, 축 범위, 임계값, 라벨 개수 같은 다른 값도 같은 방법으로 바꿉니다. 키마다 단위와 조정 방향이 주석으로 적혀 있습니다. 어떤 값이 어디서 왔는지는 `fa param explain first-figure plots.dose_response.band_alpha`처럼 확인합니다.

## 6. 그림 설명 쓰기

figure spec(`figure_specs/figure_01_first-figure.py`)에는 그림 제목, 패널 설명, 이 그림이 주장할 수 있는 범위가 들어갑니다. 빌드가 이 내용을 그림 폴더의 `README.md`로 내보냅니다. 제목을 바꿔 봅니다.

<!-- replace: figure_specs/figure_01_first-figure.py | title="Title of figure 1 -->
```python
    title="Two compounds lower viability with dose; a screen finds 51 hits",
```

<!-- run -->
```bash
fa build first-figure
```

> 실제 그림에서는 "51" 같은 결과 숫자를 손으로 쓰지 않습니다. 분석 스크립트에서 `claims.record("n_hits", n)`으로 기록하고 텍스트에는 `{n_hits}`라고 씁니다. 데이터가 바뀌면 설명도 따라 바뀝니다(AGENTS.md §4.5).

## 다음으로

- **내 데이터로**: 같은 형식의 번들을 `raw_data/<study>/<project>/` 아래에 두고 같은 명령을 씁니다. 지원하는 그림과 열 규칙은 `fa bundle contracts`와 [계약서 목록](../contracts/README.md)에 있습니다.
- **논문 그림으로**: 탐색 프로젝트를 `fa promote <project> --figure 1 --slug <slug>`로 논문 Figure로 승격합니다.
- **이미지 그림**: [현미경 이미지 튜토리얼](imaging_figure.md)
- **AI 에이전트와 함께**: 같은 과정을 에이전트가 MCP 도구로 할 수 있습니다([연결 방법](../howto/ai_agents.md)). 파일을 바꾸는 단계마다 먼저 diff를 보여 줍니다.
- **정리**: 연습 프로젝트를 지우려면 생성된 세 파일(`configs/config_first-figure.yaml`, `analysis/first-figure_analysis.py`, `figure_specs/figure_01_first-figure.py`), `outputs/first-figure/`를 지웁니다. VS Code 빌드 목록이 있는 저장소라면 `.vscode/tasks.json`에서 그 이름도 지웁니다.
