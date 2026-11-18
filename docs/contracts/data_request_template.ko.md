# 데이터 요청서 양식 (모든 요청에 하나의 양식)

데이터를 요청하는 모든 경우(새 번들, 고친 번들, 빠진 열, 재실행)는 이 양식 하나에서 시작한다. 사람이 쓰든
에이전트가 쓰든 같다. 요청서는 데이터를 만드는 쪽(분석 파이프라인, 서버, 다른 패키지, 동료)에게 보내고,
무엇을 요청했고 무엇이 왔으며 어디서 왔는지의 기록으로 저장소에 남긴다.

**쓰는 법**

1. 아래 블록을 `docs/data_contracts/<이름>_request.md`로 복사한다. 이름은 `_request.md`로 끝나야 한다.
   `fa storyline requests`와 `fa storyline evidence`가 그것으로 요청서를 찾는다.
2. 모든 절을 채운다. 해당하지 않는 절은 지우지 말고 "없음." 한 줄을 남긴다. 지우면 만드는 쪽은 그 절을
   빠뜨린 것인지 알 수 없다.
3. 다 채우면 `<!-- ... -->` 안내 주석을 지운다.
4. 만드는 쪽에 이 파일과 [번들 계약서](README.md)를 함께 알려 준다. 번들이 갖춰야 할 모양은 모두
   계약서에 있고, 요청서는 이번 납품이 무엇인지만 말한다.
5. 같은 데이터에 대한 후속 요청은 **같은 문서** 안의 새 개정이다(`version: r1.1`, 8절에 새 항목). 새
   문서를 만들지 않는다. 다른 질문이면 새 문서를 만들고, 그것이 예전 문서를 대신하면 예전 문서의
   `superseded_by`에 새 문서의 이름을 적는다.

---

양식 블록은 한 곳에서 관리하도록 영어 원문 그대로 둔다. 요청서 본문은 어느 언어로 써도 된다.

````markdown
---
request: "<name>"          # the file name without _request.md
status: open               # open | partial | delivered | resolved | superseded
date: "YYYY-MM-DD"         # the day it was sent
version: "r1"              # r1, r1.1, r2 ... one per round with the producer (section 8)
delivered: []              # filled when data arrive: the raw_data/ files or folders that landed (globs allowed)
derived: []                # bundle files built here from the delivery, if any
superseded_by: []          # names of requests that replace this one
---

# Data request: <one line that says what is asked>

**Producer**: <who makes the data: pipeline, server, package, person>
**Consumer**: <project(s) and figure/panel that will read it, e.g. `kyg-paper-main-fig3-...`, panel b>
**Contract**: <bundle contract and plot_type for each bundle, e.g. `table_bundle_contract.md`, `line_band`; "new plot type" -> `new_plot_type_contract.md`>
**Priority**: <blocking | needed before <date> | when convenient>

## 0. Why

<!-- What the figure needs, what is missing or wrong now, and what was already ruled out.
     Quote the observation (a number, a file, a build message), not an impression. -->

## 1. Check first -- you may already have it

<!-- Files or results the producer may already hold that would answer this without new work.
     "None." if there is nothing to check. -->

## 2. What to deliver

<!-- One row per bundle. A bundle is one panel's data: inputs/data.csv + metadata/metadata.yaml.
     Folder names, column names and metadata fields follow the contract named above; write here only
     what is specific to this delivery. -->

| Bundle folder (under `raw_data/`) | plot_type | New or change | Columns / content |
|---|---|---|---|
| `<study>/<project>/<bundle>/` | `<plot_type>` | new / change of `<file>` | `<col_a>`, `<col_b>` (unit), ... |

Rules that apply to every bundle (from the contracts):

- Column names exactly as given, case included; order does not matter.
- Values as the analysis produced them: not rounded, not renamed, not shortened for display.
- Absent means no row: no placeholder rows filled with NaN.
- A change to a delivered bundle is a new version: say what changed and why in `metadata.yaml`
  `notes` and in section 8 below. Delivered files are not edited in place without saying so.

## 3. Where it came from (`upstream` in each bundle's metadata.yaml)

Each bundle's `metadata/metadata.yaml` states what it was made from (decision 0008). Fill in what you
know; a path without a hash is better than nothing.

```yaml
upstream:
  host: <machine or service where the bundle was made>
  produced_by: <script path @ commit, or tool and version>
  files:                          # the files the bundle was made from
    - path: <path on that machine>
      sha256: <sha256sum output>  # `sha256sum <file>` on Linux/macOS, `certutil -hashfile <file> SHA256` on Windows
      size: <bytes>
```

## 4. Validation

Before delivering:

- [ ] `fa bundle check raw_data/<...>/<bundle>` reports no error for each bundle
- [ ] every column of section 2 is present with exactly that name
- [ ] `upstream` is filled in each `metadata.yaml` (section 3)
- [ ] <checks specific to this request: expected row count, value range, a known value to match>

## 5. Not asked for

<!-- What this request deliberately leaves out, so it is not produced by mistake. "None." if nothing. -->

## 6. Questions for the producer

<!-- Decisions the producer has to make or confirm. Number them so answers can refer to them. -->

## 7. Delivery

**Destination**: `raw_data/<study>/<project>/` (one folder per bundle, as in section 2)
**Delivery notes**: <a short note beside the bundles, e.g. `raw_data/<study>/DELIVERY_NOTES_<name>.md`,
saying what was delivered and anything that differs from this request>

## 8. Revisions

<!-- One entry per round, newest last. The producer's answer goes here too. -->

### r1 (YYYY-MM-DD) -- request sent
````

---

**데이터가 도착하면** (요청한 사람이나 에이전트가):

1. 납품된 번들마다 `fa bundle check`를 돌린다.
2. 머리말의 `delivered`(이곳에서 번들을 만들었으면 `derived`도)를 채우고 `status`를 정한다
   (`delivered`, 또는 빠진 것을 8절에 적고 `partial`).
3. `fa storyline requests`는 모든 요청과 그 상태, 그리고 어느 게시 그림이 그것을 쓰는지 보여 준다.
   `fa storyline evidence <slot|project>`는 그림에서 이 요청까지 거슬러 올라가는 사슬을 보여 준다.
