# How-to: 저널 규격으로 바꾸기

그림은 처음부터 인쇄될 크기로 그립니다. 그래서 투고할 저널이 바뀌면 그림을 다시 그리는 것이 아니라 **저널 프리셋을 바꾸고 검사를 다시 돌립니다.** 프리셋은 그 저널의 그림 폭, 최대 높이, 글꼴, 글자 크기, 선 굵기, 패널 태그 표기와, preflight가 그 기준으로 검사할 값을 담은 YAML 파일입니다.

## 1. 들어 있는 프리셋

| 프리셋 | 폭 | 글꼴 | 글자 | 패널 태그 | 출처 |
|---|---|---|---|---|---|
| `journal_generic` | 180 mm | Arial | 6–8 pt | a, b, c | 대부분의 생명과학 저널이 받아 주는 공통 범위 (저널을 정하기 전 초안용) |
| `journal_nature` | 183 mm (1단 89, 1.5단 120·136) | Arial, 없으면 Helvetica | 5–7 pt | a, b, c · 8 pt 굵게 | Nature 최종 원고 안내 |
| `journal_science` | 184 mm (1단 89, 1.5단 127) | Myriad, 없으면 Arial | 최소 6 pt | A, B, C · 9 pt 굵게 | Science 수정 원고 안내 |

각 파일 머리말에 안내문 주소와 확인한 날짜가 있고, 안내문에 없는 값에는 "not stated"라고 적혀 있습니다. 저널 안내는 바뀌므로 투고 전에 머리말의 날짜와 주소를 확인하세요.

## 2. 바꾸기

config의 `project.style`에서 페이지 프리셋을 저널 프리셋으로 바꿉니다. 이 한 줄이 전부입니다.

```yaml
project:
  style: ["default", "print", "journal_nature"]   # 전: page_a4_portrait_narrow
```

그리고 검사와 함께 빌드합니다.

```bash
fa build <project> --preflight
```

config에 직접 적은 값은 프리셋보다 우선합니다(병합 순서: 번들 < 프리셋 < config). 그래서 config에 글자 크기를 직접 정해 둔 패널은 프리셋을 바꿔도 그대로이고, preflight가 그 저널 기준에 맞지 않는 곳을 알려 줍니다.

## 3. preflight가 짚는 것

| 검사 | 저널 프리셋의 키 |
|---|---|
| 너무 작은 글자, 너무 가는 선 | `print_check.min_font_pt`, `min_line_pt` |
| 너무 큰 글자 (패널 태그 제외) | `preflight.max_font_pt` |
| 저널 컬럼 폭이 아닌 그림 | `preflight.allowed_widths_mm`, `width_tol_mm` |
| 페이지보다 긴 그림 | `page.content_height_mm` |
| 태그 대소문자·크기 | `preflight.panel_tag_case`, `panel_tag_size_pt` |
| PDF에 허용되지 않은 글꼴, 설치되지 않은 글꼴 | `preflight.allowed_fonts` |

고칠 때는 지적된 값을 config에서 바꿉니다. 키마다 단위와 조정 방향이 주석으로 적혀 있고, 값이 어디서 왔는지는 `fa param explain <project> <키>`로 봅니다.

## 4. 알아 둘 것

- **글꼴.** 프리셋은 글꼴 하나가 아니라 순서 있는 목록을 씁니다(`rcparams: font.sans-serif`). 첫 글꼴이 설치되어 있지 않으면 다음 글꼴을 씁니다. Myriad처럼 상용 글꼴을 쓰려면 설치하면 됩니다.
- **수식 글자.** matplotlib은 지수(10²)나 아래 첨자(H₂O₂)를 기본으로 DejaVu 글꼴로 그립니다. 저널 프리셋은 `rcparams`의 `mathtext.*`로 이것도 같은 글꼴로 맞춥니다. `rcparams:` 블록은 config를 불러올 때 matplotlib에 적용되므로, config에 직접 써도 됩니다.
- **태그를 직접 그리는 스크립트.** `place_panel_tags`를 쓰는 그림은 태그가 프리셋을 따릅니다. 태그 글자를 스크립트가 직접 쓰는 경우에는 `figures.panel_tag_case`("lower" 또는 "upper")를 읽어 대소문자를 정하고, 태그에 `gid=PANEL_TAG_GID`를 붙여 preflight가 태그로 알아보게 합니다.
- **검사하지 않는 규칙.** 예를 들어 Science는 빨강과 초록을 함께 쓰지 말라고 합니다. preflight의 색 검사는 색각이상 시뮬레이션에서 두 색이 구별되는지를 재므로, 구별되는 빨강·초록 쌍은 통과합니다. 안내문의 글로 된 규칙은 직접 확인하세요.
