---
name: "ingest_plot"
description: "Ingest any custom python plotting script and raw data, converting it into a compliant plot bundle and integrating it into the figure atlas."
---

# Ingest Plot Agent Skill (데이터 및 소스 반입 자동화 지침)

이 지침서는 사용자로부터 임의의 데이터와 파이썬 시각화 스크립트(`data + plotting`)를 받았을 때, 이를 본 프로젝트의 다중 피규어 아틀라스 템플릿 규격에 맞게 분할하여 반입하고 자동 빌드 및 검증을 마치는 상세 프로토콜입니다.

규칙의 정본은 저장소 루트의 `AGENTS.md`입니다. 이 문서는 반입 절차와 판단 지점만 다루고, 기계적인 단계는 `fa` 명령에 맡깁니다(MCP로 연결된 에이전트는 같은 명령을 `fa_*` 도구로 부릅니다).

| 단계 | 명령 |
|---|---|
| 새 프로젝트(config·분석 스크립트·spec·빌드 목록) | `fa new project <name> [--domain d --category exploratory]` |
| 번들 검사 | `fa bundle check raw_data/<...>/<bundle>` |
| 번들을 config의 `plots:` 블록으로 반입(주석 포함 전체 파라미터) + 빌드 | `fa ingest bundle raw_data/<...>/<bundle> --project <name>` |
| 새 렌더러 골격(스키마·테스트·export, 번들 유형 등록) | `fa new renderer <plot> [--plot-type <type>]` |
| 렌더러의 전체 파라미터 블록 출력 / 빠진 키 채우기 | `fa param scaffold <renderer>` / `fa param sync <project> --apply` |
| 빌드 + 인쇄 검사 | `fa build <name> --preflight` |

파일을 바꾸는 명령은 모두 `--dry-run`으로 먼저 보여 줄 수 있습니다. 판단이 필요한 부분 -- 대상 프로젝트 확인, Case A의 렌더링 코드 이식, Case C의 의도 해석과 확정 게이트, 그림 검토 -- 은 아래 절차를 따릅니다.

---

## 7단계 반입 & 통합 프로토콜 (7-Phase Ingest & Integrate Protocol)

### Phase 1: 대상 프로젝트 식별 및 상태 파악
1. 사용자에게 이 인제스트 작업이 어떤 **프로젝트**에 속하는지 명칭(`<project_name>`)을 확인합니다.
   * 예: 기존 프로젝트에 플롯 추가인지, 신규 프로젝트 생성(`fa new project`)인지 확인.
   * **Study 네이밍 규칙**: 대상 raw_data 상위 폴더(`raw_data/<study>/`) 아래에 이미 여러 개의 형제 번들(예: `fig1-...`, `fig2-...`)이 존재해 하나의 study를 이루는 경우, `<project_name>`은 **항상 study slug로 시작**해야 합니다 (예: `stress-mouse-acute-1d-de-go`, `stress-human-acute-1d-de-go`). study slug 뒤에 곧바로 organism/cohort 등 구분자를 붙이고, 그 다음에 나머지 설명을 붙입니다. 이렇게 해야 `configs/`, `analysis/`, `figure_specs/`, VS Code 빌드 태스크의 프로젝트 피커에서 형제 프로젝트들이 알파벳순으로 함께 정렬됩니다.
   * 새 프로젝트를 확정한 뒤에는 `raw_data/<study>/README.md`(있다면)의 매핑 표에 `raw bundle folder → project_name → organism/설명` 행을 추가/갱신합니다. 없다면 새로 만들 것을 사용자에게 제안합니다.
2. 명칭이 확정되면 대응할 대상 파일들을 특정합니다:
    * **설정 파일**: `configs/config_<project_name>.yaml`
    * **분석 파일**: `analysis/<project_name>_analysis.py`
    * **피규어 스펙**: `figure_specs/figure_<번호>_<project_name>.py`
