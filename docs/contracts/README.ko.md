# 데이터 번들 계약서 (2차 파이프라인용)

이 폴더의 문서들은 fig-atlas가 **그림을 그리기 위해 그대로 소비할 수 있는** 데이터 번들의 정확한 폴더/파일/컬럼 스펙입니다. 2차 분석 파이프라인(예: CMG-SeqViewer, 또는 그 뒤를 잇는 자동화 export 스텝)이 이 스펙대로 파일을 만들어 `raw_data/<study>/<project>/<bundle_name>/` 아래에 놓으면, fig-atlas 쪽에서는 **탐색·재집계·폴더 재구성 없이** config만 작성해서 바로 렌더링할 수 있습니다.

아래 표의 상단 3개는 오믹스 plot type의 컬럼 스펙으로, 오믹스 팩(`fig_atlas_omics/contracts/`)에 있습니다. 그 아래는 분야와 무관한 문서입니다: 이미지 번들 계약, 그리고 신규 plot type을 처음 요청할 때의 일반 번들 제출 절차.

| 계약서 | 적용 대상 | 예시 프로젝트 |
|---|---|---|
| [`de_go_bundle_contract.md`](../../fig_atlas_omics/contracts/de_go_bundle_contract.md) | 단일 데이터셋(하나의 비교조건) DE + GO/KEGG 인리치먼트 | `fig1-acute-1d-de`, `fig11-human-chronic-24h-de-go` 등 |
| [`integrated_bundle_contract.md`](../../fig_atlas_omics/contracts/integrated_bundle_contract.md) | 다중 데이터셋 통합 (time-series 클러스터 / co-expression 모듈) | `fig3-acute-1d-3d-integrated`, `fig7-acute-1d-chronic-24h-integrated`, `fig10-human-acute-1d-3d-integrated` |
| [`cross_condition_bundle_contract.md`](../../fig_atlas_omics/contracts/cross_condition_bundle_contract.md) | 여러 비교조건에 걸친 GO/KEGG 인리치먼트 교차비교 | `fig14-mouse-go-cross-comparison`, `fig15-human-go-cross-comparison` |
| [`new_plot_type_contract.md`](new_plot_type_contract.md) | **신규 plot type (위 3개에 해당하지 않는 모든 경우)** — 일반 번들 제출 구조 | `feature_enrichment_bundle`, `ma_plot_bundle`, ATAC 전용 번들 등 |
| [`image_bundle_contract.md`](image_bundle_contract.md) | 현미경 이미지·블롯·젤 (분야 무관): 채널별 원본 파일 + `pixel_size`·`channels` 메타데이터 | `pilot-imaging` (공개 BBBC013; [튜토리얼](../tutorials/imaging_figure.md)) |
| [`table_bundle_contract.md`](table_bundle_contract.md) | 범용 표 (분야 무관): 선 + 오차 띠(`line_band`), 효과 대 유의성 산점도(`threshold_scatter`). 열 이름은 `plot_params`에서 지정 | `examples/` ([첫 그림 튜토리얼](../tutorials/first_figure.md)) |

> **위치와 자동 검사 (2026-10-08, 로드맵 6a.2)**: 오믹스 전용 계약서 3개(DE+GO, 통합, 교차조건)와 ATAC 확장 계획은 오믹스 팩 `fig_atlas_omics/contracts/`로 옮겼습니다. 이 폴더에는 분야와 무관한 문서(이 README, 신규 plot type 절차)만 남습니다.
> 각 계약서는 기계로 검사할 수 있는 형태(`fig_atlas_omics/contracts/__init__.py`, 코어 계약은 `fig_atlas/contracts.py`)도 함께 갖습니다.
> - `fa bundle check <번들 폴더>`(또는 `--all`로 `raw_data/` 전체): 번들 구조, `plot_type`에 맞는 계약, 그릴 렌더러를 검사합니다. 렌더러가 꼭 필요로 하는 열이 없으면 **오류**, 계약서가 필수라고 적은 나머지 열이 없으면 **경고**입니다.
> - `fa bundle contracts`: 등록된 계약과 `plot_type` → 렌더러 매핑을 보여 줍니다.
> - 새 계약은 코드와 문서를 함께 추가합니다. 계약이 가리키는 문서가 없거나 렌더러가 없는 `plot_type`이면 `tests/test_plugins.py`가 실패합니다.

## 공통 원칙 (3개 계약서 모두에 적용)

1. **폴더 구조**: 한 프로젝트(하나의 최종 figure)는 `raw_data/<study>/<project_name>/` 아래에 여러 개의 **번들(bundle)** 서브폴더를 가집니다. 서브패널 하나 = 번들 하나입니다.
2. **번들 최소 요구사항**: 모든 번들은 최소한
   ```
   <bundle_name>/
     inputs/data.csv          # 그림이 바로 읽는 표 (아래 계약서별 컬럼 스펙 참고)
     metadata/metadata.yaml   # plot_type + plot_params (렌더러 파라미터의 "이 정도면 이렇게 그렸었다"는 기본값 스냅샷)
   ```
   을 갖춰야 합니다. `manifest.json`, `outputs/*.{png,svg,pdf}`, `scripts/figure.py`는 있으면 좋지만 fig-atlas 렌더링에는 필수가 아닙니다(참고/재현용).
3. **컬럼은 이름으로 매칭됩니다**: pandas가 컬럼명으로 읽으므로 **컬럼 순서는 중요하지 않지만, 이름은 대소문자까지 정확히 일치**해야 합니다(계약서에 명시된 그대로).
4. **원본 값은 절대 가공/반올림/재작명하지 않습니다**: 표시용 축약(`D1_vs_Control` → `D1` 같은 것)은 fig-atlas 쪽 config의 `*_rename_map`이 담당하는 영역이므로, 번들의 raw 값은 통계적으로 정확한 원본 그대로 내보내면 됩니다.
5. **"absent"는 행을 아예 안 만드는 것으로 표현**합니다: 어떤 term/조건 조합이 유의하지 않아 없는 경우, placeholder 행(NaN 채운 행 등)을 만들지 말고 그냥 그 행을 생략하세요. fig-atlas 쪽 렌더러가 "없음"으로 알아서 처리합니다.
6. **`metadata.yaml`의 `plot_params`는 초기값 스냅샷일 뿐, 최종 스타일 소스는 아닙니다**: fig-atlas 쪽에서 프로젝트별 `configs/config_<project>.yaml`이 최종 소스이므로, 여기 적힌 색상/폰트크기/threshold 등은 "이 데이터를 어떻게 한 번 그려봤는지"의 참고값 정도로만 정확하면 됩니다. 다만 **어떤 필드가 존재하는지(스키마)는 계약서와 정확히 일치**해야 자동 통합이 됩니다.

## 이 계약서가 없애주는 작업

지금까지는 CMG-SeqViewer(또는 유사 2차 도구)에서 매번 같은 파라미터로 반복 탐색한 결과물을 사람이 직접 훑어보고, 폴더 이름을 정하고, 파일을 `inputs/data.csv` 위치로 옮기고, 없는 컬럼을 확인하는 작업을 거쳐야 했습니다. 이 계약서대로 export 스텝이 자동화되면, fig-atlas 쪽에서 할 일은 **config 작성 + (필요하면) 이미 있는 렌더러 재사용**뿐입니다 — 새로운 레이아웃이 정말 필요할 때만 새 렌더러/새 계약서를 추가합니다.
