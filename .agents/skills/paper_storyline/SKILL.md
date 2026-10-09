---
name: "paper_storyline"
description: "Analyze figure atlas manifests and panel notes to screen candidate figures and generate a hypothesis-driven manuscript figure plan."
---

# Paper Storyline Agent Skill (논문 피겨 선별 및 스토리라인 수립 지침)

이 지침서는 탐색 단계(Phase 1)에서 생성된 수십 개의 피겨 및 매니페스트(`outputs/clean_atlas_manifest.csv`)를 기반으로, 연구자의 가설에 부합하는 **논문 본문(Main Figures 1~6) 및 보충자료(Supplementary Figures) 배치안을 기획·제안하는 4단계 프로토콜**입니다.

---

## 4단계 스토리라인 기획 프로토콜 (4-Step Storyline Protocol)

### Step 1: 아틀라스 인덱스 및 메타데이터 전수 조사
1. 최신 매니페스트 `outputs/clean_atlas_manifest.csv`를 로드하여 현재 사용 가능한 모든 프로젝트 목록, 피겨 번호, 제목, 소스 코드 경로를 파악합니다.
2. 주요 후보 프로젝트의 `figure_specs/figure_*.py`를 확인하여:
   - `panel_notes`: 각 서브패널이 나타내는 시각화 종류(Volcano, MA, Cluster Heatmap, GO Dotplot 등)
   - `claim_boundary`: 데이터가 직접적으로 증명하는 범위와 한계
   를 확인합니다.

### Step 2: 연구 가설 및 타겟 저널 맞춤 구조화
사용자가 제시한 연구 질문(예: "급성 vs 만성 산화 스트레스 하에서 유전자 발현과 염색질 동역학")에 맞춰 논문의 전형적인 흐름으로 피겨를 배치합니다:
- **Main Figure 1 (Overview & Baseline Landscape)**: 전체 오믹스 프로파일링, 글로벌 변화, QC, 대표 화산도(Volcano)/MA 플롯
- **Main Figure 2 (Dynamic Progression / Clusters)**: 시계열(Time-series) 클러스터링, maSigPro/WGCNA 패턴, 경로(GO/KEGG) 농축
- **Main Figure 3 (Cross-condition / Cross-species Comparison)**: 급성 vs 만성 비교, 인간 vs 마우스 상동 유전자 일치도(Concordance)
- **Main Figure 4~5 (Mechanism & Target Discovery)**: 핵심 타겟 유전자 좁히기(Funnel/Tier), 프로모터 모티프(HOMER) 및 조절 인자 규명
- **Supplementary Figures**: 상세 QC 지표, 개별 조건별 전체 GO/KEGG 트리맵 및 파라미터 민감도 검증

### Step 3: 스토리라인 명세서 (`docs/storylines/figure_plan_<topic>.md`) 작성
기획안을 정형화된 마크다운 문서로 작성합니다:
```markdown
# Manuscript Figure Plan: [연구 제목]

## Target Journal: [저널명]
## Core Hypothesis: [핵심 가설 요약]

---

### Main Figure 1: [피겨 제목]
- **Core Narrative**: [이 피겨가 전달해야 하는 핵심 과학적 결론]
- **Proposed Layout**: [예: 2x2 Mosaic 또는 Top 2-col + Bottom 1-row]
- **Subpanel Mapping**:
  - **Panel A**: [시각화 종류] (`<project_name>` -> `<source_panel>`)
  - **Panel B**: [시각화 종류] (`<project_name>` -> `<source_panel>`)
  - ...
- **Key Takeaway**: [리뷰어/독자가 한눈에 얻어야 하는 인사이트]

---

### Supplementary Figure 1: [보충 피겨 제목]
...
```

