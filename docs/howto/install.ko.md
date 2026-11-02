# fig-atlas 설치

fig-atlas는 명령어 도구 `fa`가 들어 있는 파이썬 패키지입니다. 대부분은 그림 작업에 쓰는 환경에 **릴리스**를
설치하고, 그림은 따로 만든 *프로젝트 저장소*(`fa init`으로 생성)에 둡니다. fig-atlas 자체를 고치는 사람만
소스 사본이 필요합니다(마지막 절).

아직 PyPI 패키지가 없어서 `pip install fig-atlas`는 동작하지 않습니다. 대신 pip가 GitHub에서 릴리스를 바로
설치하며, 버전 고정도 똑같이 됩니다.

## 준비할 것

| | |
|---|---|
| 파이썬 | 3.10 이상 (테스트는 3.12에서 돌아갑니다), Windows, macOS, Linux |
| 환경 | conda(Miniconda, Anaconda) 또는 파이썬의 `venv`. 연구 프로젝트마다 환경을 하나씩 두면 재현하기 가장 쉽습니다 |
| Git | 아래 첫 번째 설치 방법에 필요합니다. 두 번째 방법은 Git 없이 됩니다 |
| 글꼴 | 저널 프리셋은 Arial을 씁니다. Windows와 macOS에는 있고, Linux에서는 설치하세요(예: `ttf-mscorefonts-installer`). 없으면 검사가 대체된 글꼴을 보고합니다 |

## 릴리스 설치

[릴리스 페이지](https://github.com/ibs-CMG-NGS/fig-atlas/releases)에서 가장 최근 릴리스를 고릅니다.
아래 명령은 `v0.2.1` 기준입니다.

conda를 쓸 때:

```bash
conda create -n figures python=3.12
conda activate figures
pip install "git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1"
```

`venv`를 쓸 때:

```bash
python -m venv .venv
.venv\Scripts\activate                 # Windows (PowerShell 또는 cmd)
source .venv/bin/activate              # macOS, Linux
pip install "git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1"
```

Git이 없으면 릴리스 압축 파일로 설치합니다(같은 패키지).

```bash
pip install "https://github.com/ibs-CMG-NGS/fig-atlas/archive/refs/tags/v0.2.1.zip"
```

선택 기능은 대괄호 안에 이름을 씁니다. `workflow`(Snakemake), `docs`(이 문서 사이트 빌드), `test`(pytest)입니다.

```bash
pip install "fig-atlas[workflow] @ git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1"
```

## 설치 확인

```bash
fa --version
fa --help
```

`fa --version`은 버전과 패키지를 불러오는 폴더를 보여 줍니다. 예: `fa 0.2.1 (.../site-packages)`. `fa renderers`와 `fa layouts`는 프로젝트 저장소를 만들기 전에도 그릴 수 있는 그림과 배치를 보여 줍니다.
다음은 프로젝트 저장소와 첫 그림 만들기입니다: [튜토리얼: 첫 그림](../tutorials/first_figure.md).

## 프로젝트 저장소에 버전 고정

프로젝트 저장소 맨 위의 `requirements.txt`에 릴리스를 적어 두면, 공동 저자, 심사위원, 2년 뒤의 나 누구든 같은
fig-atlas를 설치합니다.

```text
fig-atlas @ git+https://github.com/ibs-CMG-NGS/fig-atlas@v0.2.1
```

```bash
pip install -r requirements.txt
```

`pip freeze`는 실제로 설치된 커밋을 보여 줍니다. 그림마다 출처 기록에도 빌드에 쓴 코드가 남습니다.

## 업그레이드

새 릴리스의 [변경 기록](https://github.com/ibs-CMG-NGS/fig-atlas/blob/main/CHANGELOG.md)을 읽고,
`requirements.txt`의 버전을 바꾼 뒤 다시 설치합니다.

```bash
pip install --upgrade -r requirements.txt
fa --version
fa build --all --preflight
```

그림을 보내기 전에 다시 빌드해서 확인하세요. 새 릴리스는 기본값을 바꿀 수 있고, 무엇이 달라졌는지 검사가
알려 줍니다.

## fig-atlas 자체를 고칠 때

fig-atlas를 고치려면 소스 사본을 *편집 가능(editable)* 모드로 설치해, 고친 내용이 바로 반영되게 합니다.

```bash
git clone https://github.com/ibs-CMG-NGS/fig-atlas
cd fig-atlas
pip install -r requirements.txt
pip install -e ".[docs,test]"
```

또는 `conda env create -f environment.yml`이 패키지를 편집 가능 모드로 설치한 환경 `fig-atlas`를 만듭니다.
테스트는 `python -m pytest`로 돌립니다.

## 문제가 생기면

| 증상 | 원인과 해결 |
|---|---|
| `fa: command not found` (Windows에서는 `'fa'은(는) ... 인식되지 않습니다`) | 환경이 활성화되지 않았습니다. `conda activate figures`(또는 `venv` 활성화). `python -m fig_atlas`도 `fa`와 똑같이 동작합니다. |
| 설치 중 `git: command not found` | 위의 압축 파일 방법(`.../archive/refs/tags/v0.2.1.zip`)을 쓰거나 Git을 설치하세요. |
| `fa --version`이 예상과 다른 폴더를 보여 줌 | 파이썬이 다른 fig-atlas 사본을 찾았습니다. fig-atlas 소스 폴더 안에서 실행하면 흔히 생깁니다. 프로젝트 저장소에서 `fa`를 실행하세요. |
| Windows에서 환경의 `python.exe`를 직접 실행할 때 DLL 오류 | 먼저 환경을 활성화하세요. 활성화해야 라이브러리 폴더(`Library\bin`)가 경로에 들어갑니다. |
| 검사가 대체된 글꼴을 보고함 | Arial을 설치하거나(Linux), 가진 글꼴을 쓰는 프리셋을 쓰세요. |
