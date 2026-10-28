# 0007. 렌더러는 결과를 그린다. 계산하지 않는다

- 상태: 채택
- 날짜: 2026-10-27

## 배경

그림은 숫자를 인쇄한다. 괄호 아래의 P값, 모서리의 Pearson r, 범례의 AUC, 맞춤 곡선 옆의 EC50, 생존 패널의 log-rank P. 그 숫자는 어딘가에서 계산된다. fig-atlas에서는 그 계산이 렌더러 안으로 새어 들어오고 있었다. `dose_response`는 `scipy.optimize.curve_fit`으로 4PL을 적합하고, `group_scatter`는 `scipy.stats.pearsonr`을 돌려 r과 P를 인쇄하며, 새 그림 종류 확장 계획(v2)은 짝지은 검정·사후 비교·ROC/AUC·곡선 맞춤 프레임워크를 담은 통계 층을 제안했다(`plans/PLAN_PLOT_CATALOG.md`).

이는 패키지가 스스로에 대해 말하는 것과 어긋난다(`docs/guide/01-why.md`): *"It does not choose analysis methods or statistical criteria."* 또한 연구의 진짜 검정 옆에 두 번째 구현을 놓는다. 그 구현은 검정 선택의 근거가 되는 설계(짝짓기, 블록, 공변량, 결측)를 볼 수 없다.

## 결정

**그림이 인쇄하는 숫자는 데이터로 들어온다.** 분석 스크립트(scipy, R, statsmodels — 연구가 쓰는 무엇이든)가 검정·적합·모형을 실행하고, 결과를 렌더러가 이름으로 가리킬 수 있는 컬럼으로 쓴다(`r_col`, `pvalue_col`, `fpr`/`tpr`, 맞춤 모수, 곡선 좌표). 그리고 검정 표를 `fig_atlas.stats.record(table, name=...)`로 등록한다. 빌드가 그 표를 그림 옆에 쓰고, `verify`가 그것이 있는지 확인한다.

**렌더러는 자기 모양의 기하를 계산할 수 있다** — 곡선 자체가 되는 추정량이다. Kaplan-Meier 계단 함수, 선의 평균과 신뢰띠, 덴드로그램이 정하는 행 순서, violin이 그리는 밀도, 점 위에 그은 최소제곱 직선. 이것은 그리기이지 추론이 아니며, 렌더러는 주어진 데이터로 그것을 그릴 수 있어야 한다.

**`fig_atlas.stats`에 남는 것은 표시 계층이다**: `stars()`(임계값은 config에서), `adjust()`(표시용 보정 p 열), `describe_stars()`(범례 문장), `record()`/`write()`(그림 옆 검정 표). 이미 있는 검정 함수(`two_group`, `compare_to_control`, `anova`)는 호환을 위해 남기되 확장하지 않는다. 새 작업은 분석 스크립트에서 계산한다.

## 결과

- 계약의 문법은 "값이 컬럼으로 들어온다"이다. `bar_scatter`(`pvalue_col`)와 `cis_linkage`(`pearson_r`)가 이미 그렇게 하고, 새 그림 종류가 이를 따른다.
- 감사는 `tests/test_renderer_purity.py`가 맡는다. 렌더러는 `scipy.cluster`/`scipy.spatial`(순서)을, `line_band`만 `scipy.stats`(CI 띠의 t 분위수)를 쓸 수 있다. 두 예외는 과도기이며 제거 카드를 이름으로 밝힌다: `dose_response`의 4PL 적합(E-04), `group_scatter`의 Pearson 폴백(E-04). 코드와 맞지 않게 된 허용 항목은 테스트를 실패시켜 목록이 썩지 않는다.
- 카탈로그 패널이 필요한 여섯 통계(짝지은 검정, 사후 비교, 상관·회귀, ROC/AUC, 곡선 맞춤, 분할표)의 레시피는 패키지 코드가 아니라 문서와 템플릿이다(`cmg-figures` 계획 카드 I-04).
- 재현성은 약해지지 않는다. 그림은 여전히 숫자를 담고, 이제 그 숫자를 어떤 검정이 만들었는지 말하는 표와 그 숫자를 그린 컬럼까지 담는다. 담지 않게 된 것은 검정의 두 번째, 숨은 구현이다.
- 분석 스크립트가 없는 경우(표를 잠깐 보는 정도)의 정직한 길은 짧다. 그림을 만드는 스크립트에서 값을 계산하고, 컬럼을 쓰고, 표를 등록하면 된다. `fa`가 대신 통계를 돌려 주지는 않는다.
