# How-to: 새 분야 팩 만들기

fig-atlas의 코어(`fig_atlas`)는 분야와 무관합니다. 전기생리, 이미징, 임상처럼 특정 분야의 지식은 **분야 팩**이라는 별도 패키지에 담고, 코어는 진입점(entry point)으로만 팩을 찾습니다. 오믹스 팩 `fig_atlas_omics`가 첫 번째 예입니다.

이 문서는 전기생리 팩 `fig_atlas_ephys`를 예로, 팩을 처음부터 만드는 과정을 보여 줍니다. 아래 코드 블록 중 `<!-- file: ... -->` 표시가 붙은 것은 `tests/test_example_pack.py`가 그대로 꺼내 실제 팩을 만들고 인식되는지 확인합니다. 그래서 이 문서의 예제는 항상 동작합니다.

## 1. 무엇을 팩에 넣나

| 팩에 넣는 것 | 예 |
|---|---|
| 데이터 읽기·반입 어댑터 | ABF/NWB 파일 읽기, 장비 내보내기 형식 변환 |
| 번들 계약 | 어떤 열·파일·메타데이터가 있어야 하는가 |
| 레시피 | 코어 렌더러(모양) + 이 분야의 열 역할·용어·기본값 |
| 분석 도우미 | 스파이크 검출, 입력 저항 계산 |
| 이 분야에서만 의미 있는 모양 | (드묾) 서열 로고, 유전체 트랙 |

**렌더러는 모양 단위입니다.** 선, 막대, 산점도, 히트맵은 처음 쓰는 데이터가 전기생리여도 코어에 둡니다(AGENTS.md §3). 대부분의 분야 그림은 코어 모양에 레시피를 얹는 것으로 충분합니다. 쓸 수 있는 모양은 `fa renderers`로 봅니다.

## 2. 패키지 구조

```
fig_atlas_ephys/
  __init__.py
  contracts.py        # 번들 계약 + plot_type -> 렌더러 매핑
  recipes.py          # 레시피
  cli.py              # (선택) `fa ephys ...` 명령
```

팩은 코어를 import해도 되지만, 코어는 팩을 import하지 않습니다.

<!-- file: fig_atlas_ephys/__init__.py -->
```python
"""Electrophysiology pack for fig-atlas (example from docs/howto/new_domain_pack.md)."""
```

## 3. 계약

번들의 `metadata.yaml`에 적힌 `plot_type`으로 계약이 정해집니다. `required`는 그리는 데 꼭 필요한 열(없으면 오류), `expected`는 문서가 요구하는 나머지 열(없으면 경고)입니다. `INGEST`는 `plot_type`을 그릴 함수(또는 레시피 이름)로 잇습니다.

<!-- file: fig_atlas_ephys/contracts.py -->
```python
from fig_atlas.contracts import Contract

CONTRACTS = [
    Contract("ephys.iv", ("iv_curve",),
             required=("voltage_mV", "current_pA"),
             expected=("cell",),
             doc="docs/howto/new_domain_pack.md",
             title="Current-voltage steps: one row per (cell, voltage step)"),
]

# plot_type -> "module:function" that draws it
INGEST = {"iv_curve": "fig_atlas_ephys.recipes:render_iv_curve"}
```

## 4. 레시피

레시피는 코어 렌더러 하나와, 이 분야에서의 열 역할·기본값을 묶은 데이터입니다. 아래는 I-V 곡선을 코어의 `line_band`(선 + 오차 띠)로 그리는 레시피입니다. `surface`는 프로젝트 config에서 쓸 파라미터 이름, `aliases`는 그 이름과 범용 이름의 대응입니다.

<!-- file: fig_atlas_ephys/recipes.py -->
```python
from fig_atlas.recipes import recipe, render

IV_CURVE = recipe(
    "iv_curve", "fig_atlas.renderers.line_band:render_line_band",
    defaults={"x_col": "voltage_mV", "y_col": "current_pA", "error": "sem",
              "labels_xlabel": "Membrane potential (mV)", "labels_ylabel": "Current (pA)",
              "zero_line": True, "show_points": True},
    surface=("error", "show_points", "line_width", "labels_title"),
    aliases={},
)

RECIPES = [IV_CURVE]


def render_iv_curve(ax, df, params=None):
    return render(IV_CURVE, ax, df, params=params)
```

