# fig-atlas 그림 종류(plot catalog) 확장 계획

> 작성일: 2026-10-24 (개정 2026-10-27) · 계획 판: **v2** (개정 기록은 맨 아래)
> 대상: 패키지 저장소 `fig-atlas`의 `fig_atlas/renderers/`, `fig_atlas/stats.py`, `fig_atlas/contracts.py`, `examples/gallery/`, `tests/`, 문서 갤러리(`docs/reference/gallery.md`)
> 관련 문서: [ROADMAP_ECOSYSTEM_STRATEGY.md](ROADMAP_ECOSYSTEM_STRATEGY.md) (Phase 6a 범용 렌더러), fig-atlas `docs/decisions/0003-renderers-are-shapes.md`, `AGENTS.md` §3 (asset accumulation)
> **상태의 정본**: [PLAN_PLOT_CATALOG.status.yaml](PLAN_PLOT_CATALOG.status.yaml) — 작업 하나하나의 상태·담당·커밋은 이 파일에만 적는다. 아래 표는 Phase 단위 요약이다.
> **상태 확인**: `python scripts/check_plan_plot_catalog.py` (cmg-figures 루트에서) — 상태 파일과 패키지에 실제로 있는 것을 대조한다(§9).

## 진행 상황

| Phase | 내용 | 상태 |
|---|---|---|
| 0 | 기반: 상태 파일·점검 스크립트, 갤러리 분류(family), 작업 카드 틀 | ✅ 완료: I-01 (`261f558`), I-02 (`50ab6eb`, G2 승인 2026-10-27) |
| 1 | 통계 층 확장 S-01–S-06 (짝지은 검정, 사후 검정, 상관·회귀, ROC, 곡선 맞춤, 분할표) | ⬜ 대기 (게이트 G1 뒤) |
| 2 | 우선순위 1 그림 8종 (PC-01–PC-08) | ⬜ 대기 |
| 3 | 기존 그림 고도화 E-01–E-06 (통계 괄호, 축 옵션 등) | ⬜ 대기 |
| 4 | 우선순위 2 그림 (PC-09–PC-18) | ⬜ 대기 |
| 5 | 우선순위 3 그림 + 릴리스 정리 (버전·CHANGELOG·갤러리 개편) | ⬜ 대기 |

범례: ✅ 완료 · 🔄 진행 중 · ⬜ 대기 · ⏸ 보류(게이트 대기) · ⛔ 막힘

---

## 1. 배경과 목표

`examples/gallery/`에 있는 그림 종류는 **코드 없이 데이터 형식만 맞추면 그려지는 그림**이다. 연구자는 폴더를 복사하고 표를 바꾼 뒤 `fa ingest bundle`을 실행한다. 일반 사용자에게 이 목록은 Prism이나 Origin의 그래프 목록과 같은 의미다. 목록이 넓을수록 코딩 없이 해결되는 일이 늘어난다.

**현황 (2026-10-24, fig-atlas `d114848`)**
- 등록된 렌더러 이름 54개(코어·오믹스 팩·레시피; 오믹스 레시피 2개는 팩 렌더러와 이름을 같이 쓴다). 모두 갤러리 그림이 있다(`tests/test_gallery_coverage.py`가 강제).
- 코드 없이 그리는 plot_type 25개. 모두 예제 번들과 계약이 있다(같은 테스트가 강제).
  - 열(column): `bar_scatter`, `boxplot`, `violin`, `histogram`
  - XY: `line_band`, `dose_response`(4PL 맞춤), `group_scatter`, `threshold_scatter`
  - 생존: `survival`
  - 효과 크기: `effect_dots`
  - 부분과 전체: `stacked_bar`, `venn`
  - 다변량: `heatmap`, `multi_group_heatmap`, `pca`
  - 이미지: `image_panel`
  - 오믹스 팩: `volcano`, `ma_plot`, `go_bar`, `go_cluster_dot`, `count_summary`, `cross_condition_heatmap`, `cross_condition_dotplot`, `motif_dotplot`, `peak_feature_enrichment`
- 통계 층(`fig_atlas.stats`): 두 그룹 검정(Welch, Student, Mann-Whitney), 대조군 대비 비교, 일원 ANOVA, 다중검정 보정(Bonferroni, Holm, BH), 별표 규칙. 짝지은 검정·사후 검정·상관·회귀·ROC는 없다.

