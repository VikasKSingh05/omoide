"""Generate the Windows icon used by the installer and executable."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets" / "icon.ico"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((16, 16, 240, 240), radius=56, fill=(72, 94, 172, 255))
try:
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 150)
except OSError:
    font = ImageFont.load_default()
draw.text((88, 42), "O", font=font, fill=(245, 246, 250, 255))
image.save(OUTPUT, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(OUTPUT)