## 5. (선택) 명령

팩은 `fa` 아래에 자기 명령을 붙일 수 있습니다. `register`는 하위 명령을 만들고 `{이름: 처리 함수}`를 돌려줍니다. 코어 명령과 이름이 같으면 코어가 우선합니다.

<!-- file: fig_atlas_ephys/cli.py -->
```python
import json


def register(subparsers):
    p = subparsers.add_parser("ephys", help="electrophysiology pack: what it provides")
    p.add_argument("action", choices=("list",))
    return {"ephys": run}


def run(args, root):
    from .contracts import CONTRACTS
    from .recipes import RECIPES
    print(json.dumps({"contracts": [c.name for c in CONTRACTS], "recipes": [r.name for r in RECIPES]}))
    return 0
```

## 6. 진입점 등록

팩의 `pyproject.toml`에 진입점을 적습니다. 그룹은 다섯 가지이고, 필요한 것만 씁니다.

<!-- file: entry_points.toml -->
```toml
[project.entry-points."fig_atlas.contracts"]
ephys = "fig_atlas_ephys.contracts:CONTRACTS"

[project.entry-points."fig_atlas.ingest"]
ephys = "fig_atlas_ephys.contracts:INGEST"

[project.entry-points."fig_atlas.recipes"]
ephys = "fig_atlas_ephys.recipes:RECIPES"

[project.entry-points."fig_atlas.commands"]
ephys = "fig_atlas_ephys.cli:register"
```

| 그룹 | 값 | 쓰임 |
|---|---|---|
| `fig_atlas.renderers` | 렌더러 패키지 (`"pack.renderers"`) | 이 분야 고유 모양이 있을 때만 |
| `fig_atlas.contracts` | `Contract` 목록 | `fa bundle check` |
| `fig_atlas.ingest` | `{plot_type: "module:function"}` | `fa bundle check`가 그릴 렌더러를 보여 줌 |
| `fig_atlas.recipes` | `Recipe` 목록 | `fig_atlas.render("이름", ...)`, `fa renderers` |
| `fig_atlas.commands` | `register(subparsers)` 함수 | `fa <팩 명령>` |

그다음 설치합니다. 진입점은 설치할 때 등록되므로, 바꿀 때마다 다시 실행합니다.

```bash
pip install -e .
```

## 7. 확인

```bash
fa renderers                    # iv_curve가 recipe로 보여야 합니다
fa bundle contracts             # ephys.iv가 보여야 합니다
fa bundle check <bundle-folder>  # plot_type: iv_curve 번들을 계약으로 검사
fa ephys list                   # 팩의 명령
```

분석 스크립트에서는 이름으로 그립니다. 레시피가 어느 팩에 있는지 몰라도 됩니다.

```python
import fig_atlas
fig_atlas.render("iv_curve", ax, df, params={"error": "sem"})
```

팩에 렌더러를 넣었다면 각 렌더러에 `SCHEMA`가 있어야 하고(`tests/test_renderer_schemas.py`가 모든 등록 패키지를 검사합니다), 하드코딩된 스타일 값이 없어야 합니다(`fa lint --hardcoded`).

## 체크리스트

- [ ] 모양은 코어 렌더러를 쓰고, 분야 지식은 레시피·계약·도우미로 담았다
- [ ] 계약마다 사람이 읽는 문서(`doc`)가 있다
- [ ] 레시피의 `defaults`와 `aliases`는 코어 렌더러의 파라미터 이름만 쓴다
- [ ] `pyproject.toml`에 진입점을 적고 `pip install -e .`를 다시 실행했다
- [ ] `fa renderers`, `fa bundle contracts`에 팩의 항목이 보인다