**목표**
1. 실험 생물학 논문에 흔한 그림 종류를 코드 없이 그릴 수 있게 한다(Prism의 그래프 분류 기준으로 빈 곳을 채운다).
2. 새 종류마다 fig-atlas의 보장(설정이 정본, 인쇄 크기, preflight, 출처 기록, 검정표)을 그대로 갖게 한다. 종류 수보다 이 보장이 우선이다.
3. 기존 종류를 고도화한다(통계 괄호, 축 옵션 등). 새 종류만큼 사용성에 영향이 크다.
4. 다른 AI 에이전트나 서브에이전트가 이 문서와 상태 파일만 보고 작업 하나를 독립적으로 맡아 끝낼 수 있게 한다.

**하지 않는 것**
- 대화형 편집(GUI에서 끌어서 고치기). 고치는 길은 config 하나다.
- 3D 그림, 장식용 그림(3D 막대, 그림자 효과). 인쇄 논문에서 읽기 어렵다.
- 분석 결과를 손으로 덮어쓰는 기능. 검정·맞춤은 통계 층에서 하고 표로 남긴다.
- 분야 전용 그림의 코어 편입(유전체 트랙 등은 팩에 둔다, ADR 0003).

## 2. 원칙

1. **모양이지 분야가 아니다.** 새 그림은 코어(`fig_atlas/renderers/`)에 둔다. 분야 고유의 열 이름·기본값은 레시피나 팩에 둔다(ADR 0003).
2. **한 종류 = 한 묶음.** 렌더러, 스키마, 계약, ingest 연결, 예제 번들, 스냅샷 사례, 테스트, 문서가 함께 들어와야 "추가됨"이다(§5 완성 정의). 빠진 조각은 커버리지 테스트가 CI에서 잡는다.
3. **분석은 통계 층에서.** 검정, 사후 비교, 상관, 회귀, 곡선 맞춤, AUC는 `fig_atlas.stats`(또는 그 아래 모듈)에서 계산하고 `stats.record`로 표를 남긴다. 렌더러 안에서 scipy를 직접 부르지 않는다(AGENTS.md §4.6).
4. **설정이 정본.** 보이는 모든 값은 스키마에 선언하고 config에서 바꾼다. 하드코딩 금지(`fa lint --hardcoded --check`).
5. **기존 것을 깨지 않는다.** 기존 예제 데이터(`examples/make_gallery.py`의 난수 순서)와 스냅샷이 바뀌면 안 된다. 기존 렌더러에 옵션을 더할 때 기본값은 지금 모양 그대로다.
6. **가볍게 의존한다.** 새 필수 의존성은 게이트 G3에서 승인받는다. 가능하면 scipy·numpy로 구현하고, 검증용 참값은 독립 구현(R, statsmodels 등)에서 받아 테스트 고정값으로 둔다.

## 3. 빈 곳 분석과 후보 목록

Prism의 그래프 분류(XY, 열, 그룹, 분할표, 생존, 부분과 전체, 다변수)와 Origin의 2D 그래프 목록에 비춰 본 빈 곳이다. **ID는 바꾸지 않는다**(상태 파일과 커밋 메시지가 이 ID를 쓴다). 우선순위와 범위는 게이트 G1에서 연구자가 확정한다.

### 3.1 통계 층 확장 (S) — 그림의 전제

| ID | 내용 | 쓰는 그림 | 참값 출처(검증) |
|---|---|---|---|
| S-01 | 짝지은 검정: paired t, Wilcoxon signed-rank | PC-01 | scipy, R `t.test(paired=TRUE)`, `wilcox.test` |
| S-02 | 사후 다중 비교: Tukey HSD, Dunnett(대조군), Kruskal-Wallis + Dunn | PC-02, E-01 | R `TukeyHSD`, `DescTools::DunnettTest`, `dunn.test` |
| S-03 | 상관(Pearson, Spearman)과 선형 회귀(기울기·절편·R²·신뢰띠·예측띠) | PC-03, PC-07, PC-08 | scipy, R `cor.test`, `lm`/`predict` |
| S-04 | ROC 곡선과 AUC(신뢰구간: DeLong 또는 bootstrap) | PC-06 | R `pROC` |
| S-05 | 곡선 맞춤 일반화: 모형 목록(선형, 지수 증가·감소, Michaelis-Menten, 4PL), 매개변수와 신뢰구간 | PC-10, `dose_response` 이관 | R `nls`, Prism 예제 데이터의 공개 결과 |
| S-06 | 분할표: chi-square, Fisher 정확검정, 비율의 신뢰구간 | PC-18 | scipy, R `chisq.test`, `fisher.test` |

