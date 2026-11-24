"""Day-0 spike: offline OCR accuracy and CPU latency on a 1080p screenshot."""

import time

from PIL import Image, ImageDraw, ImageFont

from omoide.ocr import RapidOcrEngine

LINES = ("CUDA out of memory", "invoice total 99381")


def main() -> None:
    image = Image.new("RGB", (1920, 1080), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    for index, line in enumerate(LINES):
        draw.text((80, 80 + index * 90), line, font=font, fill="black")

    engine = RapidOcrEngine()
    started = time.perf_counter()
    result = engine.recognize(image)
    print("first call (model load):", round((time.perf_counter() - started) * 1000), "ms")

    samples = []
    for _ in range(5):
        started = time.perf_counter()
        result = engine.recognize(image)
        samples.append(round((time.perf_counter() - started) * 1000))
    print("expected:", LINES)
    print("recognized:", result)
    print("warm samples (ms):", samples)
    print("warm median (ms):", sorted(samples)[len(samples) // 2])


if __name__ == "__main__":
    main()
