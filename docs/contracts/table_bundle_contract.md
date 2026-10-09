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

## 검사

`fa bundle check <번들>`이 오류로 보고하는 것:
- 필수 역할의 열 이름이 `plot_params`에 없고 기본 이름도 없을 때
- 지정된(또는 기본) 이름의 열이 `data.csv`에 없을 때

예제 번들은 `examples/`에 있습니다([첫 그림 튜토리얼](../tutorials/first_figure.md)).