### 3.2 새 그림 (PC)

| ID | 그림 | 분류 | 데이터 모양(긴 형식 표) | 통계 | 우선순위 |
|---|---|---|---|---|---|
| PC-01 | 전후 비교(before–after, 짝지은 점과 선) | 열 | subject, condition, value | S-01 | P1 |
| PC-02 | 그룹 막대(두 요인, 평균±SD/SEM, 개별 점) | 그룹 | factor_a, factor_b, value | S-02 | P1 |
| PC-03 | 상관 산점도(회귀선, 신뢰띠, r·p 표시) | XY | x, y, (group) | S-03 | P1 |
| PC-04 | raincloud(반쪽 violin + box + 점) | 열 | group, value | (선택) S-02 | P1 |
| PC-05 | 열 산점도(column scatter: 점 + 평균/중앙값 선 + 오차) | 열 | group, value | (선택) S-02 | P1 |
| PC-06 | ROC 곡선(AUC, 신뢰구간, 여러 표지자) | 진단 | label, score, (marker) | S-04 | P1 |
| PC-07 | Bland–Altman(차이 대 평균, 일치 한계) | 방법 비교 | method_a, method_b | S-03 | P1 |
| PC-08 | 상관 행렬(삼각 마스크, 값 표시, 유의성) | 다변수 | 넓은 표(변수 열) | S-03 | P1 |
| PC-09 | QQ plot(정규성) | 분포 | value, (group) | — | P2 |
| PC-10 | XY 곡선 맞춤(모형 선택, 오차 막대) | XY | x, y, (group) | S-05 | P2 |
| PC-11 | 이중 y축 선 그림 | XY | x, y1, y2 | — | P2 |
| PC-12 | bubble chart(x, y, 크기, 색) | 다변수 | x, y, size, (color) | — | P2 |
| PC-13 | 2D 밀도(hexbin/등고선) | XY | x, y | — | P2 |
| PC-14 | waterfall(순위 막대, 예: 종양 반응) | 열 | item, value, (group) | — | P2 |
| PC-15 | UpSet(집합 교집합) | 부분과 전체 | dataset, item | — | P2 (오믹스 계약서에 "렌더러 구현 대기"로 남은 수요) |
| PC-16 | 누적 영역(stacked area) | 부분과 전체 | x, part, value | — | P2 |
| PC-17 | 도넛/파이(비율, 선택적으로) | 부분과 전체 | part, value | — | P2 (게이트 G1: 넣을지 결정) |
| PC-18 | 분할표 그림(비율 막대 + 검정) | 분할표 | group, outcome, count | S-06 | P2 |
| PC-19 | 레이더(radar) | 다변수 | item, axis, value | — | P3 |
| PC-20 | 극좌표(polar/rose) | 순환 데이터 | angle, value | — | P3 |
| PC-21 | sankey/alluvial | 흐름 | source, target, value | — | P3 |
| PC-22 | 삼각 좌표(ternary) | 조성 | a, b, c | — | P3 |

### 3.3 기존 그림 고도화 (E)

| ID | 내용 | 대상 | 전제 |
|---|---|---|---|
| E-01 | 통계 괄호·별표 옵션(검정과 보정은 config, 표는 `stats.record`) | `bar_scatter`, `boxplot`, `violin`, PC-02/04/05 | S-02 |
| E-02 | 축 옵션 공통화: 로그, 끊긴 축(broken axis), 축 범위 | 열·XY 그림 | — |
| E-03 | 평균±SD/SEM/95%CI 겹치기, 개별 점 jitter·beeswarm | 열 그림 | — |
| E-04 | `dose_response`를 S-05 맞춤 틀로 이관(결과 동일 확인) | `dose_response` | S-05 |
| E-05 | `line_band`에 오차 막대 모드(띠 대신) | `line_band` | — |
| E-06 | `survival`에 number-at-risk 표와 log-rank 검정표 | `survival` | S-01 계열 |

