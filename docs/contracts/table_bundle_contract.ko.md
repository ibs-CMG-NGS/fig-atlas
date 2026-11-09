# 계약서: 표 번들 (범용 모양 — 선 + 오차 띠, 효과 대 유의성 산점도)

분야와 무관한 표 데이터 번들의 스펙입니다. 코어의 범용 렌더러는 열 이름을 정해 두지 않습니다. 어느 열이 x이고 어느 열이 y인지는 `metadata.yaml`의 `plot_params`에 적습니다(`x_col: dose`처럼). `fa bundle check`는 이렇게 지정된 열이 실제로 있는지 검사하고, `fa ingest bundle`은 그 이름을 config에 그대로 옮깁니다. 폴더 구조와 공통 원칙은 [`README.md`](README.md)를 따릅니다.

## 폴더 구조

```
<bundle_name>/
  inputs/data.csv          # 표 하나 (한 행 = 한 관측 또는 한 항목)
  metadata/metadata.yaml   # plot_type + plot_params (열 이름 지정 포함)
```

## `plot_type: line_band` — 선 + 오차 띠

시간·용량·위치에 따른 반복 측정값을 집단별 선과 오차 띠(SEM, SD, 95% CI)로 그립니다(`render_line_band`).

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `x_col` | `x` | 예 | x 값(숫자, 또는 `x_order`로 순서를 준 범주) |
| `y_col` | `y` | 예 | 반복 측정값(또는 `aggregate: none`이면 중심값) |
| `group_col` | — | 아니오 | 선을 나누는 집단 열. 적으면 그 열이 있어야 합니다 |
| `lower_col`, `upper_col` | — | 아니오 | 이미 요약된 표(`aggregate: none`)의 띠 아래·위 경계 |

```yaml
plot_type: line_band
plot_params:
  x_col: dose_uM
  y_col: viability
  group_col: compound
  x_log: true
  error: sem
```

## `plot_type: threshold_scatter` — 효과 대 유의성

항목마다 효과 크기(부호가 방향)와 유의성(작을수록 강함)이 있는 표를, 임계값으로 up / down / ns를 나눠 점으로 그립니다(`render_threshold_scatter`). volcano plot이 이 모양의 한 예입니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `x_col` | — | 예 | x에 그릴 열 |
| `y_col` | — | 예 | y에 그릴 열 |
| `effect_col` | — | 예 | 부호 있는 효과 열 (up / down 판정) |
| `sig_col` | — | 예 | 유의성 열 (예: 보정 P) |

열 이름 기본값이 없으므로 네 역할 모두 `plot_params`에 적어야 합니다. 변환은 `x_transform` / `y_transform`(`none`, `log10`, `neg_log10`)으로 줍니다.

```yaml
plot_type: threshold_scatter
plot_params:
  x_col: effect
  y_col: p_adj
  effect_col: effect
  sig_col: p_adj
  y_transform: neg_log10
  effect_threshold: 0.5
  sig_threshold: 0.05
```

## `plot_type: paired_plot` — 전후 비교

개체마다 조건 사이의 값을 선으로 이어 그립니다(전 → 후, 또는 여러 시점). 평균·중앙값 선과 유의성 괄호를 더할 수 있습니다(`render_paired_plot`). 그룹 열이 있으면 그룹이 나란히 놓이고, 그룹마다 자기 조건을 가집니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `subject_col` | `subject` | 예 | 값이 속한 개체(개체 하나에 선 하나) |
| `condition_col` | `condition` | 예 | 조건. 순서는 `condition_order` |
| `value_col` | `value` | 예 | 측정값 |
| `group_col` | — | 아니오 | 두 번째 요인. 그룹이 나란히 놓입니다. 적으면 그 열이 있어야 합니다 |
| `pvalue_col` | — | 아니오 | 분석 스크립트에서 짝지은 검정으로 구한 그룹별 P 값([분석 레시피](../howto/analysis_recipes.md) 2절). 괄호를 그립니다. 적으면 그 열이 있어야 합니다 |

```yaml
plot_type: paired_plot
plot_params:
  subject_col: mouse
  condition_col: timepoint
  value_col: glucose
  condition_order: ["baseline", "week 4"]
  pvalue_col: p_value
  summary: mean
```

## `plot_type: grouped_bar` — 그룹 막대 (요인 둘)

