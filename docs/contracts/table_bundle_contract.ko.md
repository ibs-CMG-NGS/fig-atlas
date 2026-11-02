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

## 검사

`fa bundle check <번들>`이 오류로 보고하는 것:
- 필수 역할의 열 이름이 `plot_params`에 없고 기본 이름도 없을 때
- 지정된(또는 기본) 이름의 열이 `data.csv`에 없을 때

예제 번들은 `examples/`에 있습니다([첫 그림 튜토리얼](../tutorials/first_figure.md)).