## 4. 작업 카드 (작업 하나의 명세)

작업마다 상태 파일에 카드가 있다. 에이전트는 **카드와 이 문서만 읽고** 시작할 수 있어야 한다. 카드의 필드:

```yaml
- id: PC-03                      # 고정 ID (§3)
  title: correlation scatter with regression line
  kind: plot                     # plot | stats | enhance | infra
  phase: 2
  priority: P1
  status: todo                   # todo | claimed | in_review | done | blocked | dropped
  depends_on: [S-03]             # 이 ID들이 done이어야 시작
  plot_type: correlation_scatter # 새 plot_type / 렌더러 이름 (코어, 분야 이름 금지)
  data: "x, y, optional group"   # 긴 형식 표의 열 역할
  owner: null                    # 맡은 에이전트/사람 (예: "claude-code@KimYG 2026-10-25")
  branch: null                   # fig-atlas 브랜치 (예: plot/PC-03-correlation-scatter)
  commits: []                    # 완료 커밋 해시
  version: null                  # 들어간 패키지 버전 (예: 0.2.0.dev1)
  review: null                   # 게이트 G2 결과 (예: "approved 2026-11-02")
  notes: ""
```

## 5. 완성 정의 (Definition of Done)

### 5.1 그림(PC) 하나

- [ ] **렌더러**: `fa new renderer <name> --plot-type <type> --family <family>`으로 시작한 코어 모듈. 모양은 `(ax, df, params)`(여러 축이 필요하면 `(fig, df, params)`). 그린 데이터 표를 반환한다(Source Data용).
- [ ] **분류**: 렌더러 모듈에 `FAMILY`(갤러리 분류, `fig_atlas/family.py`); `tests/test_gallery_coverage.py`가 모든 렌더러에 하나를 요구한다.
- [ ] **스키마**: 모든 매개변수에 역할·단위·조정 안내. 열 이름은 `*_col` 매개변수로(역할 열).
- [ ] **계약**: 코어 계약(`fig_atlas/contracts.py`, `role_columns`)과 ingest 연결(`plot_type`).
- [ ] **예제 번들**: `examples/make_gallery.py`에 합성 데이터 생성 함수를 **맨 뒤에** 추가(기존 예제 데이터 불변), 설명 주석이 달린 `metadata.yaml`.
- [ ] **스냅샷 사례**: `tests/renderers/cases.py`에 사례(배치·모드가 여럿이면 변형 사례도).
- [ ] **단위 테스트**: 빈 표, 결측값, 그룹 하나, 열 이름 바꾸기, 반환 표의 내용.
- [ ] **통계**(해당 시): `fig_atlas.stats` 경유, 그림에 표시하는 값은 `stats.record`와 live claim으로.
- [ ] **검사 통과**: `pytest`(전체), `fa reference --check`, `fa lint --hardcoded --check`, 세 운영체제 CI.
- [ ] **시각 검토(게이트 G2)**: 갤러리 그림을 연구자가 확인하고 승인.
- [ ] **기록**: CHANGELOG "Added — plot types"에 한 줄, 상태 파일 `done` + 커밋 + 버전.

### 5.2 통계(S) 하나

- [ ] `fig_atlas.stats`의 함수, 표(DataFrame) 반환, 범례용 설명 함수(`describe` 계열).
- [ ] **참값 테스트**: 독립 구현(R 등)으로 계산한 값을 `tests/data/stats_reference/<id>.csv`에 출처·버전·명령과 함께 저장하고 허용오차(기본 상대 1e-6, 반복 계산은 명시) 안에서 일치.
- [ ] 경계 사례: n<3, 동률, 결측, 분산 0, 한 그룹.
- [ ] `docs/reference/api.md` 자동 생성 반영(`fa reference`).

### 5.3 고도화(E) 하나

- [ ] 기본값이면 기존 그림이 바뀌지 않는다: 기존 스냅샷 전부 그대로(갱신 금지).
- [ ] 새 옵션을 쓰는 변형 스냅샷 사례 하나 이상, 예제 번들 하나 이상에서 사용.
- [ ] 스키마 갱신, `fa reference --check`.

## 6. 검증 전략

