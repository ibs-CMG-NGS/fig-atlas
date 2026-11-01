# fig-atlas-template 설계 리뷰 및 개선 계획

> 작성일: 2026-07-14
> 대상: 저장소 전체 구조 (`fig_atlas/`, `Snakefile`, `scripts/`, `analysis/`, `configs/`, `figure_specs/`, `.agents/`)

## 구현 진행 상황

| 항목 | 상태 | 비고 |
|---|---|---|
| P1 — 렌더러 라이브러리화 | ✅ 완료 | `fig_atlas/renderers/` 신설, 4개 analysis 스크립트가 import로 전환. 중복 제거 검증 완료 |
| P2 — Snakefile config 기반 일반화 | ✅ 완료 | `CONFIG_PATH` 단일 소스로 DAG·자식 스크립트 동기화. pilot-test2 snakemake all → 4/4 PASS |
| P3 — 경로 전략 단일화 | ✅ 완료 | 전 산출물을 `outputs/<project>/`로 통일(gitignore), `OUTPUT_ROOT` 배선. 4개 프로젝트 + snakemake + 외부 OUTPUT_ROOT 검증 |
| P4 — 최소 테스트 + CI | ✅ 완료 | pytest 16개(config/publish/verify/params) 통과, GitHub Actions에서 테스트 + 예제 파이프라인 스모크 |
| P5 — 하드코딩 스타일 값 제거 | ✅ 완료 | go_dot 폰트 크기를 axes_label_size/title_size/tick_label_size에서 조회. 기본값 동작 보존 |
| P6 — 경로 정규화 함수 | ✅ 완료 | `_resolve`를 raw_root/output_root(env 포함)에 적용, analysis의 이중 join 제거. pytest 18개 |
| P7 — 환경 설정 표준화 | ✅ 완료 | SKILL.md `.venv` 하드코딩 제거(활성화 env + `python`), `figure1_heatmap` 명명 잔재 → `figure1_example` |

범례: ✅ 완료 · 🔄 진행 중 · ⬜ 대기

---

## 1. 전체 구조 요약

이 패키지는 **"과학 논문 피규어의 재현 가능한 생성"**을 위한 템플릿이다. 핵심은 세 가지 관심사를 분리하는 것이다.

| 관심사 | 위치 | 역할 |
|---|---|---|
| **What** | `figure_specs/figure_NN_*.py` | `FigureSpec` 데이터클래스로 피규어의 번호·제목·출처·패널 설명·주장 범위(claim boundary)를 선언 |
| **How** | `analysis/*.py` | 실제 통계·렌더링 로직, 산출물 파일 생성 |
| **Where** | `fig_atlas/publish.py`, `verify.py` | 파일 복사, README 자동 생성, 완결성 검증 |

여기에 YAML 설정 기반 스타일링, 환경변수 경로 오버라이드, Snakemake DAG, 그리고 커스텀 스크립트를 규격 번들로 흡수하는 "Ingest Plot" 자동화 프로토콜이 얹혀 있다.

---

## 2. 잘 설계된 점

1. **관심사 분리와 단일 진실 공급원(Single Source of Truth)**
   `FigureSpec` 하나가 publish, README 생성, verify를 모두 구동한다. 메타데이터가 여러 곳에 흩어져 서로 어긋날(drift) 여지가 구조적으로 차단된다. `@dataclass(frozen=True)`로 불변성까지 준 것도 적절하다.

2. **설정 계층화(precedence)의 명확함**
   `pilot-test2_analysis.py`의 파라미터 병합 순서 — `코드 기본값 < 번들 metadata.yaml < 글로벌 스타일 < config.yaml plots` — 는 재사용 라이브러리에서 매우 좋은 패턴이다. 렌더러가 모두 `params.get(name, default)`로 값을 조회하므로 하드코딩 없이 프로젝트별 재정의가 가능하다.

3. **원시 데이터 불변 원칙과 번들 규격**
   `raw_data/<project>/<bundle>/inputs/data.csv` + `metadata/metadata.yaml` 구조로 데이터를 읽기 전용으로 격리하고, 스타일은 별도 YAML로 분리한 것은 재현성 측면에서 옳은 결정이다.

