# 하우투: 요약 표 그리기

논문이 보여주는 것이 그림만은 아닙니다. 군별 평균 표, 제작한 construct 표, 시퀀싱 런 표 — 이런 것들은 그림 옆 페이지에 놓이는데, 지금까지 fig-atlas가 유일하게 그리지 못하던 것이 바로 이것이었습니다. 스프레드시트에서 캡처한 그림을, 그 스프레드시트가 쓰던 글꼴 그대로 붙여 넣어 왔습니다.

`table` 렌더러는 이 표를 인쇄 크기로, 출판 관례대로, 그림과 똑같은 번들과 똑같은 설정 파일에서 그립니다.

## 무엇보다 먼저: 이것은 표를 투고하는 방법이 아닙니다

**저널은 표를 편집 가능한 텍스트로 받습니다** — Word, Excel, 또는 출판사 자체 양식. 그림으로 만든 표는 그림입니다. 교정이 되지 않고, 저널 자체 스타일로 다시 조판되지 않으며, 화면 낭독기가 읽지 못합니다. 그림으로 투고하면 대개 되돌아옵니다.

그러니 이 렌더러는 이런 데 쓰십시오.

- **컴펜디움 쪽** — 표가 관련된 그림들 옆에 놓이는 자리,
- **발표와 포스터** — 표의 글꼴과 크기가 그림과 맞아야 하는 자리,
- **점검** — 인쇄 크기로 그려 보면 그 표가 한 쪽에 들어가기는 하는지 바로 보입니다.

그리고 투고에는 CSV 자체를 내십시오 — `inputs/data.csv`, 또는 생성 코드가 쓰는 `outputs/supplementary/*.csv`. 그러면 그린 표와 낸 표가 한 파일에서 나오므로 서로 어긋날 수 없습니다.

## 1. 이미 가진 표에서, 코드 없이

어떤 CSV든 표 번들입니다. 필수 열이 없습니다 — 어떤 표든 인쇄할 수 있기 때문입니다.

```bash
cp -r <fig-atlas>/examples/gallery/table raw_data/<project>/group_summary
# raw_data/<project>/group_summary/inputs/data.csv 를 내 표로 바꿉니다
fa bundle check raw_data/<project>/group_summary
fa ingest bundle raw_data/<project>/group_summary --project <project>
fa build <project> --preflight
```

`fa ingest bundle`이 `plots.<이름>` 블록 전체를 프로젝트 설정에 써 줍니다 — 모든 파라미터를 단위와 "무엇이 바뀌는지" 주석과 함께. 그다음부터는 다른 패널과 똑같이 설정 파일에서 표를 조정합니다. `fa bundle check`는 `columns`에 적었는데 데이터에 없는 열을 오류로 보고하고, 어떤 열도 가리키지 않는 열별 키를 경고합니다(`column_format`의 오타는 그러지 않으면 보이지 않습니다 — 그 숫자만 서식 없이 찍힐 뿐입니다).

## 2. 표답게 보이게 하는 것은 열별 처리입니다

전문적인 표와 붙여 넣은 표를 가르는 것은 배치가 아닙니다. **정렬과 숫자 서식입니다.** 이것이 없으면 `41` 옆에 `0.4871234`가 찍히고, 독자는 두 행을 한눈에 비교하지 못합니다.

```yaml
plots:
  group_summary:
    renderer: "table"
    bundle: "raw_data/<project>/group_summary"
    columns: ["group", "n", "mean_latency_s", "sd_latency_s", "p_vs_vehicle"]
    column_labels:
      mean_latency_s: "Latency (s), mean"
      p_vs_vehicle: "P vs vehicle"
    column_format:               # 숫자 열마다 서식 하나
      mean_latency_s: ".1f"
      sd_latency_s: ".1f"
      p_vs_vehicle: ".3g"        # .3f로는 1e-07이 0.000으로 찍힙니다
    column_align:                # 기본값: 숫자는 오른쪽, 글자는 왼쪽
      group: left
    column_width:                # 표 너비의 [0-1]; 나머지는 측정합니다
      group: 0.34
    na_text: "--"                # 빈 칸이 무엇으로 찍히는지
    title: "Latency to fall, by treatment group"
    footnotes:
      - "Welch's t test against vehicle, each dose separately."
```

| 이럴 때 지정합니다 | 키 |
|---|---|
| 실수 열이 전체 자릿수로 찍힐 때 | `column_format` |
| 머리글이 원래 열 이름 그대로일 때(`mean_latency_s`) | `column_labels` |
| 글자 열이 숫자 열을 좁게 밀어낼 때 | `column_width` |
| 빈 칸이 값처럼 읽힐 때 | `na_text` |
| 열들이 한 덩어리로 읽힐 때 | `col_gap`(올립니다) |
| 머리글이 세 줄로 접힐 때 | `header_size`(내립니다) |

나머지 — 선, 글꼴, 간격 — 는 스타일 프리셋에서 오므로 표마다 지정하지 않습니다.

## 3. 생김새는 스타일 프리셋에서 옵니다

`table_classic`이 출판 관례입니다. 가로선 세 개(머리글 위, 머리글 아래, 마지막 행 아래), 세로선 없음, 칸 채움 없음. fig-atlas에 들어 있고 렌더러의 기본값이므로, 아무것도 지정하지 않은 프로젝트도 이미 그렇게 그립니다.

인쇄가 아니라 화면에서 읽을 표라면 `row_stripe: true`가 한 줄 건너 음영을 넣습니다. 논문에는 쓰지 마십시오.

```yaml
project:
  style: ["default", "print", "table_classic"]
```

## 4. 컴펜디움의 표 페이지

