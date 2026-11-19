"""Захват кадров с камеры через OpenCV.

Модуль намеренно не зависит от распознавания/перевода — только камера.
OpenCV импортируется лениво, чтобы тесты и CLI без AR работали без него.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_INDEX = 0


class CameraError(RuntimeError):
    """Ошибка работы с камерой."""


class Camera:
    """Обёртка над `cv2.VideoCapture`.

    Пример:
        cam = Camera(index=0)
        cam.open()
        frame = cam.read()   # numpy.ndarray (H, W, 3) в BGR
        cam.release()
    """

    def __init__(
        self,
        index: int = DEFAULT_INDEX,
        width: Optional[int] = None,
        height: Optional[int] = None,
        capture: Optional[Any] = None,
    ) -> None:
        if index < 0:
            raise ValueError("index камеры должен быть >= 0")
        self.index = index
        self.width = width
        self.height = height
        self._capture = capture
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened

    def _ensure_cv2(self) -> Any:
        try:
            import cv2  # локальный импорт: тесты могут мокать
        except ImportError as exc:  # pragma: no cover
            raise CameraError(
                "opencv-python не установлен. Установите: pip install opencv-python"
            ) from exc
        return cv2

    def open(self) -> None:
        """Открыть камеру. Бросает CameraError, если устройство недоступно."""
        if self._opened:
            raise CameraError("Камера уже открыта")

        if self._capture is None:
            cv2 = self._ensure_cv2()
            self._capture = cv2.VideoCapture(self.index)

        if not self._capture.isOpened():
            self._capture = None
            raise CameraError(f"Не удалось открыть камеру с индексом {self.index}")

        if self.width is not None:
            self._capture.set(3, self.width)  # cv2.CAP_PROP_FRAME_WIDTH
        if self.height is not None:
            self._capture.set(4, self.height)  # cv2.CAP_PROP_FRAME_HEIGHT

        self._opened = True
        logger.info(
            "Камера открыта: index=%s, width=%s, height=%s",
            self.index,
            self.width,
            self.height,
        )

    def read(self) -> Any:
        """Прочитать один кадр. Возвращает numpy.ndarray (BGR)."""
        if not self._opened or self._capture is None:
            raise CameraError("Камера не открыта")

        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraError("Не удалось прочитать кадр")
        return frame

    def release(self) -> None:
        """Закрыть камеру. Идемпотентно."""
        if self._capture is not None:
            try:
                self._capture.release()
            finally:
                self._capture = None
        self._opened = False
        logger.info("Камера закрыта: index=%s", self.index)

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.release()