4. **publish와 verify의 분리**
   생성(publish)과 완결성 검사(verify)를 분리해, 파일 존재·비어있음·README 섹션 유무를 CSV 리포트로 남긴다. CI에 걸기 좋은 형태다.

5. **환경변수 기반 경로 + 다중 프로젝트 지원**
   `config_<project>.yaml` + `spec_pattern` glob으로 한 저장소 안에서 여러 프로젝트를 격리해 운영할 수 있다.

---

## 3. 잘못 설계된 점 / 실제 결함

### 3.1 Snakefile이 실제로 동작하지 않을 가능성이 높음 (가장 심각)
- `configfile: "config.yaml"` — 실제 파일은 `configs/config.yaml`에 있다. 저장소 루트에서 `snakemake --dry-run`을 돌리면 설정 파일을 못 찾는다.
- `rule build_atlas`가 `figure_specs/figure_01_example.py`와 `.done/example_analysis`를 **하드코딩**한다. README는 "각 피규어마다 규칙 하나씩 추가"를 표방하지만 실제 DAG는 example 프로젝트에만 고정돼 있다.
- `expand("figure_specs/figure_01_example.py", fig=FIGS)` — 상수 문자열에 `expand`를 쓰고 있어 같은 경로를 N번 반복할 뿐 의미가 없다.
- Snakefile은 산출물을 루트 `manifests/`에 고정하는데, `pilot-test2` config는 `outputs/pilot-test2/manifests`를 쓴다. 프로젝트별 `CONFIG_PATH`가 DAG에 전혀 연결돼 있지 않아, 기본 예제 외에는 Snakemake 경로가 어긋난다.

### 3.2 문서(README)와 실제 구조의 불일치
- README의 프로젝트 구조도는 `outputs/figures/`, `outputs/<project>/…`를 그리지만, 기본 `config.yaml`은 루트 `figures/`·`manifests/`로 publish한다. 반면 프로젝트 config는 `outputs/` 아래로 보낸다. 커밋 대상(`figures/`)과 git-ignore 대상(`outputs/`)이 이중 스킴으로 섞여 혼란스럽다.
- README 구조도에 있는 `scripts/build_atlas.py`, `run_all.py` 등은 실제로 존재하지만, 그 위치·역할 설명이 `outputs/` 구조 설명과 어긋난다.

### 3.3 재사용 가능한 "핵심"이 정작 얇음 — 렌더러 중복
`fig_atlas/`는 "프로젝트 간 수정 불필요한 코어"를 표방하지만, 정작 가치 있고 복잡한 **렌더링 로직(volcano/heatmap/pca/venn/go_dot)이 라이브러리에 없다.** `render_volcano` 등이 `analysis/pilot_analysis.py`(584줄)와 `analysis/pilot-test2_analysis.py`(846줄)에 **복사-붙여넣기로 중복**돼 있다. 주석은 "공유한다(shared with)"고 적혀 있지만 실제로는 import가 아니라 사본이다. 렌더러를 고치면 두 곳을 동기화해야 하는 DRY 위반이며, 템플릿의 핵심 자산이 패키지화되지 않은 아키텍처 공백이다.

### 3.4 `output_root` / `OUTPUT_ROOT` 환경변수가 사실상 죽은 설정
README는 `OUTPUT_ROOT`로 출력 경로를 바꾸라고 안내하지만, analysis 스크립트들은 `CONFIG.project_root / "outputs" / <project>`를 하드코딩한다. `CONFIG.output_root`를 아무도 쓰지 않아, "config 기반 경로" 주장이 부분적으로 사실이 아니다.

### 3.5 `raw_root`의 이중 join 취약성
`RAW = CONFIG.project_root / CONFIG.raw_root`인데, `raw_root` 프로퍼티는 `RAW_ROOT` 환경변수가 절대경로일 때 절대경로를 반환할 수 있다. `project_root / <절대경로>`는 플랫폼에 따라 예측 불가한 결과를 낸다. 상대/절대 경로 처리 규칙이 모호하다.

