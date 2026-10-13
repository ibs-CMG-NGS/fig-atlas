# Tutorial: 스케치와 데이터로 그림 만들기 (Case C)

그림이 들어오는 길은 내가 가진 것에 따라 셋입니다([가이드 5장](../guide/05-entry-paths.md)). 이 문서는 **코드는 없고 데이터와 원하는 그림의 모양(스케치, 캡처, 말 설명)만 있는** Case C를 한 예제로 보여 줍니다.

Case C는 AI 도우미가 그림을 **해석**해야 하므로, 같은 요청에도 해석이 조금씩 다를 수 있습니다. 그래서 이 문서는 따라 하는 명령보다 **실제로 있었던 한 번의 진행**(2026-10-13, Claude Code와 연구자)을 기록합니다. 해석안, 연구자에게 물은 것, 받은 답, 결과를 그대로 적었습니다. 번들이 만들어진 뒤의 단계는 명령이고, `tests/test_tutorials.py`가 CI에서 그대로 실행합니다.

예제 파일은 [`examples/case_c/`](../../examples/case_c/)에 있습니다. 데이터와 스케치는 시뮬레이션으로 만든 것입니다(`examples/case_c/make_example.py`). 더 좋은 실제 요청이 생기면 교체합니다.

## 1. 요청: 데이터와 스케치

데이터(`examples/case_c/request/data.csv`)는 유전자 12개의 log2 fold change, 95 % 신뢰구간, 보정 P입니다.

```text
gene,log2fc,ci_low,ci_high,padj
Hmox1,2.3,1.784,2.817,3.99e-16
Nqo1,1.578,1.272,1.884,2.82e-21
Gclm,1.064,0.554,1.573,0.000596
...
```

그리고 원하는 그림을 손으로 그린 스케치입니다. 메모가 붙어 있습니다.

<!-- img/: copied or drawn by `fa reference` from this page's own files; do not edit by hand -->
![스케치: 유전자마다 점과 가로 신뢰구간, 0에 점선, "biggest up on top", "red = up, blue = down (only if padj < 0.05)", "same style as our other panels!" 메모](img/case_c_sketch.png)

AI 도우미에게는 이렇게 요청합니다.

> "`examples/case_c/request/`의 data.csv와 sketch.png로 이 그림을 만들어 줘(Case C). 프로젝트는 `antioxidant-effects`."

## 2. 해석안과 확인 (그리기 전)

