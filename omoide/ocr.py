"""Local OCR. RapidOCR bundles its models, so nothing is uploaded or downloaded."""

from __future__ import annotations

from typing import Protocol

from PIL import Image


class OcrEngine(Protocol):
    def recognize(self, image: Image.Image) -> str: ...


class NoopOcrEngine:
    def recognize(self, image: Image.Image) -> str:
        return ""


class FakeOcrEngine:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def recognize(self, image: Image.Image) -> str:
        return self.text


class RapidOcrEngine:
    """Lazy-loaded so startup stays fast for users who only copy text."""

    def __init__(self) -> None:
        self._engine: object | None = None

    @property
    def engine(self) -> object:
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            # The package default (limit_type='min', 736) upscales small images
            # enormously. 'max' caps the long side and keeps CPU inference fast.
            self._engine = RapidOCR(
                use_angle_cls=False,
                det_model_path=None,
                det_limit_type="max",
                det_limit_side_len=960,
            )
        return self._engine

    def recognize(self, image: Image.Image) -> str:
        import numpy as np

        array = np.array(image.convert("RGB"))
        result, _ = self.engine(array)  # type: ignore[operator]
        if not result:
            return ""
        texts: list[str] = []
        for item in result:
            if isinstance(item, dict):
                value = item.get("text") or item.get("rec_text") or ""
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                value = item[1]
            else:
                value = ""
            if isinstance(value, str) and value.strip():
                texts.append(value.strip())
        return " ".join(texts)