### 3.6 설정 기반 원칙의 불완전한 준수
CLAUDE.md는 "폰트/축 크기 하드코딩 금지"를 규정하지만, `render_go_dot`은 xlabel `fontsize=11`, 제목 `fontsize=13` 등을 하드코딩하고 있다. 글로벌 rcParams와 개별 `params.get()` 조회, 그리고 하드코딩이 혼재한다.

### 3.7 자동화된 테스트·CI 부재
"재사용 템플릿"인데 단위 테스트가 전혀 없다. `verify_atlas`는 런타임 산출물 점검이지 코드 회귀 방지 테스트가 아니다.

### 3.8 환경 설정 안내의 분열
README는 conda(`fig-atlas`)와 venv 두 갈래를 제시하고, `SKILL.md`는 `.venv/Scripts/python`을 하드코딩한다. 신규 사용자가 어느 환경을 표준으로 삼아야 할지 모호하다.

### 3.9 명명의 잔재(legacy leak)
example의 `source_stem="outputs/figures/figure1_heatmap"`은 실제로 히트맵이 아니라 3패널(선/산점/막대) 그림이다. 템플릿에서 이런 오해 소지 명칭은 정리되는 게 좋다.

---

## 4. 개선 계획 (우선순위 순)

### P1 — 렌더러를 라이브러리로 승격 ✅ 완료 (2026-07-14)
`fig_atlas/renderers/`(또는 `plot_lib/`) 패키지를 만들어 volcano/heatmap/pca/venn/go_dot을 한 곳에 두고, analysis 스크립트는 `from fig_atlas.renderers import render_volcano`로 조립만 하게 한다.
- **효과**: 중복 800여 줄 제거, 템플릿의 핵심 가치가 실제로 재사용 가능해짐.
- **관련 결함**: 3.3

**구현 내역**
- 신규 패키지 `fig_atlas/renderers/`: `volcano.py`, `heatmap.py`, `pca.py`, `venn.py`, `go_dot.py`, `boxplot.py`, `panels.py`(`panel_label` 헬퍼), `__init__.py`(공개 API).
- 공유 데이터 헬퍼 `load_bundle_params`를 `fig_atlas/params.py`로 추출하고 `fig_atlas` top-level에서 노출. (렌더러 자체는 matplotlib/seaborn 지연 로딩을 위해 top-level에 넣지 않고 서브패키지로만 노출.)
- `analysis/pilot_analysis.py`, `analysis/pilot-test2_analysis.py`, `analysis/pilot-llm-agent-test_analysis.py`에서 인라인 렌더러 정의를 삭제하고 라이브러리 import로 교체. `example_analysis.py`는 공유 렌더러 미사용이라 변경 없음.
- **검증**: `render_volcano/heatmap/pca`가 두 pilot 스크립트에서 바이트 동일함을 확인 후 단일 추출. 4개 프로젝트 파이프라인(analysis→build→verify)을 실제 실행 → pilot-test·pilot-test2·pilot-llm-agent-test 모두 `PASS 4/4`. example(기본 config)의 verify 실패는 P1과 무관한 기존 경로 충돌(3.2, `figures/`에 다수의 `figure_01_*` 폴더) → P3에서 해결 예정.
- **주의**: go_dot의 하드코딩 폰트 크기는 P1에서 순수 추출을 위해 그대로 유지했고, P5에서 정리한다.

### P2 — Snakefile을 config 기반으로 일반화하거나, 안 되면 제거 ✅ 완료 (2026-07-14)
- `configfile` 경로를 `configs/config.yaml`로 수정.
- spec 목록을 `spec_pattern` glob으로 동적 생성.
- 산출물 경로를 config의 `manifests_root`에서 읽도록 수정.
- 유지가 부담이면 차라리 `run_all.py` 하나로 단일화해 문서-현실 괴리를 줄인다.
- **관련 결함**: 3.1