Case C의 규칙상 AI는 **코드를 만들기 전에** 해석안을 보여 주고 승인을 받습니다([`ingest_plot` 스킬](https://github.com/ibs-cmg-ngs/fig-atlas/blob/main/.agents/skills/ingest_plot/SKILL.md), C-2). 이번에 제시된 해석안은 이랬습니다.

**스케치와 데이터로 정한 것**

1. **그림 종류:** 유전자마다 점 + 95 % 신뢰구간. 이미 있는 렌더러 `effect_dots`가 그리는 모양이라 새로 만들지 않고 재사용합니다.
2. **열 대응:** `gene` → 행 이름, `log2fc` → 점, `ci_low`/`ci_high` → 구간 양 끝.
3. **순서:** `log2fc`가 큰 것이 위("biggest up on top").
4. **색 규칙:** `padj < 0.05`이고 증가면 up, `padj < 0.05`이고 감소면 down, 나머지는 유의하지 않음. 임계값 0.05는 스케치에 적혀 있습니다.
5. **부가 요소:** x = 0 점선, 제목, x축 제목.
6. **"same style as our other panels":** 프로젝트의 인쇄 프리셋(글자 크기, 선 굵기, 최종 크기 렌더링)으로 해석.

**스케치만으로 정할 수 없어 물은 것과 답**

| 질문 | 선택지 | 답 |
|---|---|---|
| A. 색 | 스케치의 빨강·파랑 그대로, 또는 색각이상에 안전한 팔레트(추천: 빨강·파랑 쌍은 preflight 색 경고 대상) | 추천대로: 안전한 팔레트 |
| B. 색 규칙을 어디서 적용하나 | (1) 렌더러에 "임계값으로 색 나누기" 옵션 추가(추천: config만으로 조정, 다른 프로젝트도 재사용), (2) 분석 스크립트가 분류 열을 계산 | 추천대로: (1) |
| C. 범례 | (1) 작은 범례, (2) 범례 없이 그림 설명에서 설명 | 추천을 표시하지 않았던 항목. AI가 (1)을 고르고 이유(그림이 혼자 읽히도록)를 밝힘 |
| D. 크기 | 단일 칼럼(폭 85 mm, 높이 약 70 mm) | 추천대로 |

연구자의 답은 한 줄이었습니다. "추천대로 진행하자." C처럼 추천이 없던 항목을 AI가 정했다면, 그 사실과 이유를 보고에 밝히고 검토 때 바꿀 수 있게 합니다.

## 3. 해석 → 번들, 그리고 렌더러에 더한 것

B의 답에 따라 `effect_dots`에 옵션 세 개가 더해졌습니다. 기존 그림은 그대로이고, 다음 프로젝트도 씁니다.

- `item_sort: estimate_desc`: 값이 큰 행을 위로
- `color_by: threshold`와 `sig_col`, `sig_threshold`, `up_color`, `down_color`, `ns_color`, `class_labels`: 방향과 유의성으로 색 나누기
- `zero_line_style`: 0 선의 모양(점선 등)

번들([`examples/case_c/effects_bundle/`](../../examples/case_c/effects_bundle/))에는 요청의 데이터를 **그대로** 복사한 `inputs/data.csv`, 스케치 사본 `metadata/reference.png`, 그리고 확정된 값이 들어갑니다. 값마다 스케치에서 읽었는지 연구자의 답인지 주석이 붙고, `param_source: inferred_from_mockup`이 코드에서 뽑은 값이 아님을 밝힙니다.

<!-- file: examples/case_c/effects_bundle/metadata/metadata.yaml -->
```yaml
# Case C example (docs/tutorials/case_c_from_sketch.md): the bundle made from
# request/data.csv and request/sketch.png -- no code. inputs/data.csv is the
# request's table, copied unchanged; metadata/reference.png is the sketch.
# Every plot_params value below was read from the sketch and the data, or is
# an answer the researcher gave at the confirmation step (2026-10-13).
# Synthetic data.
plot_type: effect_dots
param_source: inferred_from_mockup    # not extracted from code: check against reference.png
plot_params:
  # what is plotted (from the data's columns)
  item_col: gene                      # one row per gene
  estimate_col: log2fc                # the dot
  low_col: ci_low                     # the interval, 95 % CI ("log2 fold change (95% CI)")
  high_col: ci_high
  item_sort: estimate_desc            # sketch: "biggest up on top"
  # colour by direction and significance (sketch note; researcher: a renderer option)
  color_by: threshold
  sig_col: padj                       # sketch: "(only if padj < 0.05)"
  sig_threshold: 0.05
  up_color: "#D55E00"                 # researcher: a colour-blind-safe palette, not the sketch's red/blue
  down_color: "#0072B2"
  ns_color: "#9CA3AF"
  class_labels: {up: "Up", down: "Down", ns: "n.s."}
  # marks
  zero_line: true                     # sketch: dashed line at 0
  zero_line_style: "--"
  # text
  title: "H2O2 response of antioxidant genes"
  xlabel: "log2 fold change (95% CI)"
  legend: true                        # researcher: a small legend (the sketch had a note)
```

## 4. 번들 → 그림 (직접 하기)

여기부터는 직접 따라 할 수 있습니다. 저장소 루트에서 프로젝트를 만들고 번들을 붙입니다.

<!-- run -->
```bash
fa new project antioxidant-effects
mkdir -p raw_data/antioxidant-effects
cp -r examples/case_c/effects_bundle raw_data/antioxidant-effects/
fa bundle check raw_data/antioxidant-effects/effects_bundle
fa ingest bundle raw_data/antioxidant-effects/effects_bundle --project antioxidant-effects
```

크기는 D의 답대로 단일 칼럼으로 합니다. `configs/config_antioxidant-effects.yaml`의 `figures` 블록에서 두 줄을 바꿉니다.

<!-- replace: configs/config_antioxidant-effects.yaml | height_mm: 80 -->
```yaml
  height_mm: 70                       # Figure height in mm (width = the page content width); raise if panels feel cramped
```

<!-- replace: configs/config_antioxidant-effects.yaml | width_mm: null -->
```yaml
  width_mm: 85                        # Figure width in mm; null = the page content width, 85 = one journal column
```

<!-- run -->
```bash
fa build antioxidant-effects --preflight
```

`[ok] antioxidant-effects: 0 error(s), 0 warning(s)`와 `PASS: 5/5 checks passed`가 나옵니다.

## 5. 검토 (그린 뒤)

![결과: 유전자 12개가 log2 fold change 순으로, 유의한 증가는 주황, 감소는 파랑, 나머지는 회색. 0에 점선, 오른쪽 아래에 범례](img/case_c_result.png)

AI는 결과와 함께 스케치와 무엇이 같고 무엇이 다른지 보고했습니다.

- **스케치와 같음:** 점 + 95 % 신뢰구간, 큰 증가가 위, 0 점선, 제목과 축 제목, 색 규칙(증가 7, 감소 2, 유의하지 않음 3).
- **답에 따라 바뀜:** 빨강·파랑 → 안전한 팔레트, 손글씨 메모 → 범례, 손그림 글꼴 → 인쇄 글꼴과 크기.
- **확인을 부탁한 것:** 단일 패널인데 왼쪽 위에 패널 태그 `a`가 붙는 점. 다른 패널과 합칠 때를 위한 것입니다.

**판정은 연구자가 합니다.** 이번에는 "OK"로 끝났습니다. 고칠 점이 있으면 "점을 조금 작게", "범례를 오른쪽 위로"처럼 말하면 AI가 config의 값만 바꿔 다시 빌드합니다. 코드는 바뀌지 않습니다.

## 6. 남는 것

- **번들:** 원본 데이터(그대로), 스케치(`reference.png`), 해석의 출처가 적힌 값.
- **config:** `fa ingest bundle`이 쓴, 모든 파라미터가 설명과 함께 적힌 블록. 이후 조정은 여기서 합니다.
- **렌더러:** `effect_dots`의 새 옵션. 다음에 같은 모양을 요청하면 해석만 하면 됩니다.
- **출처 기록:** 그림이 어떤 데이터·코드·설정으로 만들어졌는지(`figure_01.provenance.json`).

모양이 기존 렌더러 어느 것과도 맞지 않으면 AI가 렌더러를 새로 만듭니다(`fa new renderer`). 그때도 해석안 확인과 결과 검토는 같습니다.