범주마다 그룹별 막대를 그립니다. 막대는 평균(또는 중앙값)이고 SD·SEM·95% CI 오차 막대와 반복값 점이 겹칩니다(`render_grouped_bar`). `arrangement: interleaved`는 범주 안에 그룹을 나란히, `separated`는 그룹마다 묶음을 따로 둡니다. 괄호는 범주 안에서 각 그룹을 `control_group`과 비교합니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `category_col` | `category` | 예 | 첫 번째 요인(x 범주) |
| `group_col` | `group` | 예 | 두 번째 요인(막대 색) |
| `value_col` | `value` | 예 | 반복 측정값 |
| `pvalue_col` | — | 아니오 | (범주, 그룹) 행마다 그 그룹의 `control_group` 대비 P 값. 분석 스크립트의 사후 검정에서 구합니다([분석 레시피](../howto/analysis_recipes.md) 3절). 적으면 그 열이 있어야 합니다 |

```yaml
plot_type: grouped_bar
plot_params:
  category_col: genotype
  group_col: treatment
  value_col: expression
  control_group: vehicle
  pvalue_col: p_vs_vehicle
  error: sem
```

## `plot_type: correlation_scatter` — 상관 산점도 (변수 둘)

항목마다 점 하나를 찍고, 회귀선과 그 띠, 그룹별 r과 P를 그립니다(`render_correlation_scatter`). 선과 띠와 숫자는 분석 스크립트가 만듭니다([분석 레시피](../howto/analysis_recipes.md) 4절). 선과 띠는 같은 표의 추가 행에 좌표로, r과 P는 열로 들어옵니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `x_col` | `x` | 예 | 첫 번째 변수 |
| `y_col` | `y` | 예 | 두 번째 변수 |
| `group_col` | — | 아니오 | 점(과 적합 행)을 색 그룹으로 나눕니다 |
| `fit_x_col`, `fit_y_col` | — | 아니오 | 적합 행에서 x 격자와 적합된 y. 그룹이 빈 적합 행은 모든 점에 대한 선입니다 |
| `band_lower_col`, `band_upper_col` | — | 아니오 | 적합 행에서 띠의 아래·위 경계(신뢰띠 또는 예측띠; 어느 쪽인지 범례에 적습니다) |
| `r_col`, `p_col` | — | 아니오 | 그룹마다의 r과 P, 그 그룹의 행에 반복. 적으면 그 열이 있어야 합니다 |

```yaml
plot_type: correlation_scatter
plot_params:
  x_col: body_weight
  y_col: fat_mass
  group_col: diet
  fit_x_col: fit_x
  fit_y_col: fit_y
  band_lower_col: ci_low
  band_upper_col: ci_high
  r_col: r
  p_col: p_value
```

## `plot_type: raincloud` — raincloud (반쪽 violin, 박스, 점)

범주마다 반쪽 violin(구름), 사분위와 수염을 보이는 박스, 모든 값을 점(비)으로 그립니다(`render_raincloud`). `orientation: horizontal`은 범주를 y축에 두고 첫 범주를 맨 위에, `vertical`은 x축에 둡니다. 괄호는 각 범주를 `control_category`와 비교합니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `category_col` | `group` | 예 | 각 값의 범주 |
| `value_col` | `value` | 예 | 값 |
| `pvalue_col` | — | 아니오 | 범주의 행마다 그 범주의 `control_category` 대비 P 값. 분석 스크립트의 검정에서 구합니다([분석 레시피](../howto/analysis_recipes.md) 3절). 적으면 그 열이 있어야 합니다 |

```yaml
plot_type: raincloud
plot_params:
  category_col: treatment
  value_col: latency
  control_category: vehicle
  pvalue_col: p_vs_vehicle
  orientation: horizontal
```

## `plot_type: column_scatter` — 열 산점도 (점, 평균 또는 중앙값, 오차)

범주마다 값을 점으로 찍고 평균 또는 중앙값 선과 오차 막대를 그립니다(`render_column_scatter`; Prism의 scatter dot plot). `point_layout: swarm`은 점을 실제 값에 둔 채 겹치지 않게 옆으로 펼치고, `jitter`는 무작위로 흩고, `aligned`는 한 세로줄에 둡니다. 괄호는 각 범주를 `control_category`와 비교합니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `category_col` | `group` | 예 | 각 값의 범주 |
| `value_col` | `value` | 예 | 값 |
| `pvalue_col` | — | 아니오 | 범주의 행마다 그 범주의 `control_category` 대비 P 값. 분석 스크립트의 검정에서 구합니다([분석 레시피](../howto/analysis_recipes.md) 3절). 적으면 그 열이 있어야 합니다 |

```yaml
plot_type: column_scatter
plot_params:
  category_col: treatment
  value_col: il6
  control_category: vehicle
  pvalue_col: p_vs_vehicle
  summary: mean
  error: sd
```

