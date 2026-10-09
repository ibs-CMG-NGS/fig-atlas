# 계약서 3: GO/KEGG 인리치먼트 교차조건 비교 (Cross-Condition Comparison)

**적용 대상**: 하나의 term(또는 pathway) 집합을 놓고, **여러 독립적인 비교조건**(예: Acute D1/D3, Chronic 24h/48h, 각각 vs Control)에서 방향/유의성이 어떻게 달라지는지 한 그림으로 비교.
**실제 예시**: `fig14-mouse-go-cross-comparison/`, `fig15-human-go-cross-comparison/`.
**소비 렌더러**: `render_cross_condition_heatmap`, `render_cross_condition_dotplot` (둘 다 오믹스 팩 `fig_atlas_omics/renderers/`에 존재). UpSet 플롯은 데이터 스키마만 정의되어 있고 **렌더러는 아직 미구현**입니다 (`render_upset` 예정 — 데이터가 먼저 이 스펙대로 오면 렌더러 작업만 하면 됨).

---

## 1) 히트맵/닷플롯 공용 번들 — `cross_condition_heatmap_semantic-{bp,kegg}/`, `cross_condition_dotplot_semantic-{bp,kegg}/`

**핵심**: 히트맵용과 닷플롯용은 **완전히 동일한 표**입니다 (같은 온톨로지의 heatmap/dotplot 두 뷰가 같은 원본 데이터를 다르게 시각화할 뿐). 2차 파이프라인이 이 표를 **한 번만 생성**해서 두 번들 폴더에 동일하게 넣거나(또는 fig-atlas 쪽에서 한 파일을 공유 로드하도록 폴더를 하나로 합쳐도 됩니다 — 중복 export가 필수는 아닙니다).

```
cross_condition_heatmap_semantic-bp/
  inputs/data.csv
  metadata/reference.png   # (선택)
```

### `inputs/data.csv` 컬럼 (long-format: 한 행 = 1개 term × 1개 조건, 유의한 조합만)

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `GO ID` | string | 필수 | GO ID 또는 KEGG pathway ID |
| `GO Term` | string | 필수 | term/pathway 이름 (컬럼명은 KEGG여도 `"GO Term"` 그대로 사용) |
| `Condition` | string | 필수 | 비교조건 라벨 (예: `"D1_vs_Control"`, `"24h_vs_Control"`) — **모든 term에서 철자/대소문자가 정확히 동일**해야 합니다. fig-atlas config의 `condition_order`가 이 값과 정확히 매칭되어야 하기 때문입니다 |
| `Direction` | string | 필수 | `"UP"` 또는 `"DOWN"` — 한 term은 모든 조건에서 **하나의 방향만** 가져야 합니다 (한 term이 어떤 조건에선 UP, 다른 조건에선 DOWN으로 섞이면 안 됨 — 섞이는 경우가 있다면 그 사실을 알려주세요, 렌더러가 이를 전제로 짜여 있습니다) |
| `Gene Ratio` | float | 필수 | 0~1 사이 비율 (dot plot의 크기 인코딩에 사용) |
| `Adjusted P-value` | float | 필수 | FDR |
| `Signed -log10(FDR)` | float | 필수 | `sign(Direction) * -log10(Adjusted P-value)` — UP은 양수, DOWN은 음수. 히트맵의 구간(bin) 분류와 dot plot의 색상 인코딩 모두 **이 컬럼 하나로** 결정됩니다 |
| `Direction Flip` | bool | 선택 | 사용 안 함, 있어도 무방 |

**"absent" 표현 규칙**: 어떤 (term, 조건) 조합이 그 조건에서 FDR 유의성을 통과하지 못했다면, **그 조합의 행을 아예 만들지 마세요** (NaN 채운 행 X). 히트맵은 없는 조합을 자동으로 "absent"(흰색) 칸으로 그립니다.

### 도메인별 term 개수에 따른 안내

- BP처럼 term이 많을 때(예: 29개)는 히트맵(전체 표시)과 dot plot(상위 N개만 필터링, fig-atlas config의 `top_n_up`/`top_n_down`)을 **같은 원본 표에서** 각각 다르게 잘라 씁니다 — 필터링은 fig-atlas 쪽 config 몫이니 원본 표는 자르지 말고 전체를 보내주세요.
- KEGG처럼 term이 적을 때(예: 5개)는 필터링이 의미가 없어 dot plot 하나만으로 충분한 경우가 많습니다 — 이 경우 heatmap 번들 폴더를 아예 안 만들어도 됩니다 (fig-atlas 쪽에서 "정보 중복"으로 판단해 dot plot만 쓰는 것으로 이미 한 번 이 결정을 내린 전례가 있습니다).

---

## 2) UpSet 플롯 번들 — `upset-{bp,kegg}-{up,down}/` (스키마 확정, 렌더러 구현 대기)

여러 조건에 걸쳐 term이 얼마나 겹치는지(overlap)를 보여주는 집합 다이어그램용 데이터입니다.

```
upset-bp-up/
  inputs/data.csv
```

### `inputs/data.csv` 컬럼

| 컬럼명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `GO ID` | string | 필수 | |
| `GO Term` | string | 필수 | |
| `N Conditions` | int | 필수 | 이 term이 유의했던 조건의 개수 |
| `Conditions` | string | 필수 | `"; "`(세미콜론+공백)으로 join된 조건 이름 목록, 예: `"24h_vs_Control; 48h_vs_Control; D1_vs_Control"` — 위 1)번 표의 `Condition` 값과 철자가 동일해야 합니다 |

폴더는 온톨로지(`bp`/`kegg`) × 방향(`up`/`down`) 조합마다 하나씩, 총 최대 4개입니다. UP/DOWN 어느 한쪽에 겹치는 term이 전혀 없으면 그 폴더는 생략 가능합니다.

> 주의: 실제 저장소의 현재 폴더명 중 일부가 `upset-fegg-*`(오타로 보임, `kegg`의 오타 추정)로 되어 있습니다 — 앞으로 새로 export할 때는 `upset-kegg-*`로 통일해 주세요.

---

## 폴더 존재 규칙

| 폴더 | 있어야 하는 경우 |
|---|---|
| `cross_condition_heatmap_semantic-{bp,kegg}/` | 그 온톨로지에 term이 여러 개 있어 히트맵이 의미 있을 때 (term이 너무 적으면 생략 가능, 위 안내 참고) |
| `cross_condition_dotplot_semantic-{bp,kegg}/` (또는 `cross_condition_top30_dotplot_semantic-bp/`) | 항상 |
| `upset-{bp,kegg}-{up,down}/` | 겹치는 term이 2개 조건 이상 존재할 때 |