| 층 | 무엇을 | 어떻게 | 언제 |
|---|---|---|---|
| V1 단위 | 데이터 처리, 반환 표, 오류 메시지 | pytest, 작업별 테스트 파일 | 매 커밋 |
| V2 구조 스냅샷 | 그려진 요소(글자, 크기, 색, 위치) | `tests/renderers/test_renderer_snapshots.py`(운영체제 간 글꼴 차이를 허용하는 구조 비교) | 매 커밋 |
| V3 통계 정확성 | 검정·맞춤·AUC 값 | 독립 구현의 참값 고정 파일과 대조(§5.2), 출처 기록 | S 작업마다 |
| V4 예제 빌드 | 예제 번들이 계약을 지키고 85 mm 한 단에서 preflight 오류·경고 0 | `tests/test_gallery_examples.py` | 매 커밋 |
| V5 커버리지 | 렌더러마다 갤러리 그림, plot_type마다 예제·계약 | `tests/test_gallery_coverage.py` | 매 커밋 |
| V6 설정·문서 | 스키마-코드 일치, 하드코딩 없음, 레퍼런스 최신 | `fa reference --check`, `fa lint --hardcoded --check`, 스키마 테스트 | 매 커밋(CI) |
| V7 운영체제 | Linux, Windows, macOS | GitHub CI matrix | 매 push |
| V8 불변 | 기존 예제 데이터·스냅샷이 바뀌지 않음 | `git diff --stat examples/gallery tests/renderers/snapshots`가 새 파일만 보여야 함(점검 스크립트가 확인) | 작업 완료 시 |
| V9 시각 검토 | 읽기 쉬운가, 저널 그림으로 쓸 만한가 | 갤러리 그림 묶음을 연구자가 검토(게이트 G2). 참고로 Prism/Origin의 같은 그림과 요소 대조(축, 범례, 오차 표시, 통계 표시) | 묶음마다 |
| V10 실사용 | 실제 연구 데이터에서 동작 | 우선순위 1 그림은 cmg-figures 탐색 프로젝트 하나에서 써 본다(Case B) | Phase 2 끝 |

**한 작업의 완료 보고에 반드시 들어갈 증거**: 실행한 명령과 결과 요약(테스트 수·통과), 새 갤러리 그림 경로, preflight 결과, 바뀐 파일 목록, V8 확인 결과.

## 7. Phase별 계획과 완료 기준

### Phase 0 — 기반
- I-01: 상태 파일과 점검 스크립트(이 문서와 함께 작성).
- I-02: 갤러리 분류: 렌더러 모듈에 `FAMILY`(column, xy, grouped, survival, parts_of_whole, multivariate, diagnostic, image, schematic, field)를 선언하고(정본은 `fig_atlas/family.py`), plot_type은 그 렌더러의 분류를 물려받으며, 갤러리 페이지를 분류별로 묶는다.
- 작업 카드 틀과 서브에이전트 지시문 틀(§8.4).
- **완료 기준**: 점검 스크립트가 현재 상태(25 plot_type)를 정확히 보고, 갤러리가 분류별로 나뉜다.

### Phase 1 — 통계 층 (S-01–S-06)
- **게이트 G1**(시작 전): 후보 목록·우선순위·범위(PC-17 도넛 포함 여부 등) 확정, 참값을 만들 도구(R 설치 여부) 확인.
- S-01–S-04가 Phase 2의 전제. S-05·S-06은 Phase 4 전까지.
- **완료 기준**: 각 S의 참값 테스트 통과, API 레퍼런스 반영.

### Phase 2 — 우선순위 1 그림 (PC-01–PC-08)
- 서로 의존이 없으므로 병렬로 진행할 수 있다(§8.3의 충돌 규칙).
- **게이트 G2**: 4개씩 두 묶음으로 시각 검토.
- **완료 기준**: 8종 모두 §5.1 완료, V10 실사용 1건, 패키지 버전 0.2.0.dev 계열로 기록(게이트 G4에서 정식 0.2.0 여부 결정).

### Phase 3 — 고도화 (E-01–E-06)
- E-01(통계 괄호)이 가장 중요. S-02 뒤에 시작.
- **완료 기준**: §5.3, 기존 스냅샷 불변.

### Phase 4 — 우선순위 2 그림 (PC-09–PC-18)
- **완료 기준**: §5.1, 게이트 G2 묶음 검토.