**구현 내역**
- `CONFIG_PATH` 환경변수를 **단일 소스**로 삼아 `configfile: CONFIG_PATH`(기본 `configs/config.yaml`)를 로드하고, 자식 스크립트(`build_atlas.py`/`verify_atlas.py`)는 상속된 동일 env로 같은 config를 본다. → DAG와 스크립트가 절대 어긋나지 않음.
- 산출물 경로(`MANIFEST`, `VERIFICATION`)를 config의 `paths.manifests_root`에서 파생. 하드코딩 `manifests/` 제거.
- 하드코딩 `figure_01_example.py`와 무의미한 `expand(상수, fig=FIGS)` 제거. spec 입력은 `spec_pattern` glob으로 동적 생성.
- 분석 스크립트를 config 키 `project.analysis_script`로 선택(4개 config 모두 추가). 기본값 `analysis/example_analysis.py`.
- 자식 실행을 `python` 대신 `sys.executable`(`params.py`)로 호출 → env 활성화 여부와 무관하게 이식성 확보.
- analysis 완료 마커를 `.done/analysis_<project_name>`로 프로젝트별 분리 → CONFIG_PATH 전환 시 다른 프로젝트 마커 재사용으로 인한 오탐 방지.
- **검증**: 기본 config `--dry-run` 4-job DAG 정상. `CONFIG_PATH=configs/config_pilot-test2.yaml snakemake all` 실제 실행 → 경로가 `outputs/pilot-test2/manifests/...`로 정확히 해석되고 `PASS 4/4`, 4-of-4 steps 완료. `.done/`·`.snakemake/`·`outputs/*`는 모두 gitignore 확인.

### P3 — 경로 전략 단일화 ✅ 완료 (2026-07-14)
- 커밋되는 `figures/`와 git-ignore되는 `outputs/`의 이중 스킴을 하나로 통일.
- `output_root`/`OUTPUT_ROOT`를 실제로 analysis 스크립트가 사용하도록 배선.
- README 구조도를 실제 기본 config 동작과 일치시킨다.
- **관련 결함**: 3.2, 3.4

**채택 방향(사용자 승인)**: 옵션 1 — 발행 아틀라스를 커밋하지 않고 전부 `outputs/<project>/` 아래로 재생성(gitignore). 피규어는 raw+config에서 결정론적으로 만들어지는 빌드 산출물이므로 바이너리 커밋을 지양.

**구현 내역**
- `config.py`: `output_root` 기본값을 `outputs`로 정상화(`${OUTPUT_ROOT}` 미설정 플레이스홀더 폴백 처리). `figures_root`/`manifests_root`/`supplementary_root`를 명시값이 없으면 `outputs/<project.name>/...`로 파생. 경로 정규화 헬퍼 `_resolve`(절대→그대로, 상대→project_root 기준)와 `project_name`/`_project_output_dir` 추가.
- `spec.py`/`publish.py`: `source_stem`을 **project_root가 아니라 output_root 기준**으로 재정의·해석(`{output_root}/{source_stem}`). `OUTPUT_ROOT`가 저장소 밖이어도 안전하도록 `relative_to` 실패 시 절대경로로 폴백하는 `_display_path` 도입.
- `verify.py`, `scripts/build_atlas.py`, `scripts/verify_atlas.py`: 동일한 `relative_to` 방어 처리(외부 OUTPUT_ROOT에서 크래시하던 print문 수정).
- 4개 spec: `source_stem`에서 `outputs/` 접두어 제거. 4개 analysis 스크립트: 하드코딩 `project_root/"outputs"` → `config.output_root`.
- 3개 pilot config: 기본 네임스페이스와 동일해진 `figures_root`/`manifests_root`/`supplementary_root` 명시값 삭제(중복 제거). 기본 config: `spec_pattern`을 전체(`figure_*.py`)에서 예제 전용(`figure_01_example.py`)으로 좁혀 다중 spec 발행 충돌 제거.
- `README.md`: 구조도·Quickstart·"What is committed vs. rebuilt" 섹션을 실제 동작(전부 `outputs/<project>/`, gitignore; 루트 `figures/`·`manifests/`는 참고용 정적 샘플)과 일치하도록 갱신. `prepare_external_pipeline.py` 기본 stem도 갱신.
- **검증**: 4개 프로젝트 직접 실행 `PASS 4/4`(기본 example 포함 — 기존 폴더 충돌 3.2 해소). `snakemake all` 기본·pilot-test2 모두 100%/`PASS 4/4`. 외부 `OUTPUT_ROOT`(스크래치패드)로 pilot-test2 실행 시 analysis→build→verify 전 단계가 외부 경로에 정확히 기록되고 `PASS 4/4`. 커밋된 `figures/`·`manifests/` 샘플은 무변경(clean) 확인.

