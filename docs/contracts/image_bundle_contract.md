# Contract: image bundles (microscope images, blots, gels)

The folder, file and metadata specification of image data bundles, for any field. Images received in this format are drawn directly by the core renderer `render_image_panel` (`plot_type: image_panel`), and adjustments such as crop, display range and gamma are recorded with the originals' hashes in the provenance record and the README (AGENTS.md §4.7). General rules for tabular bundles follow [`new_plot_type_contract.md`](new_plot_type_contract.md).

> This contract came out of the imaging pilot (roadmap 6a.4, public BBBC013). Those data do not publish the pixel size, so no scale bar could be drawn — which is why `pixel_size` below is required.

## Folder structure

```
<bundle_name>/
  inputs/
    <channel-file-1>.tif     # one greyscale file per channel (or one colour photograph)
    <channel-file-2>.tif
  metadata/
    metadata.yaml            # required — the keys below
```

## Rules for the image files in `inputs/`

| Rule | Content |
|---|---|
| **Originals only** | No copies with adjusted brightness or contrast, and no cropped copies. Adjustments are made in the config when the figure is drawn, and they are recorded. |
| **One file per channel** | A multichannel microscope image comes as one greyscale file per channel (8- or 16-bit). The renderer tints and combines the channels. A colour photograph (e.g. of a blot) comes as one file. |
| **Lossless formats** | Use TIFF or PNG. JPEG loses information in compression and is not used for quantification. The format must be readable by Pillow (PNG, JPEG, 8/16-bit TIFF). |
| **The same size** | The channel files of one bundle must have the same width and height in pixels. |

## `metadata/metadata.yaml`

```yaml
plot_type: image_panel

# Required: the physical size of one pixel, used for the scale bar.
# If the source does not publish it, write null and give the reason (to tell it apart from an omission).
pixel_size: 0.325
pixel_unit: "µm"
# pixel_size: null
# pixel_size_note: "BBBC013 does not publish the pixel size"

# Required: the channels (file names in inputs/). label and color are the figure's defaults.
channels:
  - file: "dna.tif"
    label: "DNA"
    color: "#3b82f6"
  - file: "gfp.tif"
    label: "FKHR-GFP"
    color: "#22c55e"

# Recommended: acquisition and source
acquisition:
  instrument: "IN Cell Analyzer 3000"
  objective: "40x / 0.6 NA"
  exposure_ms: [100, 250]          # in channel order
source:
  license: "CC BY 3.0"
  citation: "Ljosa et al., Nature Methods, 2012"
  url: "https://bbbc.broadinstitute.org/BBBC013"
```

| Key | Required | Description |
|---|---|---|
| `plot_type` | Required | `image_panel` |
| `pixel_size` | Required (the value may be `null`) | The size of one pixel, in `pixel_unit`. If `null`, the reason goes in `pixel_size_note` |
| `pixel_unit` | Recommended | Default `µm` |
| `channels` | Required | Per channel `file` (required), `label`, `color` |
| `acquisition` | Recommended | Instrument, objective, exposure and so on — used for writing the legend |
| `source` | Required for public data | Licence, citation, URL — they go into the legend's source sentence as recorded values |

Crop position, display range and gamma are not put in the bundle. They can differ from figure to figure, so they belong in the project config (`plots.<name>`).

## Checks

```bash
fa bundle check raw_data/<study>/<project>/<bundle_name>
```

- **Errors:** no image files; no `pixel_size` or `channels` key in `metadata.yaml`; a file named in `channels` is not in `inputs/`
- **When it passes:** `fig_atlas.renderers:render_image_panel` is shown as the renderer that draws it.

The machine-checkable definition is `core.image` in `fig_atlas/contracts.py`.
