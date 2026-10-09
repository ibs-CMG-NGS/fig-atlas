---
name: "assemble_figure"
description: "Assemble multi-panel publication figures by composing modular exploratory data loaders and fig_atlas renderers under a unified GridSpec layout."
---

# Assemble Figure Agent Skill (논문용 복합 피겨 조립 및 자동 합성 지침)

이 지침서는 확정된 스토리라인 명세서(`docs/storylines/figure_plan_*.md`)를 바탕으로, 탐색 단계에서 검증된 **데이터 로더와 렌더러 함수(`fig_atlas/renderers/*`, 오믹스 전용은 `fig_atlas_omics/renderers/*`)를 조립하여 논문 규격의 완성형 Multi-panel Figure 프로젝트(그림 하나당 `<domain>-paper-main-fig<N>-<slug>` 하나)를 생성하고 검증하는 프로토콜**입니다. 규칙의 정본은 저장소 루트의 `AGENTS.md`입니다.

---

## 5단계 복합 피겨 합성 프로토콜 (5-Step Figure Assembly Protocol)

### Step 1: 대상 피겨 사양 및 서브패널 매핑 로드
1. `docs/storylines/figure_plan_*.md`에서 합성 대상 피겨(예: `Main Figure 1`)의 서브패널 목록과 각각의 원천 탐색 프로젝트명을 확인합니다.
2. 각 서브패널의 데이터 로드 함수와 렌더링 파라미터를 원본 `analysis/<project_name>_analysis.py`에서 특정합니다.

### Step 2: 논문 피겨 프로젝트 만들기
1. 탐색 프로젝트 하나가 그대로 논문 그림이 되면 `fa promote <project> --figure <N> --slug <slug>`(`--dry-run` 먼저)로 승격합니다. 여러 탐색 프로젝트를 합성하는 새 그림이면 `fa new project <domain>-paper-main-fig<N>-<slug> --domain <domain> --category paper`로 만듭니다. 두 경우 모두 config·분석 스크립트·spec이 `<domain>/paper/` 아래에 생기고 빌드 목록에 등록됩니다.
2. 그림은 **최종 인쇄 크기로 1:1** 그립니다(docs/decisions/0001). config의 `project.style`에 `["default", "print", "page_a4_portrait_narrow"]`처럼 페이지 프리셋을 겹치고, 그림 높이·GridSpec 비율·여백은 `figures:` 아래 키로 둡니다. 저널이 정해지면 `styles/journal_<name>.yaml` 프리셋을 더합니다.
   * **Mandatory Rich In-Line Comments**: For multi-panel GridSpec ratios (`height_ratios`, `width_ratios`), subpanel gutters (`wspace`, `hspace`, `margin_*`), and plot parameters, include informative English in-line comments (`# ...`) explaining visual purpose, units, and tuning advice so researchers can adjust layouts directly in YAML.

### Step 3: 복합 렌더링 분석 스크립트 작성 (`analysis/<domain>/paper/<project>_analysis.py`)
1. **데이터 중복 로드 방지**: 원천 `analysis/` 스크립트의 데이터 로드 함수를 재사용하거나 공용 모듈로 분리하여 호출합니다.
2. **페이지 크기 캔버스 + config 레이아웃**: 크기·비율·간격은 숫자로 쓰지 않고 config에서 읽습니다. 렌더러는 이름으로 부를 수 있습니다(`fig_atlas.render`). 그림 높이·GridSpec 비율·간격은 config의 `figures:` 아래 키로 두고, 스크립트가 읽는 키는 `LAYOUT_SCHEMA`에 선언합니다.
   ```python
   import matplotlib.pyplot as plt
   from fig_atlas import get_config, render, save_page_figure
   from fig_atlas.renderers import place_panel_tags

   config = get_config()
   fcfg = config._raw["figures"]["figure1"]                  # 레이아웃 키: 주석과 함께 config에
   w, h = config.page.figure_size_in(height_mm=float(fcfg["height_mm"]))
   fig = plt.figure(figsize=(w, h))
   gs = fig.add_gridspec(2, 2, height_ratios=fcfg["height_ratios"], hspace=fcfg["hspace"], wspace=fcfg["wspace"])
   ax_a, ax_b = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
   render("volcano", ax_a, data_a, config._raw["plots"]["volcano"])    # 렌더러가 코어든 팩이든
   render("heatmap", ax_b, data_b, config._raw["plots"]["heatmap"])
   place_panel_tags(fig, [[("a", [ax_a])], [("b", [ax_b])]])          # 외곽 경계 기준 정렬 (AGENTS.md §1.5)
   save_page_figure(fig, stem.with_suffix(".pdf"))
   ```
   스크립트가 config에서 직접 읽는 키는 `LAYOUT_SCHEMA`에 선언합니다(Step 4 참조). 패널이 번들 하나씩이면 `fa new project`의 골격처럼 `fig_atlas.bundle_figure.draw_plots`로 `plots:` 블록을 차례로 그릴 수도 있습니다.

### Step 4: 논문 피겨 사양서 작성 (`figure_specs/<domain>/paper/figure_<NN>_<project>.py`)
1. 논문 본문에 들어갈 완성형 **Figure Title**, **Figure Legend (`panel_notes`)**, **Claim Boundary**를 작성하여 등록합니다. 데이터에서 나온 수치(개수·비율·통계량)는 손으로 적지 말고, 분석 스크립트에서 `fig_atlas.claims.record("n_anchors", n)`로 기록한 뒤 텍스트에는 `{n_anchors:,}`처럼 자리표시자로 씁니다(publish가 채우고, 값이 없으면 verify가 FAIL). `fa claims <project> --list`로 남은 손 수치를 확인합니다. 저널 Source Data용으로 각 패널이 그리는 표를 저장 전에 `fig_atlas.source_data.add(df, panel="a", title=...)`로 등록합니다(빌드가 `figure_NN_source_data/`로 내보냄). 투고 패키지는 `fa export <project> --zip`(RO-Crate). 분석 스크립트가 config에서 직접 읽는 시각 키(렌더러를 거치지 않는 레이아웃·색·여백)는 스크립트의 `LAYOUT_SCHEMA`에 점 경로로 선언(역할·단위·조정 방향)하고, 빌드 후 `fa param sync <project> --apply`로 config에 채웁니다.

### Step 5: 빌드 및 무결성 검증
1. 빌드 태스크를 실행하여 렌더링 및 사양 검증을 수행합니다:
   `fa build <project_name> --preflight`(또는 `python -m fig_atlas build ...`; VS Code에서는 Ctrl+Shift+B). 빌드 후 preflight까지 실행하고 verify에 결과를 반영합니다.
2. `outputs/<domain>/paper/<project_name>/figures/figure_XX_*/` 디렉터리에 `.png`, `.pdf`, `.svg` 및 `README.md`가 정상 생성되었는지 확인합니다.
3. **Preflight로 출판 규격을 확인합니다**: 패널 간 글자 겹침·패널 침범, 패널 태그 정렬(AGENTS.md §1.5), 인쇄 시 최소 글자 크기·한 페이지 초과, PDF 폰트(Type 42), 색각이상 구분·텍스트 대비. `outputs/preflight/<project_name>/` 오버레이와 `preflight_findings.csv`의 `hint`를 보고 **error는 config로 해소**하고, warn/info는 사용자에게 보고합니다. 논문 제출 직전에는 config에 `preflight: {mode: enforce}`를 두어 error가 verify를 실패시키게 할 수 있습니다.