### Phase 5 — 우선순위 3 + 릴리스 정리
- PC-19–PC-22는 수요를 다시 확인한 뒤 진행(게이트 G1 재검토).
- 릴리스: 버전, CHANGELOG, 갤러리 첫 화면에 "그림 종류 목록" 표, 논문 원고의 렌더러 수(live 값) 확인.

## 8. 에이전트 작업 규약

### 8.1 작업 하나의 흐름
1. **고르기**: 점검 스크립트의 "can start now" 목록에서 고른다(`status: todo`, `depends_on`이 모두 `done`, 그 Phase의 게이트 통과). 우선순위(P1 → P2 → P3), 같은 우선순위에서는 ID 순.
2. **맡기**: 카드에 `status: claimed`, `owner`, `branch`를 적고 cmg-figures에 커밋한다(`plan(plot-catalog): claim PC-03`). 다른 owner가 있는 카드는 건드리지 않는다. 48시간 넘게 진척 없는 claim은 사람에게 물어본 뒤 넘겨받는다.
3. **작업**: fig-atlas에서 `branch` 브랜치(또는 서브에이전트는 worktree)에서 §5 체크리스트대로.
4. **검토 요청**: 체크리스트의 자동 검증이 모두 통과하면 `status: in_review`, 증거(§6 끝)를 카드 `notes`나 보고서에 남긴다.
5. **완료**: 게이트 G2 승인 후 main에 합치고 push, CI 확인, 카드에 `done`, `commits`, `version`, `review`를 적는다.
6. **막힘**: 진행할 수 없으면 `status: blocked`와 이유. 설계 판단이 필요한 것은 사람에게 묻는다(스스로 범위를 바꾸지 않는다).

### 8.2 커밋과 브랜치 규칙
- fig-atlas 브랜치: `plot/<ID>-<짧은 이름>`, `stats/<ID>-...`, `enhance/<ID>-...`.
- 커밋 메시지 첫 줄에 ID: `feat(renderers): PC-03 correlation scatter ...`, `feat(stats): S-03 ...`.
- 한 브랜치 = 작업 하나. 다른 작업의 파일을 고치지 않는다.

### 8.3 병렬 작업과 충돌
여러 작업이 함께 손대는 공유 파일이 있다. 규칙:

| 공유 파일 | 규칙 |
|---|---|
| `fig_atlas/renderers/__init__.py`(export), `fig_atlas/contracts.py`(계약 목록·ingest) | 맨 끝에 추가만. 합칠 때 순서대로 rebase |
| `tests/renderers/cases.py`(사례, `CASES`) | 함수와 `CASES` 항목을 맨 끝에 추가만 |
| `examples/make_gallery.py` | 생성 함수·`META`·`makers` 맨 끝에 추가만(기존 난수 순서 보존). 합칠 때 두 번째 작업은 rebase 후 `python examples/make_gallery.py`로 재생성하고 V8 확인 |
| `CHANGELOG.md` | 한 줄 추가만 |
| `docs/reference/*`(자동 생성) | 직접 고치지 않는다. 합친 뒤 `fa reference`로 재생성. 이 PC에서 기존 그림이 글꼴 차이로 다시 그려지면 새 그림만 남기고 되돌린다 |

- 병렬로 돌리는 서브에이전트는 저장소 사본(worktree)에서 일하고, 합치는 것은 한 명(조정자)이 순서대로 한다.
- 같은 공유 파일을 크게 바꾸는 작업(예: Phase 0의 갤러리 분류)은 병렬 작업 전에 끝낸다.

### 8.4 서브에이전트 지시문 틀
```
fig-atlas 그림 종류 확장 계획의 작업 <ID>를 맡아라.
읽을 것: cmg-figures/docs/PLAN_PLOT_CATALOG.md (§2 원칙, §5 완성 정의, §6 검증, §8 규약),
         cmg-figures/docs/PLAN_PLOT_CATALOG.status.yaml 의 <ID> 카드, fig-atlas/AGENTS.md.
작업 위치: fig-atlas worktree, 브랜치 <branch>. 공유 파일은 §8.3 규칙대로 맨 끝에 추가만.
끝나면 보고: (1) 바뀐 파일, (2) 실행한 검증 명령과 결과, (3) 갤러리 그림 경로,
(4) V8(기존 예제·스냅샷 불변) 결과, (5) 남은 문제. main에 합치거나 push하지 말 것.
```

