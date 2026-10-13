# Tutorial: 데이터가 바뀐 뒤 — 낡은 그림 찾기, 다시 그리기, 스토리라인 개편

논문 그림은 한 번 그리고 끝나지 않습니다. 데이터가 다시 전달되고, 그림이 논문 Figure로 올라가고, 스토리라인이 바뀝니다. 이 튜토리얼은 그 흐름을 명령만으로 따라 합니다.

- 같은 데이터를 읽는 그림 두 개를 만들고, 하나를 논문 Figure 1로 **승격**합니다.
- **스토리라인**을 시작하고 첫 컴펜디움(R000)을 만듭니다.
- 데이터가 **다시 전달**되면, 어떤 그림이 낡았는지(`fa status`)와 그 파일을 읽는 그림이 무엇인지(`fa impact`)를 찾습니다.
- 다시 그리고, 무엇이 바뀌었는지 스토리라인 **개편 기록**으로 남깁니다(R001).

준비물: `fa`가 설치된 Python 환경, 그리고 `fa init`으로 만든 프로젝트 저장소(또는 이 저장소). 예제 번들은 `examples/gallery/`에 있습니다. 아래 명령은 POSIX 셸 기준입니다.

## 1. 같은 데이터를 읽는 그림 두 개

<!-- run -->
```bash
fa new project lab-dose --domain lab --category exploratory
fa new project lab-dose-qc --domain lab --category exploratory
mkdir -p raw_data/dose-study
cp -r examples/gallery/dose_response raw_data/dose-study/
fa ingest bundle raw_data/dose-study/dose_response --project lab-dose
fa ingest bundle raw_data/dose-study/dose_response --project lab-dose-qc
fa build lab-dose lab-dose-qc --preflight
```

두 프로젝트가 같은 번들을 읽습니다. 하나는 논문에 들어갈 그림, 하나는 품질 확인용 그림이라고 생각하면 됩니다.

## 2. 논문 Figure 1로 승격

<!-- run -->
```bash
fa promote lab-dose --figure 1 --slug viability
```

설정, 분석 스크립트, figure spec이 `lab/paper/`로 옮겨지고 이름이 `lab-paper-main-fig1-viability`가 됩니다. 파일 안의 경로도 함께 고쳐지고, 승격된 프로젝트가 한 번 빌드됩니다.

## 3. 스토리라인 시작

<!-- run -->
```bash
fa storyline new dose --title "Dose study"
```

`docs/storylines/dose/storyline.yaml`(어느 프로젝트가 어느 Figure인지)과 `docs/storylines/figure_plan_dose.md`(서술과 개편 기록)가 생깁니다. `storyline.yaml`에 Figure 1을 적습니다.

<!-- replace: docs/storylines/dose/storyline.yaml | figures: [] -->
```yaml
figures:
  - slot: "Main Figure 1"
    project: "lab-paper-main-fig1-viability"
    figure_number: 1
    description: "Viability over dose"
```

<!-- run -->
```bash
fa storyline registry
fa storyline check
fa storyline compile --strict
```

`registry`가 계획 문서의 표를 다시 쓰고, `check`가 프로젝트와 맞는지 확인하고, `compile`이 컴펜디움 PDF를 만들어 **R000**으로 보관합니다(`outputs/storylines/figure_plan_dose/R000/`). `--strict`는 낡은 그림이나 preflight 오류가 있으면 만들지 않습니다.

## 4. 데이터가 다시 전달되면

실험실이 compound B의 값을 고친 데이터를 다시 보냈다고 합시다. 원본은 우리가 고치지 않습니다. 새로 받은 파일이 그 자리를 대신합니다(여기서는 한 줄을 바꿔 흉내 냅니다).

<!-- replace: raw_data/dose-study/dose_response/inputs/data.csv | compound B,0.01,1,100.99 -->
```text
compound B,0.01,1,90.99
```

<!-- run -->
```bash
fa status
fa impact raw_data/dose-study/dose_response
```

`fa status`는 그 파일을 읽은 두 그림을 **STALE**로, 이유(`input changed: .../data.csv`)와 함께 보여 줍니다. 내용 해시로 비교하므로 파일을 열었다 닫기만 한 경우는 낡은 것으로 치지 않습니다. `fa impact`는 그 번들을 읽은 그림을 프로젝트에 상관없이 모두 찾습니다. 승격 전의 옛 출력 폴더는 "더 이상 없는 프로젝트의 옛 출력"으로 따로 표시됩니다.

이 상태에서 컴펜디움을 만들면 거절됩니다.

```bash
fa storyline compile --strict
#   [!] stale: lab-paper-main-fig1-viability fig 1 -- input changed: raw_data/dose-study/dose_response/inputs/data.csv
#   [x] --strict: not compiling with stale figures or preflight errors
```

다시 그리고, 지난 컴펜디움 이후 무엇이 바뀌었는지 봅니다.

<!-- run -->
```bash
fa build lab-paper-main-fig1-viability lab-dose-qc --preflight
fa storyline diff --draft
```

`diff --draft`는 R000 이후 바뀐 것(그림과 그 이유: data / config / code)을 모아 개편 기록의 초안 한 줄을 제안합니다. 숫자를 손으로 옮겨 적지 않아도 됩니다.

## 5. 개편 기록 남기기

제안된 줄에 제목과 이유를 채워 계획 문서의 `## Revisions` 아래에 넣습니다.

<!-- replace: docs/storylines/figure_plan_dose.md | ## Revisions -->
```markdown
## Revisions

> **2026-10-13 Revision (1) — corrected delivery**: the lab re-sent the dose data with compound B corrected; Main Figure 1 was rebuilt from it. Changes since R000: `lab-paper-main-fig1-viability` (data).
```

<!-- run -->
```bash
fa storyline revisions --sync
fa storyline compile --strict
fa storyline snapshots
fa storyline diff
```

`revisions --sync`가 개편 기록을 `docs/storylines/dose/revisions/R001.md`로 옮겨 적고(이후 그 파일의 `kind`, `evidence` 머리말을 채웁니다), `compile`이 새 컴펜디움을 **R001**로 보관합니다. R000은 그대로 남습니다. `fa storyline diff`는 두 컴펜디움 사이의 차이, 즉 어느 Figure의 어떤 입력이 바뀌었는지를 보고서로 씁니다.

데이터 요청 문서(`docs/data_contracts/*_request.md`)에 전달 정보를 적어 두면 `fa storyline evidence "Main Figure 1"`이 그림에서 그 요청과 개편 기록까지 거슬러 올라갑니다.
