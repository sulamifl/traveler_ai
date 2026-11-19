"""Тесты overlay. OpenCV не требуется — используется мок cv2."""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from translator.ar.describe import DescribedBlock
from translator.ar.overlay import OverlayError, OverlayRenderer, OverlayStyle


def _make_fake_cv2() -> types.ModuleType:
    module = types.ModuleType("cv2")
    module.FONT_HERSHEY_SIMPLEX = 0
    module.LINE_AA = 16

    calls: dict[str, list] = {"rectangle": [], "putText": [], "getTextSize": []}

    def rectangle(img, pt1, pt2, color, thickness):
        calls["rectangle"].append((pt1, pt2, color, thickness))
        return img

    def putText(img, text, org, font, scale, color, thickness, line_type):
        calls["putText"].append((text, org, color))
        return img

    def getTextSize(text, font, scale, thickness):
        calls["getTextSize"].append((text, font, scale, thickness))
        return (len(text) * 8, 12), 3

    module.rectangle = rectangle
    module.putText = putText
    module.getTextSize = getTextSize
    module._calls = calls  # type: ignore[attr-defined]
    return module


def _frame() -> np.ndarray:
    return np.zeros((100, 100, 3), dtype=np.uint8)


def _block(text: str = "Hello", x: int = 10, y: int = 20) -> DescribedBlock:
    return DescribedBlock(
        original_text="orig",
        translated_text=text,
        bbox=(x, y, 30, 15),
        confidence=90.0,
    )


def test_render_draws_rectangle_and_text(monkeypatch):
    fake = _make_fake_cv2()
    monkeypatch.setitem(sys.modules, "cv2", fake)

    renderer = OverlayRenderer()
    out = renderer.render(_frame(), [_block("Hello")])

    assert out.shape == (100, 100, 3)
    assert len(fake._calls["rectangle"]) == 2  # рамка + фон подписи
    assert len(fake._calls["putText"]) == 1
    assert fake._calls["putText"][0][0] == "Hello"


def test_render_empty_blocks_returns_copy(monkeypatch):
    fake = _make_fake_cv2()
    monkeypatch.setitem(sys.modules, "cv2", fake)

    frame = _frame()
    renderer = OverlayRenderer()
    out = renderer.render(frame, [])
    assert out is not frame
    assert fake._calls["rectangle"] == []


def test_render_copy_false_mutates_in_place(monkeypatch):
    fake = _make_fake_cv2()
    monkeypatch.setitem(sys.modules, "cv2", fake)

    frame = _frame()
    renderer = OverlayRenderer()
    out = renderer.render(frame, [_block()], copy=False)
    assert out is frame


def test_render_none_frame_raises():
    renderer = OverlayRenderer()
    with pytest.raises(OverlayError):
        renderer.render(None, [])


def test_missing_cv2_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "cv2":
            raise ImportError("no cv2")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    renderer = OverlayRenderer()
    with pytest.raises(OverlayError):
        renderer.render(_frame(), [])


def test_custom_style_applied(monkeypatch):
    fake = _make_fake_cv2()
    monkeypatch.setitem(sys.modules, "cv2", fake)

    style = OverlayStyle(box_color=(1, 2, 3), thickness=5)
    renderer = OverlayRenderer(style=style)
    renderer.render(_frame(), [_block()])

    first_rect = fake._calls["rectangle"][0]
    assert first_rect[2] == (1, 2, 3)
    assert first_rect[3] == 5


def test_empty_text_skips_label(monkeypatch):
    fake = _make_fake_cv2()
    monkeypatch.setitem(sys.modules, "cv2", fake)

    renderer = OverlayRenderer()
    renderer.render(_frame(), [_block(text="")])
    assert fake._calls["putText"] == []
