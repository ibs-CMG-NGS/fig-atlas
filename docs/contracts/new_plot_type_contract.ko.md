# 계약서 0: 신규 Plot Type 요청 — 일반 번들 제출 스펙

**목적**: 아직 fig-atlas에 존재하지 않는 새로운 형태의 시각화를 처음 요청할 때,  
upstream pipeline이 제출해야 하는 번들의 **일반 구조와 필수 요소**를 정의합니다.

기존 3개 계약서(`de_go`, `integrated`, `cross_condition`)에 해당하는 그림은  
해당 계약서를 따르면 됩니다. 이 문서는 **그 어디에도 해당하지 않는 신규 plot type**에 적용됩니다.

---

## 번들 폴더 구조 (최소 요구사항)

```
raw_data/<study>/<project_name>/<bundle_name>/
  inputs/
    data.csv            # 필수 — 렌더러가 직접 읽는 표 (아래 규칙 참고)
  metadata/
    metadata.yaml       # 필수 — plot_type + plot_params 스냅샷
  example/
    plot.png            # 강력 권장 — 참고용 출력 이미지 (없으면 설명으로 대체)
    script.R            # 선택 — 이 데이터로 처음 그렸던 원본 스크립트 (있으면 렌더러 합성에 참고)
```

한 프로젝트(최종 figure 하나) = 여러 번들의 집합.  
서브패널 하나 = 번들 하나.

---

## 1. `inputs/data.csv` 작성 규칙

| 규칙 | 설명 |
|---|---|
| **컬럼명 대소문자 일치** | pandas가 컬럼명으로 매칭하므로 이름은 계약서/metadata.yaml에 적힌 그대로 |
| **원본값 보존** | 로그변환·반올림·표시용 반올림 금지 — 축약 이름 변환은 fig-atlas config에서 처리 |
| **전체 행 포함** | 통계 필터(padj < 0.05 등)를 적용하지 않은 전체 결과를 넣는 것이 원칙 — 임계값은 config가 담당 |
| **Absent = 행 없음** | 어떤 조합이 유의하지 않거나 결과가 없으면 NaN 행을 만들지 말고 그냥 행을 생략 |
| **컬럼 순서 무관** | 순서는 중요하지 않으나 이름은 정확히 일치 |
| **인코딩** | UTF-8, 줄바꿈 LF 권장 |

---

## 2. `metadata/metadata.yaml` 작성 규칙

```yaml
figure_id: <bundle_name>                  # 예: feature_enrichment_cluster1
plot_type: <renderer_slug>                # 예: peak_feature_enrichment
                                          #   (기존 렌더러가 없으면 새 이름을 제안)
data_source: <upstream_tool_and_version>  # 예: "cmg-seqviewer 3.2 / masigpro 1.4"

# 이 데이터로 처음 그렸을 때의 시각화 파라미터 스냅샷.
# fig-atlas 쪽에서 configs/config_<project>.yaml이 최종 소스가 되므로,
# 여기 값은 "한 번 그려봤을 때 잘 나온 값"이면 충분합니다.
# 어떤 필드가 존재하는지(스키마)는 정확히 기술해 주세요 — 값은 나중에 조정.
plot_params:
  # 예:
  # fdr_max: 0.05
  # geneset_col: "cluster_id"
  # feature_col: "Feature"
  # odds_ratio_col: "OddsRatio"
  # sig_color: "#e57373"
  # 이 plot_type에서 의미 있는 파라미터를 모두 열거

# 이 번들이 속한 컬럼/패널 위치 (알고 있을 경우만)
panel_position:
  col: 2          # 0-indexed
  row: 3          # 0-indexed, row 0 = summary row
```

**신규 렌더러가 필요한 경우**: `plot_type`에 새 이름을 적고, `example/plot.png`와 `example/script.R`을 함께 제출하면 fig-atlas 쪽에서 렌더러를 합성합니다(`SKILL.md` Case C 절차). 기존 렌더러 목록은 `docs/reference/renderer_inventory.md`를 참고하세요(범용 `fig_atlas/renderers/`, 오믹스 `fig_atlas_omics/renderers/`). 새로 합성한 렌더러는 파라미터 스키마(`SCHEMA`)를 함께 갖추며(테스트가 강제), 그 뒤로는 `fa param scaffold <renderer>`가 조정 가능한 전체 파라미터를 설명과 함께 보여 줍니다.

---

## 3. `example/plot.png` — 권장하는 이유

fig-atlas는 기존 3개 계약서에 속하지 않는 번들을 처음 소비할 때  
**렌더러 합성 → 렌더 결과 → 제출본과 시각적 비교** 루프를 돌립니다.  
예시 이미지 없이 컬럼 스펙만 있으면 이 루프를 돌릴 수 없어 레이아웃 확인에  
추가 왕복이 발생합니다. 가능하면 항상 포함해 주세요.

---

## 4. 기존 번들 타입과 신규 번들 타입 구분

| 이미 계약서가 있는 타입 | 이 문서를 사용하는 타입 |
|---|---|
| volcano, go_cluster_dot, go_bar, go_rrvgo_treemap | feature_enrichment, ma_plot |
| multi_group_heatmap, ts_profile, venn, count_summary | peak_feature_composition, coverage_track |
| cross_condition_heatmap, cross_condition_dotplot | ts_clusters (새 컬럼 조합), 기타 |

한 프로젝트 안에 기존 타입 번들과 신규 타입 번들이 섞여 있어도 됩니다.  
기존 타입 번들은 해당 계약서를, 신규 타입 번들은 이 문서를 따르면 됩니다.

---

## 5. 여러 번들을 한 번에 제출할 때 (새 프로젝트 전체)

프로젝트 루트에 `project_manifest.yaml`을 선택적으로 추가할 수 있습니다:

```yaml
project_name: lab-atac-acute-ts-integrated   # config_<project>.yaml의 이름
study: 2026-lab-atac
layout_family: atac_integrated                      # 레이아웃 패밀리 힌트 (선택)

# 번들 목록과 각각이 사용하는 렌더러 (없으면 metadata.yaml에서 추론)
bundles:
  - name: feature_enrichment_bundle
    plot_type: peak_feature_enrichment
    panel: [row1-6, col2]
  - name: ts_clusters_bundle
    plot_type: multi_group_heatmap
    panel: [row1-6, col0]
  # ...
```

이 파일이 있으면 fig-atlas 쪽에서 config를 자동 생성할 때 정확도가 높아집니다.

---

## 6. 제출 체크리스트

<!-- i18n: prose -->
```
[ ] inputs/data.csv — UTF-8, 전체 결과, 컬럼명 정확
[ ] metadata/metadata.yaml — figure_id, plot_type, data_source, plot_params 포함
[ ] example/plot.png — 기존 스크립트/도구로 한 번 그린 결과 (권장)
[ ] example/script.R 또는 script.py — 원본 스크립트 (선택, 있으면 렌더러 합성 품질 향상)
[ ] 신규 렌더러가 필요한 경우: plot_type에 새 이름을 적고 example/ 반드시 포함
[ ] 방향성이 있는 데이터(UP/DOWN)를 포함하면: 단일 방향인지 혼재 여부를 명시
```

---

*이 계약서 자체가 새 번들 타입을 명세하는 것은 아닙니다. 번들별 구체적 컬럼 스펙은  
해당 번들이 fig-atlas에 처음 소비된 이후 별도 계약서(혹은 기존 계약서 개정)로 문서화됩니다.*
