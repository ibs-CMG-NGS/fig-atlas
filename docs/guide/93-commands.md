---
title: 부록 C. 명령 한 장 요약
audience: 터미널을 쓰는 연구자
reviewed: 2026-10-08
---

# 부록 C. 명령 한 장 요약

AI에게 말로 시키는 일은 모두 아래 명령으로도 할 수 있습니다. 터미널(Windows의 명령 프롬프트·PowerShell, macOS·Linux의 터미널, 또는 편집기 안의 터미널)에서 저장소 폴더에 있을 때 씁니다. 환경을 먼저 켭니다(`conda activate fig-atlas`, 어느 폴더에서든).

- 모든 명령은 `fa --help`, `fa 명령 --help`로 설명을 볼 수 있습니다.
- 파일을 바꾸는 명령은 `--dry-run`을 붙이면 **바뀔 내용만 보여 주고 아무것도 쓰지 않습니다.**
- `--json`을 붙이면 프로그램이 읽는 형식으로 결과를 냅니다(AI가 쓰는 방식).

## 프로젝트와 데이터

| 하고 싶은 일 | 명령 | 장 |
|---|---|---|
| 새 프로젝트 | `fa new project 이름 --domain lab --category exploratory` | 4 |
| 번들 검사 | `fa bundle check 번들폴더` | 3 |
| 그릴 수 있는 그림 종류와 계약서 | `fa bundle contracts` | 3 |
| 번들을 패널로 붙이기 (+ 빌드) | `fa ingest bundle 번들폴더 --project 이름` | 4 |
| 프로젝트 목록 | `fa list` | — |
| 그릴 수 있는 그림 이름 | `fa renderers` | — |

## 빌드와 검사

| 하고 싶은 일 | 명령 | 장 |
|---|---|---|
| 빌드 | `fa build 이름` | 4 |
| 빌드 + 인쇄 전 검사 | `fa build 이름 --preflight` | 8 |
| 검증만 | `fa verify 이름` | 8 |
| 설정 값이 어디서 왔는지 | `fa param explain 이름 plots.패널.키` | 6 |
| 빌드가 기본값으로 대신한 키를 설정에 채우기 | `fa param sync 이름` (미리보기) → `--apply` | 6 |
| 안 쓰이는 설정 키·오타 찾기 | `fa lint 이름` | 6 |
| 손으로 쓴 숫자 찾기 | `fa claims 이름 --list` | 9 |
| 인쇄 크기 감사 | `fa audit-print` | 7 |

## 출처와 신선도

| 하고 싶은 일 | 명령 | 장 |
|---|---|---|
| 낡은 그림 찾기 | `fa status` | 10 |
| 이 파일을 쓰는 그림 | `fa impact 파일경로` | 10 |
| 그림의 뿌리 | `fa lineage 이름` | 10 |
| 스냅샷 이후 바뀐 것 | `fa diff-figure 이름` | 10 |
| 투고 패키지 (RO-Crate zip) | `fa export 이름 --zip` | 7 |

## 논문 생애주기와 스토리라인

| 하고 싶은 일 | 명령 | 장 |
|---|---|---|
| 승격 | `fa promote 이름 --figure 2 --slug 짧은이름` | 11 |
| 은퇴 | `fa retire 이름` | 11 |
| 대응표 다시 쓰기 | `fa storyline registry` | 11 |
| 스토리라인 정합성 검사 | `fa storyline check` | 11 |
| 바뀐 것 초안 | `fa storyline diff --draft` | 11 |
| 개편 기록 동기화 | `fa storyline revisions --sync` | 11 |
| 컴펜디움 PDF (엄격; 이 시점의 스냅샷도 저장) | `fa storyline compile --strict` | 11 |
| 바뀐 내용 기록 저장 | `fa storyline diff --write` | 11 |
| 저장된 스냅샷 목록 | `fa storyline snapshots` | 11 |
| 그림의 근거 추적 | `fa storyline evidence "Main Figure 3"` | 11 |

## 만드는 사람용

| 하고 싶은 일 | 명령 |
|---|---|
| 새 그림 종류(렌더러) 골격 | `fa new renderer 이름 --plot-type 종류` |
| 코드 속 숫자(하드코딩) 검사 | `fa lint --hardcoded` |
| AI 도우미에 도구 제공 | `fa mcp` ([연결 방법](../howto/ai_agents.md)) |

연구 저장소에서 `fa new renderer`를 실행하면 렌더러는 그 저장소의 `renderers/` 폴더에 만들어집니다. 패키지를 설치하거나 고칠 필요 없이 `fa renderers`, `fa ingest bundle`, `fa build`가 그 렌더러를 찾고, 출처 기록에도 그 파일이 남습니다. 다른 연구에도 쓸 만한 모양(막대, 선, 산점도, 히트맵)이면 나중에 fig-atlas 코어로 옮기는 것을 고려하세요.

---
이전: [부록 B. 자주 묻는 질문과 문제 해결](92-faq.md) · 다음: [부록 D. 더 읽을거리](94-reading.md)
