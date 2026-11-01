# 그림 종류 대조표: GraphPad Prism 대비 fig-atlas (I-05)

> 작성일: 2026-11-01 · 계획: [PLAN_PLOT_CATALOG.md](PLAN_PLOT_CATALOG.md) 카드 I-05 · 대조한 패키지: fig-atlas main `5123475` (plot_type 25, 렌더러 이름 54)
> 목적: "계획을 끝내면 Prism의 그림 종류를 웬만큼 덮는가"를 항목별로 확인하고, 계획에 없는 빈 곳을 후보로 올려 **게이트 G1 재검토**에서 정하게 한다.
> 판정 기호: ✅ 있음(코드 없이, 예제 번들 있음) · 🟡 일부(렌더러는 있으나 Prism의 해당 형태·옵션 일부가 없음) · 📋 계획에 있음(카드 ID) · ➕ **새 후보**(이 표에서 처음 제안, G1에서 결정) · ⛔ 범위 밖(이유)

## 1. 기준 목록과 출처

Prism 11은 데이터 표 8종을 둔다: XY, 열(column), 그룹(grouped), 분할표(contingency), 생존(survival), 부분과 전체(parts of whole), 다변수(multiple variables), 중첩(nested). 그래프는 표 종류마다 고르는 스타일과, 고급 그래프 과정·통계 결과 그래프로 이루어진다. 아래 목록은 다음 공식 문서에서 모았다(확인 2026-11-01).

