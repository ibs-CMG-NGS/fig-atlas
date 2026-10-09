# 계약서 2: 다중 데이터셋 통합 (Time-series 클러스터 / Co-expression 모듈)

**적용 대상**: 여러 비교조건(예: D1, D3, 24h, 48h)을 가로질러 공통/특이 DEG를 뽑고, 그 유전자들을 시간축 패턴(time-series cluster)이나 공발현 모듈(co-expression module)로 묶어 하나의 통합 그림으로 그리는 프로젝트.
**실제 예시**: `fig3-acute-1d-3d-integrated/`, `fig7-acute-1d-chronic-24h-integrated/`(co-expression 변형), `fig10-human-acute-1d-3d-integrated/`, `fig13-human-chronic-24h-48h-integrated/`.
**소비 렌더러**: `render_multi_group_heatmap` (+ 동반 `render_ts_profile`, **별도 번들 불필요** — 아래 참고), `render_venn`, `render_count_summary`, `render_go_cluster_dot`, `render_go_bar`.

---

## 1) 그룹-주석 히트맵 번들 — `Filtered_{common_deg,ts_cluster{N},coexp_module{NN}}_genes_heatmap_bundle/`

세 가지 변형이 있지만 **스키마는 완전히 동일**하고 폴더 이름 접두어만 다릅니다:
- `Filtered_common_deg_heatmap_bundle/` — 모든 비교조건에 공통으로 나타나는 DEG
- `Filtered_ts_cluster{N}_genes_heatmap_bundle/` — 시간축 패턴별 클러스터 (N=1,2,3,4 ...)
- `Filtered_coexp_module{NN}_genes_heatmap_bundle/` — 공발현 모듈 (NN=01,02,03 ...)

```
Filtered_ts_cluster1_genes_heatmap_bundle/
  inputs/data.csv
  metadata/metadata.yaml
```

### `inputs/data.csv` 컬럼

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `gene_label` | string | 필수 | 유전자 심볼/라벨 (행 인덱스) |
| `<sample columns...>` | float | 필수 | 정규화된 발현값, **모든 비교조건의 모든 샘플이 한 번에** 들어감 (예: `h_RNA_Cont_1..3, h_RNA_D1_1, h_RNA_D1_3, h_RNA_D3_1, h_RNA_D3_3`) |

한 행 = 이 클러스터/모듈/공통집합에 속하는 유전자 하나. z-score 계산은 fig-atlas 렌더러가 raw 값으로부터 직접 하므로, **원본 발현값(z-score 아님)** 을 그대로 넣습니다.

### `metadata/metadata.yaml`

```yaml
plot_type: multi_group_heatmap
plot_params:
  gene_label_col: gene_label
  sample_columns: "['h_RNA_Cont_1', 'h_RNA_Cont_2', 'h_RNA_Cont_3', 'h_RNA_D1_1', 'h_RNA_D1_3', 'h_RNA_D3_1', 'h_RNA_D3_3']"
  sample_groups: "{'h_RNA_Cont': ['h_RNA_Cont_1', 'h_RNA_Cont_2', 'h_RNA_Cont_3'], 'h_RNA_D1': ['h_RNA_D1_1', 'h_RNA_D1_3'], 'h_RNA_D3': ['h_RNA_D3_1', 'h_RNA_D3_3']}"
  group_colors: "{'h_RNA_Cont': '#E41A1C', 'h_RNA_D1': '#377EB8', 'h_RNA_D3': '#4DAF4A'}"
  cmap: bwr
  linkage: ward
  metric: euclidean
  cluster_rows: False
  cluster_cols: False
  z_auto: True
  z_min: -2.0
  z_max: 2.0
  show_gene_labels: False
  gene_fontsize: 7
  show_col_labels: True
  title: "Filtered: Gene List (1415 genes) | Z-score | padj<=0.05, baseMean>=0, n=688"
```