### P4 — 최소 테스트 + CI 추가 ✅ 완료 (2026-07-14)
- `publish()`가 파일이 없을 때 `FileNotFoundError`를 던지는지.
- `verify_atlas()`가 누락을 FAIL로 잡는지.
- config 계층 병합 순서가 맞는지.
- 위 pytest 3~4개 + GitHub Actions로 `verify --skip-heavy`를 돌려 회귀 방지.
- **관련 결함**: 3.7

**구현 내역**
- `tests/` 신설(총 16개, 모두 통과):
  - `test_config.py` — output_root 기본값·`${OUTPUT_ROOT}` 미설정 폴백·env 오버라이드·프로젝트 네임스페이스·명시값 우선·`_resolve` 절대/상대(6).
  - `test_publish.py` — 소스 없을 때 `FileNotFoundError`·전 포맷 복사 + README notes 작성·외부 OUTPUT_ROOT에서 절대경로 폴백(3).
  - `test_verify.py` — 발행 후 전부 PASS·미발행 시 folder FAIL·README notes 누락 FAIL·`write_report` 실패 카운트(4).
  - `test_params.py` — `load_bundle_params` 정상/누락·병합 우선순위(defaults<bundle<global<config) 계약(3).
  - `conftest.py` — tmp_path에 임시 프로젝트(config+가짜 소스) 생성 팩스처, RAW_ROOT/OUTPUT_ROOT 격리.
- `pytest.ini`(testpaths=tests). `requirements.txt`·`environment.yml`에 `pytest>=7.0` 추가.
- `.github/workflows/ci.yml` — push/PR 시 Python 3.12에서 의존성 설치 → `pytest` → 예제 파이프라인 스모크(analysis→build→verify, raw 데이터 불필요).
- **검증**: 로컬 `pytest` 16 passed. CI 스모크 시퀀스를 클린 env로 재현 → 예제 `PASS 4/4`. 캐시 아티팩트(`__pycache__`, `.pytest_cache`)는 gitignore 확인.

### P5 — 하드코딩 스타일 값 제거 ✅ 완료 (2026-07-14)
`render_go_dot` 등에 남은 `fontsize=11/13`을 `params.get('axes_label_size')`, `params.get('title_size')`로 교체해 CLAUDE.md 원칙과 일치시킨다.
- **관련 결함**: 3.6

**구현 내역**
- `fig_atlas/renderers/go_dot.py`: 함수 초입에서 `a_sz=axes_label_size(11)`, `title_sz=title_size(13)`, `tick_sz=tick_label_size(8)`를 읽어 xlabel/ylabel(→a_sz), title(→title_sz), colorbar 라벨(→tick_sz+2), size 범례(→tick_sz)에 적용.
- y축 틱 폰트: 기존 `9/8/7/6`(개수 구간별) 하드코딩을 `max(4, tick_sz+1-step)`로 대체. tick_sz 기본 8이면 9/8/7/6과 **동일**해 기본 동작 보존, 동시에 config `tick_label_size`에 반응.
- 남은 `fontsize=14`는 "데이터 없음" placeholder 메시지(스타일 대상 아님)라 의도적으로 유지.
- **검증**: pilot-test2(유일한 go_dot 사용처) 실행 `PASS 4/4`. 4개 프로젝트 전체 회귀 없음 + pytest 16 passed.

### P6 — 경로 정규화 함수 도입 ✅ 완료 (2026-07-14)
`raw_root`/`output_root`를 반환할 때 절대경로면 그대로, 상대경로면 `project_root` 기준으로 resolve하는 단일 헬퍼를 두어 이중 join 취약성을 제거한다.
- **관련 결함**: 3.5