### Step 4: 사용자 검토 게이트 (Human-in-the-loop Gate)
- 작성된 기획 문서를 사용자에게 제시하고, 패널 교체/추가/제거 피드백을 수렴하여 확정합니다.
- 확정된 계획은 즉시 **Phase 3 (`assemble_figure` 스킬)**로 인계됩니다.
- **피겨 배치(어느 프로젝트가 어느 슬롯인지, 보충 표, 은퇴 프로젝트)는 `docs/storylines/<topic>/storyline.yaml`에 기록합니다.** 이 파일이 컴펜디움 컴파일·인쇄 감사·preflight·기준선이 읽는 단일 원천입니다. 새 스토리라인은 `fa storyline init --plan docs/storylines/figure_plan_<topic>.md`로 만들 수 있습니다.
- 배치를 바꾼 뒤에는 `fa storyline registry`(md의 Master Mapping Registry 표 재생성, 상대경로 링크)와 `fa storyline check`(config·spec·`tasks.json`·archive 정합성)를 실행합니다. Registry 표를 손으로 고치지 않습니다.
- **개편할 때마다 기록을 남깁니다.** md에는 지금처럼 `> **YYYY-MM-DD 개편(N) — 제목**: ...` 블록을 쓰고(번호는 `fa storyline revisions`가 보고하는 latest + 1, 같은 번호를 다른 변경에 다시 쓰지 않음), 이어서 `fa storyline revisions --sync`로 `docs/storylines/<topic>/revisions/RNNN.md` 기록을 만듭니다. 기록의 머리말 중 `kind`(renumber/redesign/promote/retire/data-update/definition-change/layout)와 `evidence`(근거 데이터 요청 문서·배송 파일)를 채웁니다. 이미 있는 기록은 동기화가 덮어쓰지 않으므로 손으로 채운 머리말은 유지됩니다.
- **데이터 요청 문서**(`docs/data_contracts/*_request.md`)는 머리말에 `status`·`date`·`delivered`(배송 위치)·`derived`(배송분으로 만든 번들 파일)를 둡니다. 새 문서는 `fa storyline requests --sync`가 Status·Delivery 줄에서 초안을 만들어 주므로, 배송이 오면 `status`와 경로를 갱신합니다. 반영 여부(integrated)는 provenance에서 계산되므로 따로 적지 않습니다.
- **개편 블록을 쓰기 전에** `fa storyline diff --draft`로 직전 스냅샷 이후 실제로 바뀐 것(슬롯 이동, 피규어별 입력·config 키·코드)을 확인하고, 제안된 블록에 이유를 채웁니다. 수치를 손으로 옮겨 적지 말고 diff 결과를 인용합니다. 근거 데이터는 `fa storyline evidence "Main Figure N"`로 확인합니다(피규어 → 읽은 raw 데이터 → 그 데이터를 배송한 요청 문서 → 관련 개편). 블록을 추가한 뒤 `fa storyline compile --strict`(stale 피규어나 preflight error가 있으면 거부)로 새 개편 스냅샷을 만들고, `fa storyline diff --write`로 `revisions/RNNN.changes.md`를 남깁니다.

---

### Step 5: Multi-Page PDF 컴펜디움 자동 컴파일 (Storyline PDF Compilation)
스토리라인에 포함된 모든 피겨 빌드가 완료되면, 연구자 미팅, 랩 세미나, 논문 투고 패키지용으로 **단일 멀티페이지 벡터 PDF**를 즉시 컴파일합니다:
```bash
python -m fig_atlas storyline --plan docs/storylines/figure_plan_<topic>.md   # = fa storyline compile ...
```
- **Page 1 (Executive Summary Cover)**: 논문 제목, 핵심 가설, 피겨 인덱스 테이블(Figure, Project, Takeaway), 품질 보증 가이드가 수려한 저널 스타일로 렌더링됩니다.
- **Page 2+ (Vector Figures)**: Main Figures 1~N 및 Supplementary Figures가 300+ DPI 손실 없는 고해상도 벡터 PDF로 순차 병합되어 `docs/storylines/<topic>.pdf`로 저장됩니다.
