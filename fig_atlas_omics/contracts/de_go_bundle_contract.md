# 계약서 1: 단일 데이터셋 DE + GO/KEGG 인리치먼트 (`*-de-go`)

**적용 대상**: 하나의 비교조건(예: "Acute D1 vs Control")에 대한 차등발현(DE) + GO/KEGG 인리치먼트 결과를 한 그림으로 묶는 프로젝트.
**예시**: `raw_data/<study>/<project>/volcano_plot_bundle/` 처럼 그림 하나에 번들 하나.
**소비 렌더러**: `render_volcano`, `render_go_cluster_dot`, `render_go_bar`, `render_go_rrvgo_treemap` (모두 오믹스 팩 `fig_atlas_omics/renderers/`에 이미 존재 — 새 렌더러 불필요).

이 패밀리 하나의 프로젝트 폴더 아래에는 아래 5종류 번들이 (해당 데이터가 있는 만큼만) 들어갑니다. 특정 번들이 통계적으로 무의미하면(예: 유의 term이 하나도 없는 온톨로지) **그 번들 폴더를 통째로 생략**하면 됩니다 — 없는 폴더는 "결과 없음"으로 해석되고 해당 서브패널은 자동으로 스킵됩니다.

---

## 1) Volcano 번들 — `volcano_plot_bundle/`

```
volcano_plot_bundle/
  inputs/data.csv
  metadata/metadata.yaml
```

### `inputs/data.csv` 컬럼

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `gene_id` | string | 필수 | Ensembl 등 안정적 유전자 ID |
| `symbol` | string | 필수 | 유전자 심볼 (라벨링에 사용) |
| `base_mean` | float | 필수 | DESeq2 등의 baseMean |
| `log2FC` | float | 필수 | log2 fold change |
| `lfcse` | float | 권장 | log2FC 표준오차 |
| `stat` | float | 권장 | 검정통계량 |
| `pvalue` | float | 필수 | raw p-value |
| `padj` | float | 필수 | 보정된 p-value (FDR) |
| `<sample columns...>` | float | 필수(≥2개) | 정규화된 카운트, 그룹당 여러 컬럼 (예: `h_RNA_Cont_1`, `h_RNA_Cont_2`, `h_RNA_24h_1`, ...) — 볼케이노 자체엔 안 쓰이지만 다른 패널과의 교차 참조/재계산에 대비해 항상 포함 |

한 행 = 한 유전자. 필터링(예: padj 컷) 없이 **테스트된 전체 유전자**를 담는 것이 원칙입니다 — 임계값은 `metadata.yaml`/config의 threshold 파라미터가 적용하고, 데이터 자체는 미필터 상태를 유지합니다.

### `metadata/metadata.yaml`

```yaml
figure_id: volcano_plot
plot_type: volcano
plot_params:
  padj_threshold: 0.05
  log2fc_threshold: 0.585
  down_color: "#0000ff"
  up_color: "#ff0000"
  ns_color: "#808080"
  dot_size: 20
  x_min: -7.5          # 실제 데이터 범위에 맞춘 값 (null 허용 -> 자동)
  x_max: 7.5
  y_min: 0.0
  y_max: 109.7
  annotation_mode: top_n   # top_n | custom | none
  annotation_top_n: 30
  annotation_label_size: 8
  labels_title: "Volcano Plot"
  labels_xlabel: "Log2 Fold Change"
  labels_ylabel: "-Log10(Padj)"
```

---

## 2) GO BP 클러스터 대표 dot plot 번들 — `go_bp_{up,down}_cluster_dot_bundle/`

UP/DOWN 방향별로 폴더가 분리됩니다 (`go_bp_up_cluster_dot_bundle/`, `go_bp_down_cluster_dot_bundle/`). 이미 상위 도구에서 유사 term을 클러스터링해 **클러스터 대표 term만 한 행씩** 담은 표입니다.

### `inputs/data.csv` 컬럼

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `cluster_id` | string | 필수 | 클러스터 번호 (예: `"001"`) |
| `gene_set` | string | 필수 | `"UP"` 또는 `"DOWN"` (번들 자체가 방향별로 나뉘어도 이 컬럼은 유지) |
| `ontology` | string | 필수 | `"BP"` |
| `term_id` | string | 필수 | GO ID (예: `GO:0140448`) |
| `description` | string | 필수 | term 이름 (렌더러가 유일하게 강제 요구하는 컬럼) |
| `gene_ratio` | string | 필수 | `"8/827"` 형태 (분자/분모 문자열 그대로) |
| `bg_ratio` | string | 필수 | `"39/18870"` 형태 |
| `pvalue`, `fdr`, `qvalue` | float | 필수 | 통계량 |
| `gene_count` | int | 필수 | 히트 유전자 수 |
| `gene_symbols` | string | 필수 | `/`로 join된 유전자 심볼 목록 |
| `fold_enrichment` | float | 필수 | |
| `direction` | string | 필수 | `"UP"` / `"DOWN"` / `"UNKNOWN"` (클러스터 안에 방향이 섞이면 `UNKNOWN`) |
| `_cluster_size` | int | 필수 | 이 클러스터에 속한 term 개수 |
| `_fe_median` | float | 필수 | 클러스터 내 fold_enrichment 중앙값 |