**구현 내역**
- P3에서 도입한 `ProjectConfig._resolve`(절대→그대로, 상대→project_root 기준, `expandvars` 포함)를 `raw_root`·`output_root`에 일괄 적용. `RAW_ROOT`/`OUTPUT_ROOT` env 값도 `_resolve`를 거쳐 상대/절대 처리가 균일해짐.
- `raw_root`가 이제 절대경로를 반환하므로 3개 analysis 스크립트의 `RAW = CONFIG.project_root / CONFIG.raw_root`(이중 join)를 `RAW = CONFIG.raw_root`로 단순화. 절대 `RAW_ROOT` env가 우연히 동작하던 것을 명시적으로 안전하게 만듦.
- 테스트 2개 추가(`test_config.py`): 상대 raw_root의 project_root 앵커링, 절대 `RAW_ROOT` env 오버라이드.
- **검증**: raw 데이터 사용 3개 프로젝트 `PASS 4/4`, 절대 `RAW_ROOT` 오버라이드로 pilot-test analysis 정상 저장, pytest 18 passed.

### P7 — 환경 설정 표준 하나 지정 ✅ 완료 (2026-07-14)
conda를 1순위로 하되 `SKILL.md`의 `.venv` 하드코딩을 환경변수/자동탐지로 바꾸거나 최소한 README와 일치시킨다.
- **관련 결함**: 3.8, 3.9

**구현 내역**
- `.agents/skills/ingest_plot/SKILL.md` Phase 7: `.venv/Scripts/python` 하드코딩 제거. "먼저 환경 활성화(`conda activate fig-atlas` 권장, 또는 venv)" 후 `python`으로 실행하도록 변경하고, `snakemake all --cores 1` 원커맨드 대안 추가.
- 명명 잔재(3.9): 실제 히트맵이 아닌 예제의 `figure1_heatmap` → `figure1_example`로 일괄 변경. 대상: `analysis/example_analysis.py`, `figure_specs/figure_01_example.py`, `scripts/prepare_external_pipeline.py`(기본값), `docs/GUIDE.md`, `manifests/external_pipeline_requirements.md`, `external_pipeline_contract_template.yaml`, 재생성한 `external_pipeline_contract.yaml`. (README의 heatmap 예제는 실제 히트맵이라 `gene_expression_heatmap`으로 정리.)
- 커밋된 정적 샘플 `figures/figure_01_example_subpanels/README.md`의 옛 stem 문자열은 스냅샷이라 그대로 둠.
- **검증**: 이름 변경 후 예제 파이프라인 `PASS 4/4`. 전체 회귀(4개 프로젝트 직접 실행 + snakemake 기본·pilot-test2 100% + pytest 18)에서 이상 없음.

---

## 완료 요약 (2026-07-14)

P1–P7 전부 완료. 최종 상태:
- **테스트**: pytest 18개 통과 + GitHub Actions CI(테스트 + 예제 스모크).
- **파이프라인**: 4개 프로젝트 모두 직접 실행/snakemake에서 `PASS 4/4`. 외부 `RAW_ROOT`/`OUTPUT_ROOT` 오버라이드 검증.
- **구조**: 렌더러가 `fig_atlas/renderers/` 라이브러리로 단일화(중복 제거), 경로는 `outputs/<project>/` 단일 스킴(gitignore), Snakefile은 `CONFIG_PATH` 단일 소스로 config와 동기화.
- 남은 정적 샘플(`figures/`, 일부 커밋 README)은 참고용 스냅샷으로만 유지.

---

## 5. 총평

개념 설계(관심사 분리, 선언적 SPEC, 설정 계층화)는 우수하지만, 구현이 개념을 완전히 따라가지 못한 상태다. 특히 **렌더러 중복(3.3)**과 **동작하지 않는 Snakefile(3.1)**이 "재사용 템플릿"이라는 정체성을 가장 크게 훼손하고 있다. P1·P2·P3을 먼저 해결하면 완성도가 크게 올라갈 것이다.