## `plot_type: roc_curve` — ROC 곡선 (AUC와 그 신뢰구간)

표지자마다 ROC 곡선 하나, 우연 대각선, 범례에 각 곡선의 AUC와 신뢰구간을 그립니다(`render_roc_curve`). 곡선과 숫자는 분석 스크립트가 만듭니다([분석 레시피](../howto/analysis_recipes.md) 5절).

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `fpr_col` | `fpr` | 예 | 곡선 점마다의 위양성률(1 − 특이도), 0에서 1 |
| `tpr_col` | `tpr` | 예 | 곡선 점마다의 진양성률(민감도) |
| `group_col` | — | 아니오 | 곡선 점이 속한 표지자(분류기): 표지자마다 곡선 하나 |
| `auc_col`, `auc_low_col`, `auc_high_col` | — | 아니오 | 곡선마다의 AUC와 신뢰구간(bootstrap 또는 DeLong), 그 곡선의 행에 반복 |
| `operating_point_col` | — | 아니오 | 표시할 점에서 참(분석이 고른 기준점, 예: Youden) |

열을 적으면 그 열이 있어야 합니다.

```yaml
plot_type: roc_curve
plot_params:
  group_col: marker
  auc_col: auc
  auc_low_col: auc_ci_low
  auc_high_col: auc_ci_high
  operating_point_col: youden
```

## `plot_type: bland_altman` — Bland–Altman 그림 (두 측정법의 일치도)

표본마다 두 측정법의 차이를 평균에 대해 그리고, 차이 없음 선, bias, 일치 한계(limits of agreement)를 오른쪽 끝의 값과 함께 그립니다(`render_bland_altman`). 점의 좌표는 두 측정값에서 바로 구하고, bias와 한계는 분석 스크립트가 열로 줍니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `a_col` | `method_a` | 예 | 첫 번째 측정법의 표본별 측정값 |
| `b_col` | `method_b` | 예 | 두 번째 측정법의 측정값 |
| `group_col` | — | 아니오 | 점을 그룹별 색으로 나눕니다 |
| `bias_col` | — | 아니오 | bias(차이의 평균), 모든 행에 반복 |
| `loa_low_col`, `loa_high_col` | — | 아니오 | 일치 한계(예: bias ± 1.96 SD), 모든 행에 반복 |

`difference: percent`는 100 × (a − b) / 평균을 그립니다. bias와 한계도 같은 방식으로 계산합니다. 열을 적으면 그 열이 있어야 합니다.

```yaml
plot_type: bland_altman
plot_params:
  a_col: hba1c_lab
  b_col: hba1c_device
  bias_col: bias
  loa_low_col: loa_low
  loa_high_col: loa_high
```

## `plot_type: correlation_matrix` — 상관 행렬 (삼각형, 값, 별표)

여러 변수 사이의 상관을 r로 색칠한 하삼각·상삼각·전체 칸으로 그립니다. 칸은 사각형, 또는 면적이 |r|을 따르는 원이고, 칸 안에 r과 유의성 별표를 쓰며 컬러바를 붙입니다(`render_correlation_matrix`). 쌍마다의 r과 P는 분석 스크립트가 긴 표로 줍니다([분석 레시피](../howto/analysis_recipes.md) 4절): 한 쌍에 한 행.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `row_col` | `var1` | 예 | 쌍의 첫 번째 변수 |
| `col_col` | `var2` | 예 | 두 번째 변수(한 번만 준 쌍도 대각선 양쪽에 그립니다) |
| `r_col` | `r` | 예 | 쌍의 상관계수 |
| `p_col` | — | 아니오 | 쌍의 P 값: 칸의 별표, 그리고 `hide_above_p`로 빈 칸. 적으면 그 열이 있어야 합니다 |

```yaml
plot_type: correlation_matrix
plot_params:
  p_col: p_value
  triangle: lower
  mark: square        # 또는 circle
```

## `plot_type: dot_matrix` — 행 × 열 희소 격자

(행, 열) 칸마다 점을 하나 그리고, 점 넓이는 개수 열, 점 색은 범주 열로 정합니다(`render_dot_matrix`). 행이 없는 칸은 비워 두며, 행과 열 순서는 데이터 순서나 `row_order`, `col_order`를 따릅니다. 유전자 × 세포유형 발현 격자, 경로 × 조건 근거 격자 같은 그림에 씁니다.