### `metadata/metadata.yaml`

```yaml
plot_type: go_cluster_dot
plot_params:
  x_axis: "-log10(FDR)"
  color_by: "Fold Enrichment"
  size_by: "Cluster size"
  sort_by: "FDR"
  top_n: 30
  top_n_by: "FDR"
  dot_size_min: 40.0
  dot_size_scale: 20.0
  cmap: "YlOrRd_r"
  colorbar_loc: right
  colorbar_shrink: 0.6
  show_size_legend: True
```

---

## 3) GO/KEGG 막대그래프 번들 — `go_kegg_{up,down}_bar_chart_bundle/`

### `inputs/data.csv` 컬럼

클러스터 대표 dot plot과 거의 동일하되 `cluster_id`/`_cluster_size`/`_fe_median`이 **없습니다** (KEGG는 클러스터링 없이 term별로 그대로):

| 컬럼명 | 타입 | 필수 |
|---|---|---|
| `gene_set` | string | 필수 (`"UP"`/`"DOWN"`) |
| `ontology` | string | 필수 (`"KEGG"`) |
| `term_id`, `description` | string | 필수 (`description`만 렌더러가 강제) |
| `gene_ratio`, `bg_ratio` | string | 필수 |
| `pvalue`, `fdr`, `qvalue` | float | 필수 |
| `gene_count` | int | 필수 |
| `gene_symbols` | string | 필수 |
| `fold_enrichment` | float | 필수 |
| `direction` | string | 필수 |

### `metadata/metadata.yaml`

```yaml
plot_type: go_bar
plot_params:
  top_n: 30
  x_axis: "-log10(FDR)"
  sort_by: "FDR (ascending)"
  bar_color: "#4682b4"
  horizontal: True
  xlabel_text: "-log10(FDR)"
```

> 참고: 이 표는 GO BP뿐 아니라 KEGG 전용이며, `ontology` 값만 다르면 실제로 BP/CC/MF 막대그래프에도 동일 스키마가 그대로 재사용됩니다.

---

## 4) rrvgo 트리맵 번들 — `go_{bp,cc,mf}_{up,down}_rrvgo_treemap/`

GO term을 의미적으로 압축(rrvgo)한 결과. **번들 자체는 코드/스크립트 없이 데이터+참조 이미지만** 있으면 됩니다 (`metadata.yaml`도 필수 아님 — 최종 스타일은 fig-atlas config가 담당).

```
go_bp_up_rrvgo_treemap/
  inputs/data.csv
  metadata/reference.png   # (선택) 2차 파이프라인이 자체적으로 그려본 참조 이미지
```

### `inputs/data.csv` 컬럼 (R `rrvgo::reduceSimMatrix()` 출력 그대로)

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `go` | string | 필수 | GO ID |
| `cluster` | int | 필수 | 클러스터 번호 |
| `parent` | string | 필수 | 부모 GO ID |
| `score` | float | 필수 | 클러스터 대표 점수 (클러스터 내 모든 행에서 동일값) |
| `size` | float | 필수 | term의 gene-set 크기 (트리맵 사각형 면적을 좌우하는 유일한 값) |
| `term` | string | 필수 | term 이름 |
| `parentTerm` | string | 필수 | 부모 term 이름 (트리맵 바깥 블록 라벨) |
| `termUniqueness`, `termUniquenessWithinCluster`, `termDispensability` | float | 권장 | rrvgo 부가 지표 |

---

## 5단계 조건별 폴더 존재 규칙

| 폴더 | 있어야 하는 경우 |
|---|---|
| `volcano_plot_bundle/` | 항상 (DE 결과가 있으면) |
| `go_bp_up_cluster_dot_bundle/`, `go_bp_down_cluster_dot_bundle/` | 해당 방향에 유의 BP term이 있을 때만 |
| `go_kegg_up_bar_chart_bundle/`, `go_kegg_down_bar_chart_bundle/` | 해당 방향에 유의 KEGG term이 있을 때만 |
| `go_{bp,cc,mf}_{up,down}_rrvgo_treemap/` | 해당 온톨로지/방향에 유의 term이 3개 이상 있어 압축이 의미 있을 때만 |

폴더가 없으면 그 서브패널(과 그 패널의 알파벳 레이블)은 통째로 스킵되고, 뒤 패널의 레이블이 당겨지지 않습니다(레이블은 "고정 위치" 기준이라 빈 자리로 남습니다).