| 출처 | 내용 |
|---|---|
| [Prism 11 User Guide — Prism's eight data table formats](https://www.graphpad.com/guides/prism/latest/user-guide/using_data_table_format.htm) | 데이터 표 8종 |
| [Prism 11 User Guide — Format Graph: Column](https://www.graphpad.com/guides/prism/latest/user-guide/using_format_graph_one_way.htm), [Grouped graphs](https://www.graphpad.com/guides/prism/latest/user-guide/using_format_graph_two_way.htm) | 열·그룹 그래프 스타일: 막대, 산점(scatter dot), 정렬 점(aligned dot), box-and-whiskers, before-after, floating bar |
| [Box and whiskers](https://www.graphpad.com/guides/prism/latest/user-guide/box-and-whiskers.htm), [Violin plots](https://www.graphpad.com/guides/prism/latest/user-guide/graphing-box-and-whisker-and-v.htm), [Bar graphs](https://www.graphpad.com/guides/prism/latest/user-guide/bar-graphs.htm), [Nested graphs](https://www.graphpad.com/guides/prism/latest/user-guide/appearance-of-nested-graphs.htm) | 수염 방식(min–max, Tukey, 백분위), violin, 막대 배치, 중첩 그래프 |
| [Popular Prism Graphs](https://www.graphpad.com/series/popular-prism-graphs) | 산점, 선, 면적, box, 히트맵, violin, 막대, 막대 배치 4종(interleaved, stacked, superimposed, separated) |
| [Advanced Graph Types](https://www.graphpad.com/series/advanced-graph-types-and-best-practices-in-prism) | bubble, forest, population pyramid, spaghetti, volcano, 정규화 히트맵 |
| [Multiple variable tables](https://www.graphpad.com/guides/prism/latest/user-guide/multiple-variable-tables.htm), [Axis variables](https://www.graphpad.com/guides/prism/latest/user-guide/mv_graphs_axis_variables.htm), [Prism updates](https://www.graphpad.com/updates) | 다변수 그래프(bubble, 범주 축 그래프 — 11.1), 다변수 히트맵(10.3), 덴드로그램·신뢰 타원·convex hull·elbow/silhouette/gap plot(11) |
| [Correlation](https://www.graphpad.com/guides/prism/latest/statistics/stat_how_to_correlation.htm), [Bland-Altman](https://www.graphpad.com/guides/prism/7/statistics/stat_bland_altman.htm), [Frequency distributions](https://www.graphpad.com/guides/prism/5/user-guide/graphing_frequency_distribution_histograms_with_prism.htm), [What was new in Prism 8](https://www.graphpad.com/guides/prism/10/user-guide/whats-new-highlights.htm) | 상관 행렬 히트맵, Bland–Altman, 빈도 분포·누적 분포, 스플라인(smoothing, Akima) |

**한계**: Prism의 전체 그래프 목록을 한 쪽에 모은 공식 문서는 찾지 못했다. 위 문서들을 합친 것이며, ROC·QQ·잔차·추정(estimation) 그림은 통계 가이드의 해당 분석에서 그리는 그래프로 보았다(일부는 옛 판 가이드에서만 확인 — 표에 "옛 판" 표시).

## 2. 대조표

### 2.1 XY

| Prism | fig-atlas 지금 | 계획 | 판정 |
|---|---|---|---|
| 산점(XY points) | `group_scatter`, `threshold_scatter` | — | ✅ |
| 선 + 오차(SD/SEM/CI) | `line_band`(띠) | E-05(오차 막대 모드) | 🟡 → 📋 |
| 면적(area) | — | PC-16 누적 영역 | 📋 (단일 면적은 PC-16의 옵션으로) |
| 곡선 맞춤(선형·비선형, 용량-반응) | `dose_response`(4PL) | PC-10, E-04 | 🟡 → 📋 |
| 스플라인(smoothing, Akima) | — | PC-10이 맞춤 곡선 좌표를 그리므로 스플라인도 같은 입력으로 | 📋 (PC-10 범위에 명시 필요) |
| 잔차 그림(residuals) | — | — | ➕ PC-23 |
| spaghetti(개체별 궤적 + 평균) | — | — | ➕ PC-24 |
| 빈도 분포(히스토그램) | `histogram` | — | ✅ |
| 누적 빈도 분포(ECDF, 확률 축) | — | — | ➕ PC-25 |
| population pyramid(좌우 막대) | — | — | ➕ PC-26 |
| XY violin | — | — | ⛔ 드묾(열 violin으로 대체) |

### 2.2 열(column, 요인 하나)

| Prism | fig-atlas 지금 | 계획 | 판정 |
|---|---|---|---|
| 막대 + 오차 + 점 | `bar_scatter` | — | ✅ |
| 산점(scatter dot, 평균/중앙값 선) | — | PC-05 | 📋 |
| 정렬 점(aligned dot) | — | PC-05의 옵션 | 📋 (PC-05 범위에 명시 필요) |
| box-and-whiskers | `boxplot`(설정 13개) | — | 🟡 수염 방식(min–max, Tukey, 백분위) 선택 없음 → ➕ E-07 |
| violin | `violin` | — | ✅ |
| before–after(짝지은 점·선) | — | PC-01 | 📋 |
| floating bar(최소–최대 막대) | — | — | ➕ E-08 (`bar_scatter`의 막대 모드) |
| raincloud | — | PC-04 | 📋 (Prism 고유 그래프는 아님) |
| 추정 그림(estimation: 평균 차이와 신뢰구간 축) | — | — | ➕ PC-27 |
| 유의성 별·괄호 | `bar_scatter`의 `pvalue_col` | E-01 | 🟡 → 📋 |

### 2.3 그룹(요인 둘)

| Prism | fig-atlas 지금 | 계획 | 판정 |
|---|---|---|---|
| 막대 배치: interleaved / separated | — | PC-02 | 📋 (두 배치를 PC-02 옵션으로 명시 필요) |
| 막대 배치: stacked | `stacked_bar` | — | ✅ |
| 막대 배치: superimposed | — | — | ⛔ 겹쳐 그린 막대는 읽기 어렵다 |
| 그룹 산점 + 막대(Prism 8) | `bar_scatter`(`group_col`) | PC-02 | 🟡 → 📋 |
| 그룹 box / violin(두 번째 요인으로 나란히) | `boxplot`, `violin`(요인 하나) | — | ➕ E-09 |
| 그룹 before–after | — | PC-01의 옵션 | 📋 (PC-01 범위에 명시 필요) |
| 히트맵(정규화, 덴드로그램) | `heatmap`(`normalization`, `show_dendrogram`), `multi_group_heatmap` | — | ✅ |

### 2.4 분할표 · 생존 · 부분과 전체

| Prism | fig-atlas 지금 | 계획 | 판정 |
|---|---|---|---|
| 분할표 막대(개수·비율) | `stacked_bar`(`percent`) | PC-18 | 🟡 → 📋 |
| Kaplan–Meier(검열 표시) | `survival` | — | ✅ |
| 생존 곡선 신뢰띠 | — | — | ➕ E-10 (띠 좌표는 분석에서, v3 경계) |
| number-at-risk 표, log-rank 결과 | — | E-06 | 📋 |
| 파이 / 도넛 | — | PC-17 (보류, Phase 5 재검토) | 📋 |
| 백분율 점 그림(percentage dot plot) | — | — | ➕ PC-28 (P3 제안) |
| 부분과 전체 누적 막대 | `stacked_bar` | — | ✅ |

### 2.5 다변수 · 중첩

| Prism | fig-atlas 지금 | 계획 | 판정 |
|---|---|---|---|
| bubble(위치 + 크기 + 색) | — | PC-12 | 📋 |
| 범주 축 그래프(막대·box·violin·산점, 11.1) | 열 그래프들이 긴 형식 표를 받음 | — | ✅ (fig-atlas는 처음부터 긴 형식) |
| 다변수 히트맵(10.3) | `heatmap` | — | ✅ |
| 상관 행렬 히트맵 | — | PC-08 | 📋 |
| PCA(점수 그림) | `pca` | — | ✅ |
| PCA loadings·biplot·scree | — | — | ➕ E-11 |
| 신뢰 타원·convex hull(11) | — | — | ➕ E-12 (`group_scatter`, `pca` 옵션; 타원 좌표는 분석에서 계산해도 됨) |
| 덴드로그램 단독 / 히트맵 안(11) | `heatmap`, `multi_group_heatmap`의 덴드로그램 | — | 🟡 단독 덴드로그램 없음 → ➕ PC-29 (P3 제안) |
| elbow / silhouette / gap plot(11) | — | — | ⛔ 군집 수 진단: 분석 쪽 그림(선 그림으로 그릴 수 있음) |
| 중첩 그래프(subcolumn, 중첩 산점) | — | — | ➕ PC-30 |

### 2.6 고급 과정 · 통계 결과 그래프

| Prism | fig-atlas 지금 | 계획 | 판정 |
|---|---|---|---|
| forest plot | `effect_dots` | — | ✅ |
| volcano | `volcano`(오믹스 레시피), `threshold_scatter`(코어) | — | ✅ |
| population pyramid | — | — | ➕ PC-26 (위 2.1) |
| spaghetti | — | — | ➕ PC-24 (위 2.1) |
| Bland–Altman | — | PC-07 | 📋 |
| ROC 곡선 | — | PC-06 | 📋 (옛 판 가이드에서 확인) |
| QQ(정규성) | — | PC-09 | 📋 |
| 잔차 그림 | — | — | ➕ PC-23 (위 2.1) |

## 3. 요약

- **Prism 항목 50개**(위 표의 53행에서 두 절에 겹쳐 나온 3행을 뺀 것):
  - 지금 있음 ✅ 13
  - 일부 🟡 7 — 그중 5개는 계획 카드가 채우고(🟡 → 📋), 2개는 새 후보로 채울 것(🟡 → ➕)
  - 계획에 있음 📋 15
  - 새 후보 ➕ 12 (위의 🟡 → ➕ 2개를 더하면 새 카드 제안 14개: PC-23–PC-30, E-07–E-12)
  - 범위 밖 ⛔ 3
  - 집계는 이 문서의 판정 열을 센 것이다. 표를 고치면 다시 센다.
- **계획을 다 끝냈을 때 덮는 비율**: 있음 13 + 계획 15 + 계획이 채우는 일부 5 = 33 / 50 (66 %). 새 후보 14개를 모두 받아들이면 47 / 50 (94 %, 나머지 3개는 범위 밖).
- **계획(P1·P2·E)을 다 끝내면**: 열·그룹·XY·진단·다변수의 일상 그래프는 대부분 덮지만, 항목 수로는 3분의 2 정도다. **남는 빈 곳**은 새 후보 14개다. 그중 일상 사용 빈도가 높다고 보는 것: 잔차(PC-23), spaghetti(PC-24), 누적 분포(PC-25), 추정 그림(PC-27), 중첩(PC-30), box 수염 방식(E-07), 그룹 box/violin(E-09).
- **"Prism을 대체한다"고 말하려면** 그래프 종류뿐 아니라 같은 그래프 안의 꾸밈 폭(축 끊기·로그 E-02, 별·괄호 E-01, 평균±오차 겹치기 E-03)이 함께 끝나야 한다.
- **Origin**: 이 대조표는 Origin을 다루지 않는다. Origin의 강점(3D 표면, 등고선, 벡터장, 극좌표, 삼각 좌표, 공학 전용 그림)은 계획의 "하지 않는 것"(3D)과 P3(PC-20 극좌표, PC-22 삼각 좌표)에 해당한다. fig-atlas는 Origin의 2D 통계 그래프 부분만 덮도록 설계되어 있다.

## 4. 게이트 G1 재검토에 올릴 것

새 후보(➕)를 받아들일지, 우선순위를 어디에 둘지 정한다. 제안:

| ID | 후보 | 분류 | 제안 우선순위 | 비고 |
|---|---|---|---|---|
| PC-23 | 잔차 그림 | XY | P2 | 잔차는 분석에서 계산(v3), 렌더러는 점 + 0선 |
| PC-24 | spaghetti(개체별 궤적 + 평균) | XY | P2 | 반복 측정 시계열에 흔함 |
| PC-25 | 누적 분포(ECDF) | XY | P2 | 분포 비교에 흔함 |
| PC-26 | population pyramid | XY | P3 | |
| PC-27 | 추정 그림(Gardner–Altman / Cumming) | 열 | P2 | 평균 차이·신뢰구간은 분석에서(v3) |
| PC-28 | 백분율 점 그림 | 부분과 전체 | P3 | |
| PC-29 | 단독 덴드로그램 | 다변수 | P3 | 트리 좌표는 분석에서 |
| PC-30 | 중첩(subcolumn) 산점 | 중첩 | P2 | 기술 반복 안의 생물 반복을 보이는 그림 |
| E-07 | box 수염 방식 선택(min–max, Tukey, 백분위) | 열 | P1 | 범례에 방식을 적는 live claim과 함께 |
| E-08 | 막대 모드: floating bar(최소–최대) | 열 | P3 | |
| E-09 | 그룹 box / violin(두 번째 요인 나란히) | 그룹 | P1 | |
| E-10 | 생존 곡선 신뢰띠 | 생존 | P2 | 띠 좌표는 분석에서 |
| E-11 | PCA loadings·biplot·scree | 다변수 | P2 | |
| E-12 | 신뢰 타원·convex hull | 다변수 | P3 | |

또 기존 카드의 범위를 이 표에 맞춰 넓혀 적을 것(새 카드 아님): PC-01(그룹 before–after), PC-02(interleaved·separated 배치), PC-05(aligned dot), PC-10(스플라인 곡선 좌표), PC-16(단일 면적).
