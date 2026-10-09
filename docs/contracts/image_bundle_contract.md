# 계약서: 이미지 번들 (현미경 이미지·블롯·젤)

분야와 무관한 이미지 데이터 번들의 폴더·파일·메타데이터 스펙입니다. 이 형식으로 받은 이미지는 코어 렌더러 `render_image_panel`(`plot_type: image_panel`)이 바로 그리고, 크롭·표시 범위·감마 같은 조정 내역은 원본 해시와 함께 provenance와 README에 기록됩니다(AGENTS.md §4.7). 표 형식 번들의 일반 규칙은 [`new_plot_type_contract.md`](new_plot_type_contract.md)를 따릅니다.

> 이 계약서는 이미징 시범(로드맵 6a.4, 공개 BBBC013)에서 나왔습니다. 그 데이터는 픽셀 크기를 공개하지 않아 스케일바를 그릴 수 없었고, 그래서 아래의 `pixel_size`는 필수입니다.

## 폴더 구조

```
<bundle_name>/
  inputs/
    <채널 파일 1>.tif        # 채널마다 흑백 파일 하나 (또는 컬러 사진 한 장)
    <채널 파일 2>.tif
  metadata/
    metadata.yaml            # 필수 — 아래 키
```

## `inputs/` 이미지 파일 규칙

| 규칙 | 내용 |
|---|---|
| **원본 그대로** | 밝기·대비를 조정하거나 잘라 낸 사본을 넣지 않습니다. 조정은 그림을 그릴 때 config로 하고, 그 내역이 기록됩니다. |
| **채널마다 파일 하나** | 다채널 현미경 이미지는 채널별 흑백 파일로 냅니다(8비트 또는 16비트). 렌더러가 채널 색을 입혀 합성합니다. 컬러 사진(예: 블롯 촬영본)은 한 파일로 냅니다. |
| **무손실 형식** | TIFF 또는 PNG를 씁니다. JPEG는 압축 손실이 있어 정량에 쓰지 않습니다. 형식은 Pillow가 읽을 수 있어야 합니다(PNG, JPEG, 8/16비트 TIFF). |
| **같은 크기** | 한 번들의 채널 파일은 가로·세로 픽셀 수가 같아야 합니다. |

## `metadata/metadata.yaml`

```yaml
plot_type: image_panel

# 필수: 픽셀 하나의 물리 크기. 스케일바에 쓰입니다.
# 출처가 공개하지 않으면 null로 적고 사유를 남깁니다 (빠뜨린 것과 구분하기 위해).
pixel_size: 0.325
pixel_unit: "µm"
# pixel_size: null
# pixel_size_note: "BBBC013 does not publish the pixel size"

# 필수: 채널 목록 (inputs/ 안의 파일 이름). label·color는 그림의 기본값입니다.
channels:
  - file: "dna.tif"
    label: "DNA"
    color: "#3b82f6"
  - file: "gfp.tif"
    label: "FKHR-GFP"
    color: "#22c55e"

# 권장: 획득 조건과 출처
acquisition:
  instrument: "IN Cell Analyzer 3000"
  objective: "40x / 0.6 NA"
  exposure_ms: [100, 250]          # 채널 순서
source:
  license: "CC BY 3.0"
  citation: "Ljosa et al., Nature Methods, 2012"
  url: "https://bbbc.broadinstitute.org/BBBC013"
```

| 키 | 필수 | 설명 |
|---|---|---|
| `plot_type` | 필수 | `image_panel` |
| `pixel_size` | 필수 (값은 `null` 가능) | 픽셀 하나의 크기, `pixel_unit` 단위. `null`이면 `pixel_size_note`에 사유 |
| `pixel_unit` | 권장 | 기본 `µm` |
| `channels` | 필수 | 채널마다 `file`(필수), `label`, `color` |
| `acquisition` | 권장 | 장비, 대물렌즈, 노출 등 — 범례 작성에 씁니다 |
| `source` | 공개 데이터는 필수 | 라이선스, 인용, URL — 범례의 출처 문구에 기록값으로 들어갑니다 |

크롭 위치, 표시 범위, 감마는 번들에 넣지 않습니다. 그림마다 다를 수 있으므로 프로젝트 config(`plots.<name>`)에 둡니다.

## 검사

```bash
fa bundle check raw_data/<study>/<project>/<bundle_name>
```

- **오류:** 이미지 파일이 없음, `metadata.yaml`에 `pixel_size`나 `channels` 키가 없음, `channels`가 가리키는 파일이 `inputs/`에 없음
- **통과하면:** 그릴 렌더러로 `fig_atlas.renderers:render_image_panel`이 표시됩니다.

기계 검사 정의는 `fig_atlas/contracts.py`의 `core.image`입니다.
