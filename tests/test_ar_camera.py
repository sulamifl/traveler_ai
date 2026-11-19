"""Тесты захвата кадров с камеры. OpenCV не требуется — используется мок."""

from __future__ import annotations

import types

import numpy as np
import pytest

from translator.ar.camera import Camera, CameraError


class _FakeCapture:
    def __init__(self, opened: bool = True, frame=None):
        self._opened = opened
        self._frame = frame if frame is not None else np.zeros((4, 4, 3), dtype=np.uint8)
        self.released = False
        self.settings: list[tuple[int, float]] = []

    def isOpened(self) -> bool:  # noqa: N802
        return self._opened

    def read(self):
        if not self._opened:
            return False, None
        return True, self._frame

    def set(self, prop: int, value: float) -> bool:
        self.settings.append((prop, value))
        return True

    def release(self) -> None:
        self.released = True
        self._opened = False


def test_open_read_release():
    cap = _FakeCapture()
    cam = Camera(index=0, capture=cap)
    cam.open()
    assert cam.is_opened
    frame = cam.read()
    assert frame.shape == (4, 4, 3)
    cam.release()
    assert not cam.is_opened
    assert cap.released


def test_open_fails_when_capture_not_opened():
    cap = _FakeCapture(opened=False)
    cam = Camera(capture=cap)
    with pytest.raises(CameraError):
        cam.open()


def test_read_without_open_raises():
    cam = Camera(capture=_FakeCapture())
    with pytest.raises(CameraError):
        cam.read()


def test_double_open_raises():
    cam = Camera(capture=_FakeCapture())
    cam.open()
    with pytest.raises(CameraError):
        cam.open()


def test_release_idempotent():
    cam = Camera(capture=_FakeCapture())
    cam.open()
    cam.release()
    cam.release()  # не должно падать


def test_invalid_index():
    with pytest.raises(ValueError):
        Camera(index=-1)


def test_width_height_applied():
    cap = _FakeCapture()
    cam = Camera(capture=cap, width=640, height=480)
    cam.open()
    assert (3, 640) in cap.settings
    assert (4, 480) in cap.settings


def test_context_manager():
    cap = _FakeCapture()
    with Camera(capture=cap) as cam:
        assert cam.is_opened
    assert not cam.is_opened
    assert cap.released


def test_missing_cv2_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "cv2":
            raise ImportError("no cv2")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    cam = Camera()
    with pytest.raises(CameraError):
        cam.open()