## 9. 상태 확인과 추적

- **정본**: `docs/PLAN_PLOT_CATALOG.status.yaml`. `plan_version`(이 문서의 판), `package_version`(마지막으로 확인한 fig-atlas 버전·커밋), `gates`(게이트 상태: `pending` 또는 `passed <날짜> <메모>`), `phase_gates`(Phase별로 먼저 통과해야 할 게이트), 작업 카드 목록. 게이트를 통과시키는 것은 사람만 한다.
- **점검 스크립트**: `python scripts/check_plan_plot_catalog.py` (cmg-figures 루트, fig-atlas 환경)
  - 카드 목록을 상태별로 요약하고, 시작할 수 있는 카드(의존 충족, todo)를 보여 준다.
  - `done`인 PC 카드마다 패키지에 실제로 있는지 확인: 렌더러 등록, ingest 연결, 계약, 예제 번들, 스냅샷 사례, 갤러리 그림. 빠지면 불일치로 보고(종료 코드 1).
  - 패키지에는 있는데 카드가 `done`이 아닌 것도 보고(상태 파일을 고치지 않은 경우).
  - 의존 순서 위반(`depends_on`이 끝나지 않았는데 claimed 이상)과 게이트 위반(Phase의 게이트가 열려 있는데 claimed 이상)을 보고.
- **버전**: fig-atlas는 `0.1.0.devN` → Phase 2 완료 시 0.2.0 후보(게이트 G4). 그림 종류가 들어갈 때마다 CHANGELOG `[Unreleased]`의 "Added — plot types"에 ID와 함께 한 줄. 카드의 `version`에 들어간 버전을 적는다.
- **계획의 판**: 범위·우선순위·규칙이 바뀌면 이 문서 맨 아래 개정 기록에 `v<N>`을 더하고 상태 파일의 `plan_version`을 올린다. 작업 상태 변경은 판을 올리지 않는다.

## 10. 위험과 대응

| 위험 | 대응 |
|---|---|
| 공유 파일 충돌(병렬 작업) | §8.3 맨 끝 추가 규칙, 조정자가 순서대로 합침, V8 점검 |
| 통계 구현 오류 | V3 참값 테스트(독립 구현), 경계 사례, 설명 함수로 범례와 일치 |
| 렌더러가 커지고 옵션이 엉킴 | 한 렌더러 = 한 모양. 비슷한 모양은 레시피로(예: 열 산점도와 bar_scatter의 관계 정리) |
| 기본값이 출판 크기에 맞지 않음 | 예제는 85 mm 한 단에서 preflight 0, 기본 글자 크기는 print 프리셋을 따름 |
| 새 의존성 증가 | 게이트 G3, 가능하면 scipy·numpy로 |
| 시각 품질을 자동 검사가 못 잡음 | 게이트 G2 사람 검토, 이번 갤러리 작업에서 찾은 유형(색 막대·범례 겹침)을 preflight 검사로 키움 |
| 에이전트가 범위를 임의로 넓힘 | 카드 범위 밖은 `notes`에 제안만, 결정은 사람 |

## 11. 게이트 (연구자 결정)

| 게이트 | 시점 | 결정할 것 |
|---|---|---|
| G1 | Phase 1 시작 전 (Phase 5 전에 다시) | 후보 목록·우선순위·범위, PC-17(도넛/파이) 포함 여부, 참값 도구(R 사용 가능 여부) |
| G2 | 그림 묶음마다 | 갤러리 그림 시각 승인 |
| G3 | 새 필수 의존성이 필요할 때 | 추가 여부 |
| G4 | Phase 2 완료 시 | 0.2.0 정식 버전으로 낼지 |

## 12. 개정 기록

| 판 | 날짜 | 내용 |
|---|---|---|
| v1 | 2026-10-24 | 첫 작성: 후보 S 6·PC 22·E 6, 완성 정의, 검증 층 V1–V10, 에이전트 규약, 상태 파일·점검 스크립트 |
| v2 | 2026-10-27 | I-02에서 family 목록에 `schematic`(도식·패널 태그 같은 레이아웃 도우미)을 더하고, family의 정본을 계약이 아니라 렌더러 모듈의 `FAMILY`로 확정(plot_type은 ingest_map으로 상속). §5.1 완성 정의에 분류 항목 추가 |