`sample_columns`/`sample_groups`/`group_colors`는 파이썬 literal을 문자열로 담은 형태입니다 (`ast.literal_eval`로 파싱). **`sample_groups`의 순서가 곧 히트맵/그룹바의 열 순서**가 되므로, 비교조건의 자연스러운 순서(예: Control → D1 → D3, 혹은 Control → 24h → 48h)로 내보내주세요.

> **`render_ts_profile`(클러스터 평균 z-score 궤적 플롯)은 별도 번들이 필요 없습니다.** 위 히트맵 번들이 계산한 z-score 행렬을 그대로 재사용해서 그리므로, 2차 파이프라인은 이 스텝을 위해 아무것도 추가로 export할 필요가 없습니다.

---

## 2) 카운트 서머리 번들 — `count_summary_bundle/`

여러 비교조건 각각에서 유의 유전자로 판정된 것들을 long-format으로 모은 표 (UP/DOWN 막대 집계는 fig-atlas가 계산).

### `inputs/data.csv` 컬럼

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `dataset` | string | 필수 | 비교조건 라벨 (예: `"Acute_1D vs Cont"`) — `venn_diagram_bundle`의 `dataset` 값과 **명명 규칙을 통일**해두면 두 패널이 같은 순서/라벨로 나란히 읽힙니다 |
| `log2fc` | float | 필수 | |
| `adj_pvalue` | float | 필수 | |

한 행 = 그 비교조건에서 유의하다고 이미 판정된 유전자 하나 (필터링은 완료된 상태로 내보내되, 방향 판정을 위해 `log2fc`의 부호는 유지). fig-atlas 쪽에서 `fdr_max`/`lfc_min` 컷을 다시 적용해 UP/DOWN 카운트를 셉니다.

---

## 3) Venn 다이어그램 번들 — `venn_diagram_bundle/`

### `inputs/data.csv` 컬럼

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `dataset` | string | 필수 | 집합 이름 (2~3개 서로 다른 값, 예: `"Acute_1D vs Cont DE"`) |
| `item` | string | 필수 | 그 집합의 원소 (유전자 심볼/ID) |

한 행 = (집합, 원소) 하나. 교집합은 fig-atlas가 `item` 값의 중복 여부로 자동 계산하므로, **미리 교집합을 나눠서 보내지 말고 각 집합의 전체 멤버를 그대로** 보내면 됩니다.

---

## 4) GO BP dot / GO KEGG bar 번들 — `go_bp_{cluster{N},module{NN}}_dot_bundle/`, `go_kegg_{cluster{N},module{NN}}_bar_chart_bundle/`

**계약서 1(`de_go_bundle_contract.md`)의 2)/3)번 스키마와 완전히 동일**합니다 (컬럼, `metadata.yaml` 형식 모두 동일) — 다만 `cluster_id`/`gene_set` 값이 UP/DOWN 대신 그 클러스터/모듈 자체(`"Cluster01"` 등)를 가리킵니다. 새로 읽을 필요 없이 계약서 1을 그대로 참고하세요.

---

## 폴더 존재 규칙

| 폴더 | 있어야 하는 경우 |
|---|---|
| `Filtered_common_deg_heatmap_bundle/` | 공통 DEG가 하나라도 있을 때 |
| `Filtered_ts_cluster{N}_.../`, `Filtered_coexp_module{NN}_.../` | 그 클러스터/모듈이 실제로 존재할 때 (N/NN 값은 프로젝트마다 다를 수 있음 — 있는 만큼만) |
| `count_summary_bundle/`, `venn_diagram_bundle/` | 항상 (비교조건이 2개 이상일 때) |
| `go_bp_*_dot_bundle/`, `go_kegg_*_bar_chart_bundle/` | 해당 클러스터/모듈에 유의 term이 있을 때만 |

계약서 1과 마찬가지로, 없는 폴더 = 해당 서브패널 없음(스킵)으로 처리되고 레이블은 당겨지지 않습니다.