스토리라인의 `tables:` 항목은 그림 페이지 뒤에 표 한 개당 한 쪽씩, 이 렌더러로 그려집니다(`fa storyline compile`). 각 항목은 CSV를 지정하고, `render:` 블록을 가질 수 있습니다 — 렌더러 파라미터에, 표가 아니라 페이지에 속하는 키 몇 개가 더해집니다.

```yaml
tables:
  - slot: "Main Table 1"
    file: "outputs/supplementary/main_table_1.csv"
    generator: "scripts/make_main_table_1.py"
    description: "The constructs, their coordinates and what each one measures"
    render:
      columns: ["line", "chromosome", "position", "copies", "note"]
      column_labels: {copies: "Copies"}
      sort_by: "position"        # 긴 표가 어느 행부터 보여줄지
      sort_ascending: true
      orientation: auto          # auto | portrait | landscape
      transpose: false           # 첫 열이 머리글이 됩니다(짧고 넓은 표)
```

컴펜디움이 알아서 하는 일이 둘 있고, 둘 다 알아 둘 값어치가 있습니다.

- **한 쪽보다 긴 표는 들어가는 만큼의 행을 보여줍니다** — 어림이 아니라 실제로 그려서 잽니다 — 그리고 표 아래에 몇 행 중 몇 행인지, 어떤 순서인지, 나머지는 CSV에 있다는 것을 적습니다.
- **한 쪽보다 넓은 표도 같은 문제가 옆으로 누운 것입니다.** 아홉 열쯤까지는 세워서 그리고, 그보다 넓으면 돌려서 그립니다. 그런데 어느 너비를 넘으면 글자 크기로는 해결되지 않습니다 — 모든 열이 자기 가장 긴 낱말보다 좁아집니다. 답은 고르는 것입니다. 독자가 종이에서 읽을 열을 `render.columns`에 적고, 기계가 읽을 나머지는 CSV에 둡니다. 그러면 페이지가 몇 열 중 몇 열을 보여주는지 적어 줍니다.

아무도 지정하지 않은 열의 서식은 데이터에서 고릅니다. 소수점 아래가 없는 실수는 소수점을 버리고, 천 단위에 이르는 열은 자릿수를 끊어 주며, 작은 P 값은 지수 표기로 두고, 다섯 자리 이상의 정수는 끊어 씁니다(같은 표의 `chr1:24,905,310` 옆에 `7301884`가 아니라 `7,301,884`).

## 5. 분석 스크립트 안에서

스크립트는 다른 형태와 똑같이 이름으로 표를 그리고, 인쇄한 내용을 그 패널의 source data로 등록합니다.

```python
import fig_atlas
from fig_atlas import source_data

printed = fig_atlas.render("table", ax, summary, cfg.get("plots", {}).get("group_summary", {}))
source_data.add(printed, panel="b", title="Latency by treatment group")
```

`render_table`은 **인쇄된 그대로의** 행을 돌려줍니다 — 서식이 적용되고 순서도 그대로 — 그래서 source data와 지면이 같은 글자를 담습니다. 반환값의 `attrs["height_pt"]`는 표가 실제로 그려진 높이이고, 컴펜디움은 이것으로 페이지의 상자를 내용에 맞춥니다.

## 6. 표의 숫자는 계산하는 것이지 적는 것이 아닙니다

그림 범례와 같은 규칙입니다. 개수, 좌표, 거리, 비율은 전달된 데이터에서 읽혀서 표에 들어갑니다. 생성 코드나 분석 스크립트에서 읽습니다([분석 레시피](analysis_recipes.md)). 손으로 쓰는 것은 판단뿐입니다 — construct의 이름, 해석 한 문장 — 그리고 그런 문장 안의 숫자도 서식 필드로 계산값을 받습니다.

손으로 적은 표는 소리 없이 어긋나고, 그 어긋남은 보이지 않습니다. 그림은 고쳐지는데 표는 고쳐지지 않고, 빌드의 어느 단계도 둘을 비교하지 않습니다. 데이터를 읽는 생성 코드는 시험도 됩니다 — 입력 사본의 값을 바꿔 보고 그 칸이 따라 움직이는지 확인하면 됩니다.

## 7. 한계

| | |
|---|---|
| 긴 표 | `max_rows`(기본 40)를 넘는 행은 버리고 `truncation_note`에 몇 행인지 적습니다. 수천 행짜리 표는 이 형태가 아닙니다. CSV로 두십시오 |
| 칸의 글자 | `max_lines`(기본 3)까지 접힙니다. 거기서 잘린 칸은 `truncation_mark`로 끝나므로, 잘린 글이 전체인 양 보이지 않습니다 |
| 가장 작은 글자 | 인쇄 하한은 5.0 pt(`cell_size`)이고, 그보다 작으면 preflight가 오류로 보고합니다 |
| 묶음 머리글 | `column_groups`가 여러 열 위에 라벨을 얹고, 그 열들 위에만 선을 긋습니다 |
| 칸 병합, 다단 머리글, 칸 안의 색 눈금 | 그리지 않습니다. 그것이 필요한 표는 히트맵입니다 |

## 다음에 볼 곳

- [표 번들 계약](../contracts/table_bundle_contract.md) — `plot_type: table`과 `fa bundle check`가 검사하는 것
- [렌더러 갤러리](../reference/gallery.md#table) — 예제 번들, 그 데이터와 복사해 쓸 명령
- [설정 키](../reference/config.md) — 스키마에서 생성된 렌더러의 모든 파라미터
- [그림이 인쇄하는 숫자 계산하기](analysis_recipes.md) — 표의 숫자가 어디서 오는지
