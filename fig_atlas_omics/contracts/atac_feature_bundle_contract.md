# 계약서 4: ATAC 피크의 모티프·게놈 위치 인리치먼트

**적용 대상**: 차등 접근성(DA) 피크 집합이 어떤 전사인자 모티프와 게놈 위치(프로모터, 인트론 등)에 몰려 있는지를 조건별로 보여 주는 그림.
**소비 렌더러**: `render_motif_dotplot`, `render_peak_feature_enrichment` (오믹스 팩 `fig_atlas_omics/renderers/`).
**예제 번들**: `examples/gallery/motif_dotplot/`, `examples/gallery/peak_feature_enrichment/` (합성 데이터).

두 번들 모두 열 이름은 `plot_params`에서 바꿀 수 있습니다(아래 표의 "이름을 정하는 키"). 적지 않으면 기본 이름을 씁니다.

---

## 1) 모티프 인리치먼트 dot plot 번들 — `plot_type: motif_dotplot`

긴 형식: (모티프, 조건) 한 쌍에 한 줄. 모든 칸에 점을 그리며, 유의하지 않은 칸은 값과 P를 비워 두면 작은 회색 점으로 그립니다.

| 기본 열 이름 | 이름을 정하는 키 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| `motif` | `term_col` | string | 필수 | 모티프 이름 (행) |
| `pattern_class` | `class_col` | string | 필수 | 조건 또는 피크 집합 (열) |
| `log2fc` | `value_col` | float | 필수 | log2 fold enrichment (색), 유의하지 않으면 빈칸 |
| `neg_log10_p` | `p_col` | float | 필수 | -log10(P) (점 크기), 유의하지 않으면 빈칸 |

## 2) 게놈 위치 인리치먼트 번들 — `plot_type: peak_feature_enrichment`

(피크 집합, 게놈 위치) 한 쌍에 한 줄. 예: Fisher 정확검정으로 DA 피크와 배경 피크의 위치 분포를 비교한 결과. 피크 집합마다 패널 하나, 위치마다 막대 하나(log2 odds ratio)를 그리고, `fdr_max` 아래인 막대를 강조합니다.

| 기본 열 이름 | 이름을 정하는 키 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| `GeneSet` | `geneset_col` | string | 필수 | 피크 집합 (예: total, up, down) |
| `Feature` | `feature_col` | string | 필수 | 게놈 위치 범주 (Promoter, Intron, ...) |
| `OddsRatio` | `odds_ratio_col` | float | 필수 | DA 대 배경의 odds ratio |
| `p_adjust` | `fdr_col` | float | 필수 | 보정된 P |
| `DA_Count`, `DA_Pct`, `Background_Count`, `Background_Pct`, `p_value` | — | 숫자 | 권장 | 원래 개수와 비율, raw P (`render_peak_feature_composition`이 비율 막대에 씀) |
