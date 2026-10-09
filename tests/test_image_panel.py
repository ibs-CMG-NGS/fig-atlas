"""Image panels (roadmap 6a.3): fig_atlas.images and render_image_panel."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from fig_atlas import images  # noqa: E402
from fig_atlas.images import Channel, prepare  # noqa: E402
from fig_atlas.renderers import render_image_panel  # noqa: E402


@pytest.fixture
def gray8(tmp_path):
    arr = np.tile(np.arange(0, 200, 2, dtype=np.uint8), (60, 1))     # 60 x 100, values 0..198 by column
    p = tmp_path / "gray.png"
    Image.fromarray(arr).save(p)
    return p, arr


def test_load_16_bit_tiff(tmp_path):
    arr = (np.arange(40 * 30, dtype=np.uint16).reshape(30, 40) * 50)
    p = tmp_path / "deep.tif"
    Image.fromarray(arr).save(p)
    got = images.load(p)
    assert got.dtype == np.uint16 and got.shape == (30, 40) and got.max() == arr.max()


def test_crop_and_linear_display_range(gray8):
    p, arr = gray8
    prep = prepare([Channel(str(p), display_range=[0, 100])], crop=[10, 5, 60, 25])
    assert prep.rgb.shape == (20, 50, 3)
    expected = np.clip(arr[5:25, 10:60] / 100.0, 0, 1)
    assert np.allclose(prep.rgb[..., 0], expected) and np.allclose(prep.rgb[..., 1], expected)
    assert prep.record["crop"] == [10, 5, 60, 25] and prep.record["channels"][0]["display_range"] == [0.0, 100.0]


def test_percentile_range_and_gamma(gray8):
    p, arr = gray8
    prep = prepare([Channel(str(p))], gamma=0.5, percentiles=(0, 100))
    lo, hi = prep.record["channels"][0]["display_range"]
    assert (lo, hi) == (0.0, 198.0) and prep.record["gamma"] == 0.5
    assert np.allclose(prep.rgb[0, :, 0], (arr[0] / 198.0) ** 0.5)


def test_two_channels_are_tinted_and_summed(tmp_path):
    a, b = np.full((10, 10), 255, np.uint8), np.zeros((10, 10), np.uint8)
    b[:, 5:] = 255
    Image.fromarray(a).save(tmp_path / "a.png")
    Image.fromarray(b).save(tmp_path / "b.png")
    prep = prepare([Channel(str(tmp_path / "a.png"), "#00ff00", [0, 255]),
                    Channel(str(tmp_path / "b.png"), "#ff00ff", [0, 255])])
    assert prep.rgb[0, 0].tolist() == [0.0, 1.0, 0.0]          # green only
    assert prep.rgb[0, 9].tolist() == [1.0, 1.0, 1.0]          # green + magenta, clipped


def test_errors(gray8, tmp_path):
    p, _ = gray8
    with pytest.raises(ValueError, match="outside the image"):
        prepare([Channel(str(p))], crop=[0, 0, 500, 10])
    rgb = tmp_path / "rgb.png"
    Image.fromarray(np.zeros((5, 5, 3), np.uint8)).save(rgb)
    with pytest.raises(ValueError, match="colour image cannot be combined"):
        prepare([Channel(str(rgb)), Channel(str(p))])


def test_panel_draws_a_scale_bar_of_the_right_length(gray8):
    p, _ = gray8
    images.take()
    fig, ax = plt.subplots()
    try:
        entry = render_image_panel(ax, p, {"pixel_size": 0.5, "pixel_unit": "µm", "scale_bar": 20, "panel": "a"})
        (bar,) = ax.lines
        x = bar.get_xdata()
        assert x[1] - x[0] == pytest.approx(40.0)              # 20 µm / 0.5 µm per px
        assert x[1] == pytest.approx(100 * 0.95)               # lower right, 5% in
        assert [t.get_text() for t in ax.texts] == ["20 µm"]
        assert entry["scale_bar_px"] == 40.0 and images.take() == [entry]
    finally:
        plt.close(fig)


def test_bar_wider_than_the_image_is_an_error(gray8):
    p, _ = gray8
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="wider than"):
            render_image_panel(ax, p, {"pixel_size": 1.0, "scale_bar": 500})
    finally:
        plt.close(fig)
        images.take()


def test_readme_lines_flag_gamma():
    lines = images.readme_lines([{"panel": "b", "crop": None, "gamma": 0.8, "nonlinear": True,
                                  "pixel_size": 0.2, "pixel_unit": "µm", "scale_bar": 10,
                                  "channels": [{"path": "raw_data/x.tif", "dtype": "uint16", "shape": [512, 512],
                                                "label": "DAPI", "color": "#0000ff", "display_range": [100, 4000],
                                                "sha256": "a" * 64}]}])
    assert lines[0] == "## Images"
    assert "gamma 0.8 (nonlinear)" in lines[2] and "scale bar 10 µm" in lines[2]
    assert "display 100-4000" in lines[3] and "sha256 aaaaaaaaaaaa" in lines[3]