3. **데이터 상태별 분기 처리 (Branching Logic)**:
   * **Case A (비정형 소스코드 + 날 데이터)**: Phase 2부터 Phase 7까지 순차적으로 전체 단계를 실행하여 데이터 격리, 메타데이터 생성 및 통합을 수행합니다.
   * **Case B (규격 번들이 이미 raw_data 하위에 존재하여 코드 및 레이아웃 통합만 요구하는 경우)**:
     * **Phase 3(데이터 격리) 및 Phase 4(메타데이터 생성)를 생략(Skip)**합니다.
     * 먼저 `fa bundle check raw_data/<...>/<bundle>`로 번들을 검사합니다. 구조, `plot_type`에 맞는 계약(필수 열), 그릴 렌더러를 확인합니다. **오류**는 렌더러가 꼭 필요로 하는 열이 없다는 뜻이므로, 원본 데이터를 고치지 말고 사용자에게 보고합니다. **경고**(계약서가 필수라고 적은 나머지 열 누락)는 보고만 하고 진행할 수 있습니다.
     * 설치된 렌더러가 그 `plot_type`을 그리면(`fa bundle contracts`로 확인) **`fa ingest bundle raw_data/<...>/<bundle> --project <name>`** 한 명령으로 Phase 5–7을 대신합니다. 새 프로젝트라면 먼저 `fa new project`를 실행합니다. 이 명령은 config의 `plots.<name>`에 렌더러, 번들 경로, 스키마의 모든 파라미터(번들 값이 있으면 그 값, "(from the bundle)" 표시)를 주석과 함께 쓰고 빌드로 확인합니다. `fa new project`로 만든 분석 스크립트는 `draw_plots`로 이 블록을 그리므로 코드를 고칠 필요가 없습니다. `--dry-run`으로 먼저 diff를 보여 줄 수 있습니다.
     * 번들 값은 출발점입니다. 번들에는 화면용 글자 크기가 들어 있는 경우가 많으므로 `fa build <project> --preflight`로 겹침·잘림을 확인하고 글자 크기를 config에서 조정합니다.
     * 그리는 렌더러가 없거나 스크립트가 직접 배치하는 그림이면, 이미 조준된 `metadata/metadata.yaml` 및 `inputs/data.csv`를 읽고 **Phase 5(렌더링 코드 자가 작성 및 이식)**, **Phase 6(설정 파일 및 스펙 등록)**, **Phase 7(빌드 실행 및 성공 확인)**을 손으로 진행합니다.
   * **Case C (데이터 + 그림 의도만 있고 코드 없음 — 목업/캡처본/자연어 기반)**: 사용자가 원시 데이터와 함께 "이런 데이터를 이렇게 그리고 싶다"는 **참조 이미지(캡처/목업/스케치)나 자연어 설명**만 제공한 경우. 렌더링 코드를 사용자 코드에서 추출하는 대신 **LLM이 데이터 + 참조 이미지로부터 렌더러를 합성**합니다. Phase 2가 "코드 분석" → **"의도 추론"**으로 바뀌고, 코드 생성 전 **의도 확정 게이트**와 생성 후 **연구자 검토 루프**(기본은 사람이 목업과 대조·피드백; 자동 대조는 선택)가 추가됩니다. 상세는 아래 [Case C 전용 절차](#case-c-전용-절차-데이터--그림-의도-기반-합성) 참조.

### Phase 2: 입력 스크립트 분석
1. 사용자가 전달한 파이썬 스크립트의 실행 논리를 다음 세 가지 파트로 분석합니다.
   * **데이터 로드 및 가공 (Data Ingestion)**: 로컬 파일 경로, 결측값 처리, 특정 컬럼 필터링 등.
   * **시각화 파라미터 (Plot Parameters)**: 축 범위(`xlim`, `ylim`), 그래프 색상, 마커 크기, 임계치 등.
   * **플로팅 로직 (Plot Rendering)**: Matplotlib/Seaborn 함수 호출 및 축 눈금 세팅.

### Phase 3: 원시 데이터 파일 격리 및 정제
1. 사용자의 원본 데이터 파일을 프로젝트 내부 `raw_data/<project_name>/<bundle_name>/inputs/data.csv` (또는 `.tsv`) 경로로 복사/이동합니다. (config의 `raw_root`가 `raw_data/<project_name>`을 가리키므로 그 하위에 번들을 둡니다.)
2. **주의**: 데이터 내의 값들을 절대로 인위적으로 변형하지 않고 원본 그대로 보존해야 합니다. 단, 데이터 로드 시 빈 행 제거 등 아주 기본적인 가공은 허용됩니다.

### Phase 4: 메타데이터 추출 및 파일 작성
1. 분석한 소스코드에서 시각화 매개변수들을 자동으로 식별하여 다음 위치에 야믈(`YAML`) 포맷으로 작성합니다:
   * **경로**: `raw_data/<project_name>/<bundle_name>/metadata/metadata.yaml`
2. **형식**:
   ```yaml
   figure_id: <plot_name>
   figure_title: <Title of the Plot>
   plot_type: <volcano | heatmap | pca | custom>
   plot_params:
     # 소스코드에서 추출한 값들
     x_min: ...
     x_max: ...
     labels_title: ...
     # 기타 커스텀 색상 및 임계값
   ```

### Phase 5: 렌더링 코드 리팩토링 및 이식
0. **먼저 재사용 여부를 확인합니다.** `fa renderers`가 그릴 수 있는 이름을 모두 보여 줍니다(코어, 팩, 레시피). 이름으로 그리면 렌더러가 어느 패키지에 있는지 몰라도 됩니다:
     `import fig_atlas; fig_atlas.render("volcano", ax, df, params)`
   * **기존 플롯 타입과 동일**하면 새로 작성하지 말고 그대로 씁니다. `params`로 차이를 표현합니다.
   * **렌더러는 모양 단위입니다.** 막대·선·산점도·히트맵·점 행렬처럼 분야와 무관한 모양은 처음 쓰는 데이터가 오믹스여도 `fig_atlas/renderers/<plot_name>.py`(코어)에 둡니다. 분야 팩(오믹스 등)에는 그 분야에만 의미 있는 모양(서열 로고, 유전체 트랙)만 렌더러로 두고, 나머지 분야 지식은 데이터 읽기·계약·레시피·분석 도우미로 둡니다. 새 렌더러는 그 패키지의 `__init__.py`에서 export 하여 라이브러리 자산으로 남깁니다. 코어 렌더러는 팩을 import하지 않습니다(`tests/test_core_boundary.py`).
   * **새 플롯이 기존 범용 렌더러의 모양에 분야 기본값만 얹은 것이면 렌더러 대신 레시피를 만듭니다**(`fig_atlas/recipes.py`). 예를 들어 effect size 대 P 그림은 `threshold_scatter` 레시피입니다. 레시피는 범용 렌더러 이름, 열 역할·변환·색 같은 기본값, 프로젝트가 쓰는 파라미터 이름(`surface`)과 범용 이름의 대응(`aliases`)을 담은 데이터입니다. 오믹스의 volcano·ma_plot이 예시입니다(`fig_atlas_omics/renderers/volcano.py`의 `RECIPE`). 팩의 레시피는 `fig_atlas.recipes` 진입점으로 등록합니다.
   * **새 렌더러는 스키마가 필수입니다.** 모듈에 `SCHEMA = Schema("<plot_name>", params=[Param(...), ...])`를 선언하고 `render_*` 함수에 `@uses_schema(SCHEMA)`를 붙입니다. 코드가 읽는 키마다 `Param`(역할, 숫자면 단위, 필요하면 조정 방향)이 있고, 기본값은 코드의 `params.get(key, 기본값)`과 같아야 합니다(계산되는 기본값은 `CODE_DEFAULT`). `tests/test_renderer_schemas.py`가 누락·불일치를 막으며, 기존 렌더러(예: `fig_atlas/renderers/funnel.py`)가 형식 예시입니다.
   * **새 렌더러는 `fa new renderer <plot_name> [--plot-type <type>] [--doc "..."]`로 시작합니다**(`--dry-run`으로 먼저 확인). 스키마가 있는 모듈 골격(자리표시 그림), `tests/renderers/test_<plot_name>.py`, 패키지 `__init__.py` export를 만들고, `--plot-type`을 주면 그 `plot_type`의 번들을 이 렌더러가 그리도록 등록해 `fa ingest bundle`이 찾게 합니다. 기본 위치는 코어이고, 분야에만 의미 있는 모양일 때만 `--package fig_atlas_omics.renderers`처럼 팩을 지정합니다. 자리표시 그림을 실제 그림으로 바꾼 뒤 `tests/test_renderer_schemas.py`, `fa lint --hardcoded`, `fa inventory`를 실행합니다.
   * **새 렌더러를 처음부터 설계하기 전에, 해당 번들에 `scripts/figure.py`(cmg-seqviewer 원본 인라인 렌더링 코드)가 있는지 반드시 먼저 확인합니다.** 있으면 그 로직(색상, 막대/점 방향, 라벨 배치, 기본 제목 등 디자인 전체)을 그대로 포팅하는 것이 출발점이며, `plot_params`만 보고 디자인을 새로 지어내지 않습니다 — metadata의 파라미터 값만으로는 UP/DOWN을 나란히 배치할지 0 기준으로 발산시킬지 같은 시각적 설계까지는 알 수 없습니다. `scripts/figure.py`가 없을 때만(Case C처럼 진짜 코드가 없는 경우) 데이터·의도로부터 합성합니다.
1. 소스코드의 플로팅 부분을 캡슐화하여 다음 서명을 가지는 렌더링 함수로 변환합니다.
   ```python
   def render_<plot_name>(ax, df, params):
       # 또는 Heatmap처럼 fig(또는 SubFigure)가 꼭 필요한 경우 def render_<plot_name>(fig, df, params):
   ```
2. **렌더링 코드 필수 규칙**:
   * 하드코딩된 폰트 크기, 제목, 축 한계값은 물론이고 **색상, 라인 스타일/두께/투명도, 범례 위치(`loc=`), marker/edge 스타일, grid on/off, 참조선(cutoff/threshold/zero-line) 표시 여부 등 렌더링에 관여하는 모든 리터럴**을 절대 그대로 쓰지 말고, 매개변수 딕셔너리(`params.get('param_name', default)`)에서 조회하여 동적 렌더링 하도록 수정합니다. `default` 값은 포팅 전 원본 스크립트의 값과 동일하게 맞춰 시각적 회귀가 없도록 합니다.
   * `ax.tick_params`나 `ax.set_xticklabels`에 적용되는 틱 사이즈나 폰트는 글로벌 설정(`rcParams`) 혹은 글로벌 오버라이드 매개변수(`axes_label_size`, `tick_label_size`, `title_size`)를 물려받도록 구현합니다.
   * **Self-audit (Phase 6로 넘어가기 전 필수)**: 작성한 렌더러 파일에서 `color=`, `c=`, `alpha=`, `linewidth=`/`lw=`, `linestyle=`/`ls=`, `edgecolor=`, `loc=`, `fontsize=`(글로벌 오버라이드 키가 아닌 숫자 리터럴), `"#"`로 시작하는 색상 코드, 불리언 표시 스위치가 없는 `ax.axhline`/`ax.axvline`/`ax.grid` 호출 등을 훑어, `params.get()`을 거치지 않은 리터럴이 남아있지 않은지 확인합니다. 남아있으면 Phase 6로 넘어가기 전에 파라미터화합니다.
3. `analysis/<project_name>_analysis.py`는 데이터 로드 + 파라미터 병합 + 레이아웃 조립만 담당하고, 실제 렌더링은 라이브러리 렌더러 호출로 처리합니다. 공용 데이터 헬퍼도 재사용하세요: `from fig_atlas import get_config, load_bundle_params`.
4. 분석 스크립트의 산출물은 `CONFIG.output_root` 하위에 저장하고(하드코딩 `project_root/"outputs"` 금지), 원시 데이터는 `CONFIG.raw_root`를 그대로 사용합니다(`project_root / raw_root` 이중 결합 금지).

### Phase 6: 설정 파일 및 피규어 스펙 등록
1. 프로젝트 파일은 `fa new project`가 만듭니다. `project:` 블록(`name`, `figure_count`, `spec_pattern`, `analysis_script`), `paths.raw_root`, figure spec, `.vscode/tasks.json` 등록까지 들어 있습니다. 손으로 만들 때는 `spec_pattern`과 `analysis_script`를 빠뜨리지 않습니다(없으면 빌드가 예제 프로젝트로 되돌아갑니다). `figures_root` 등 출력 경로는 지정하지 않으면 `outputs/<project_name>/...`가 됩니다.
   * **`plots:` 블록은 렌더러가 읽는 키 전부를 담습니다**(AGENTS.md §1.2, docs/decisions/0002). 번들 `metadata.yaml`에 `plot_params`가 있어도 config에는 일부 override만 적는 것은 금지입니다. 번들의 `plot_type`을 그리는 렌더러가 있으면 `fa ingest bundle`이 이 블록을 주석과 함께 써 줍니다. 그렇지 않으면 `fa param scaffold <renderer>` 출력을 붙여 넣고 값만 고칩니다. 예시는 `configs/config_pilot-imaging.yaml`의 `plots:`입니다.
   * **Mandatory Rich In-Line Comments**: The config file is the researcher's self-service UI for visual tuning. Every visual parameter, layout ratio, and threshold MUST be documented with descriptive English in-line comments (`# ...`) explaining its visual role, unit/range, and tuning effects (increase/decrease). Never strip or overwrite existing comments (Zero Comment Stripping).
   * **도구**: 빌드 후 `fa param sync <project>`(미리보기) / `--apply`가 빌드가 기본값으로 대신한 키를 그 값 그대로(그림 변화 없음) 주석과 함께 config에 추가하고, `fa lint <project>`가 남은 기본값 사용·안 읽힌 키·오타 의심을 보고합니다. 렌더러 코드의 숫자 리터럴은 `fa lint --hardcoded`로 점검합니다(CI가 증가를 막음).
2. `figure_specs/figure_<번호>_<project_name>.py` 선언 파일에서:
   * `source_stem`은 **`output_root` 기준 상대경로**로 지정합니다(예: `"<project_name>/figure1_combined"` 또는 `"figures/figure1_combined"`). 접두어 `outputs/`를 붙이지 않습니다 — publish가 `{output_root}/{source_stem}`으로 해석합니다.
   * 레이아웃 배치 구조(예: `layout`, `mosaic`, `width_ratios` 등)를 수정하여 새 플롯이 서브패널로 정상 합류하도록 명시합니다.

### Phase 7: 빌드 실행 및 성공 확인
1. `fa build <project_name> --preflight`(설치 전이면 `python -m fig_atlas build ...`)로 분석 → publish → **preflight** → verify를 실행합니다. 환경은 이름 있는 conda 환경 `fig-atlas`이고 어느 폴더에서든 `conda activate fig-atlas`로 켭니다. `fa build`는 conda를 활성화하지 않은 셸에서도 matplotlib DLL 경로(환경의 `Library/bin`)를 스스로 넣습니다.
2. 분석 스크립트를 `fa` 없이 직접 실행할 때만, conda 미활성 셸에서 먼저 PATH를 보정합니다. 그러지 않으면 렌더링 시점에 트레이스백 없이 프로세스가 죽습니다. 가장 쉬운 방법은 `conda activate fig-atlas`입니다. 켤 수 없다면 환경 폴더(`conda env list`로 확인)의 `Library/bin`을 PATH 앞에 넣습니다. 예: PowerShell `$env:PATH = "<환경 폴더>\Library\bin;" + $env:PATH`.
3. 빌드가 성공(`PASS`)하는지 확인합니다.
4. **Preflight 결과를 확인하고 error부터 해소합니다** (`outputs/preflight/<project_name>/<figure>.png` 오버레이에 문제 위치가 번호와 함께 표시되고, `outputs/preflight/preflight_findings.csv`에 각 지적의 `hint`가 있습니다).
   * 글자 겹침·잘림·패널 침범·인쇄 시 최소 크기 미달 등 **error는 config(`plots`/`figures`/레이아웃 키)만 조정해 해소**하고 다시 `fa build <project_name> --preflight`로 확인합니다. 렌더러 코드 수정이 필요하면 하드코딩 없이 새 config 키로 노출합니다.
   * **warn/info는 사용자에게 보고**하고, 의도된 디자인(예: 일부러 흐린 회색 자리표시)인지 확인받은 뒤 조정합니다. 색 팔레트 변경처럼 그림의 의미가 바뀌는 수정은 사용자 확인 없이 하지 않습니다.
5. 최종 산출물 이미지·검증 리포트·preflight 결과 위치를 사용자에게 보고하며 완료합니다.

---

## Case C 전용 절차 (데이터 + 그림 의도 기반 합성)

사용자가 **원시 데이터 + 참조 이미지(캡처/목업/스케치) 또는 자연어 설명**만 제공했을 때의 흐름입니다. 코드가 없으므로 렌더러를 LLM이 합성합니다. 7단계를 다음과 같이 변형합니다.

### C-0. 범위 확인 (Guard)
* 이 파이프라인은 **데이터 구동 표준 플롯**(matplotlib/seaborn: volcano, heatmap, pca, box, venn, dot 등)이 대상입니다. 참조 이미지가 손그림 스키마·비정형 일러스트·데이터와 무관한 도식이면 config-driven 렌더러 모델에 맞지 않으므로, 그 사실을 사용자에게 알리고 범위를 조정합니다.

### C-1. 데이터·의도 파악 (Phase 2 대체: "코드 분석" → "의도 추론")
* **데이터와 참조 이미지(또는 설명)만 씁니다.** 원본 폴더에 렌더링 코드(`scripts/`), `metadata/`, 렌더링된 `outputs/`가 함께 들어 있어도 읽지 않습니다. 그것을 보면 Case B가 되어, 데이터와 의도만으로 렌더러를 합성하는 Case C의 목적(과 Case C 시험)이 무너집니다.
* 데이터(`data.csv`)의 컬럼/자료형을 읽어 후보 매핑을 세웁니다(x/y/color/size/facet, 유전자·범주 컬럼 등).
* 참조 이미지를 판독하여 **플롯 종류, 색상 팔레트, 레이아웃, 주석/라벨, 축 스케일**을 추정합니다.
* 이미지로는 알 수 없는 값(통계 임계값 `padj`/`log2FC`, 정규화 방식, 정확한 컬럼 매핑 등)은 **추정하지 말고 확정 대상 목록**으로 남깁니다.

### C-2. 의도 확정 게이트 (⚠️ 필수 — 생성 직행 금지)
* 코드를 만들기 **전에** 해석안을 사용자에게 제시하고 승인받습니다. 예:
  > "데이터에서 `log2FC`→x, `-log10(padj)`→y, `nearest_gene`→라벨로 보고 **volcano plot**으로 해석했습니다. 임계값은 padj≤0.05, |log2FC|≥1로 잡았습니다. 상위 10개 유전자 라벨링. 이대로 진행할까요?"
* 확정되지 않은 항목(임계값·컬럼 매핑 등)은 반드시 질문으로 해소합니다. 이 게이트가 Case C의 성패를 가릅니다.

### C-3. 렌더러 확보 — 재사용 우선
* 추론된 플롯 종류가 **기존 렌더러나 레시피와 일치**하면 새로 짜지 말고 재사용합니다(`fa renderers`로 이름 확인, `fig_atlas.render("<이름>", ...)`로 그리기). 차이는 `params`로 표현합니다.
* **진짜 새로운 플롯 타입**일 때만 `fa new renderer <plot> --plot-type <type>`으로 골격을 만들고, Phase 5 규칙(`render_<plot>(ax|fig, df, params)`, 하드코딩 금지, 스키마 필수, 렌더러는 모양 단위)에 따라 새 렌더러나 레시피를 완성하고 **라이브러리 자산으로 축적**합니다(다음 프로젝트가 재사용). 반복되는 스타일은 `styles/<name>.yaml` 프리셋으로 승격합니다.

### C-4. 번들·메타데이터 작성 (출처 표기)
* 데이터를 `raw_data/<project_name>/<bundle_name>/inputs/data.csv`로 보존합니다(Phase 3).
* `metadata/metadata.yaml`의 `plot_params`에 확정된 파라미터를 기록하되, **출처가 코드 추출이 아니라 목업 기반 LLM 추론(검토 필요)임을 명시**합니다(예: `param_source: "inferred_from_mockup"`).
* 참조 이미지를 `metadata/reference.png`로 번들에 함께 보존하여 재현성·리뷰를 돕습니다.

### C-5. 통합 (Phase 6과 동일)
* `fa new project`로 프로젝트를 만들고, 번들의 `plot_type`이 렌더러에 등록되어 있으면 `fa ingest bundle`로 `plots:` 블록을 씁니다(C-3의 `--plot-type`). 아니면 Phase 6처럼 `fa param scaffold`로 씁니다.

### C-6. 빌드 + 검토 루프 (Phase 7 확장)

**기본 모드 = 연구자 수동 검토 (현재 표준)**
* `fa build <project_name> --preflight`로 빌드해 `PASS`를 확인하고, **preflight error가 없게 config로 먼저 정리**합니다. 겹침·잘림·대비 같은 기계적으로 판정 가능한 문제는 연구자 검토 전에 preflight로 걸러냅니다(오버레이 PNG로 위치 확인).
* 그다음 **최종 이미지·검증 리포트·preflight 결과 위치와 "목업 대비 어떤 점을 근사/생략했는지"를 사용자(연구자)에게 보고**합니다.
* 연구자가 저장된 이미지를 목업과 눈으로 대조하고 피드백(색/레이아웃/라벨/임계값 등)을 주면, 그에 따라 `params`·`styles`(가급적 YAML만)를 조정해 재빌드합니다. **판정 주체는 연구자**이며, 에이전트가 자동으로 "닮았다/아니다"를 단정하지 않습니다.
* 기존 렌더러를 재사용하는 경우 대부분 코드 수정 없이 config의 `plots`/`style`/`params` 수정 + 재빌드만으로 반영됩니다.

**선택(향후) = 반자동 시각 대조**
* 이미지 판독이 가능한 에이전트라면 **preflight를 통과한 뒤에** 렌더 결과를 1차로 훑어 후보 조정안을 제안할 수 있으나(결정적 검사가 먼저, 시각 판독은 그다음), 이는 어디까지나 보조이며 **최종 확인은 연구자**가 합니다. 완전 자동 비교 루프를 붙일 경우 비용 폭주를 막기 위해 **반복 상한(예: 3회) + 사용자 확인 게이트**를 반드시 둡니다(경량 비전 모델로 대조, 최신 렌더 이미지만 유지).