| 역할 (plot_params 키) | 기본 열 이름 | 필수 | 내용 |
|---|---|---|---|
| `row_col` | `row` | 예 | 칸의 행(특징) |
| `col_col` | `column` | 예 | 칸의 열(표본, 조건) |
| `size_col` | — | 아니오 | 점 넓이를 정하는 개수 (없으면 모두 같은 크기) |
| `color_col` | — | 아니오 | 점 색을 정하는 범주 (없으면 한 색) |
| `row_group_col` | — | 아니오 | 행을 묶어 사이에 선을 긋는 열 |

```yaml
plot_type: dot_matrix
plot_params:
  row_col: gene
  col_col: cell_type
  size_col: pct_expressing
  color_col: response_class
```

## `plot_type: table` — 요약 표를 글자로 인쇄

표를 출판 관례대로 글자로 그립니다 — 가로선 세 개, 세로선 없음, 칸 채움 없음(`render_table`). 위의 형태들과 달리 **역할을 정하지 않습니다** — 어떤 표든 인쇄할 수 있으므로, `plot_params`에 담기는 것은 "어떤 열을 어떤 순서로, 각 열을 어떻게"입니다.

**이것은 표를 그리는 기능이고, 표를 투고하는 경로가 아닙니다.** 저널은 표를 편집 가능한 텍스트(Word, Excel)로 받습니다. 그림으로 만든 표는 교정도, 조판도, 화면 낭독기 읽기도 되지 않습니다. 컴펜디움 쪽, 발표, 포스터에 쓰고, 투고에는 `inputs/data.csv` 자체를 내십시오.

| 키 | 형태 | 필수 | 내용 |
|---|---|---|---|
| `columns` | 열 이름의 리스트 | 아니오 | 인쇄할 열과 그 순서(기본값: 데이터가 가진 순서의 모든 열). `data.csv`에 없는 이름은 오류 |
| `column_labels` | 열 이름을 키로 하는 사전 | 아니오 | 열마다 인쇄할 머리글(기본값: 열 이름 그대로) |
| `column_format` | 열 이름을 키로 하는 사전 | 아니오 | 열마다의 파이썬 format spec(`".1f"`, `",.0f"`, `".3g"`). 숫자 열마다 지정하십시오. 안 하면 `41` 옆에 `0.4871234`가 찍힙니다 |
| `column_align` | 열 이름을 키로 하는 사전 | 아니오 | `left`, `right`, `center`(기본값: 숫자는 오른쪽, 나머지는 왼쪽) |
| `column_width` | 열 이름을 키로 하는 사전 | 아니오 | 표 너비의 `[0-1]` 비율(기본값: 가장 넓은 칸에서 측정) |
| `max_rows` | 숫자 | 아니오 | 인쇄할 최대 행 수(기본 40). 넘는 행은 버리고 `truncation_note`에 몇 행인지 적습니다. 긴 표는 이 형태가 아닙니다 -- CSV로 두십시오 |

네 사전 중 하나의 키가 어떤 열도 가리키지 않으면 **오류가 아니라 경고**입니다. 깨지는 것은 없고 그 설정만 아무 일도 하지 않지만, `column_format`의 오타는 그러지 않으면 "서식이 안 먹은 숫자"로만 드러나 눈에 띄지 않습니다.

표 안의 숫자는 분석 스크립트가 계산합니다. 생성 코드에 손으로 적지 않습니다([분석 레시피](../howto/analysis_recipes.md)) — 그림 범례와 같은 규칙입니다.

```yaml
plot_type: table
plot_params:
  columns: ["group", "n", "mean_latency_s", "sd_latency_s", "p_vs_vehicle"]
  column_labels:
    mean_latency_s: "Latency (s), mean"
    p_vs_vehicle: "P vs vehicle"
  column_format:
    mean_latency_s: ".1f"
    p_vs_vehicle: ".3g"       # .3f로는 1e-07이 0.000으로 찍힙니다
  na_text: "--"               # 기준군에는 P 값이 없습니다
  title: "Latency to fall, by treatment group"
  footnotes:
    - "Welch's t test against vehicle, each dose separately."
```

## 검사

`fa bundle check <번들>`이 오류로 보고하는 것:
- 필수 역할의 열 이름이 `plot_params`에 없고 기본 이름도 없을 때
- 지정된(또는 기본) 이름의 열이 `data.csv`에 없을 때. `columns`에 적은 이름도 포함합니다

그리고 경고로 보고하는 것: 열마다의 사전(`column_labels`, `column_format`, `column_align`, `column_width`)의 키가 어떤 열도 가리키지 않을 때.

예제 번들은 `examples/`에 있습니다([첫 그림 튜토리얼](../tutorials/first_figure.md)).
