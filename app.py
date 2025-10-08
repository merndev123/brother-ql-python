import os
import io
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Brother QL Label Printer")

# Configuration via environment variables
PRINTER = os.environ.get("PRINTER")  # e.g. tcp://192.0.2.10:9100
API_KEY = os.environ.get("API_KEY")  # if set, the POST /print endpoint requires this key in header x-api-key
MODEL = os.environ.get("MODEL", "QL-1060N")
LABEL = os.environ.get("LABEL", "102x152")

# Default image size (pixels) for a 4x6 label at ~300dpi (approx from your example)
DEFAULT_SIZE = (1164, 1660)


def _load_font(size: int):
    # Try common system fonts; fall back to PIL default
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


class PrintRequest(BaseModel):
    text: str
    font_size: Optional[int] = 60
    width: Optional[int] = None
    height: Optional[int] = None
    label: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok", "printer_configured": bool(PRINTER)}

def _require_api_key(request: Request):
    """Dependency to require the API key header if API_KEY is configured."""
    if not API_KEY:
        return
    header_key = request.headers.get("x-api-key")
    if not header_key or header_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.post("/print")
async def print_label(req: PrintRequest, _=Depends(_require_api_key)):
    if not PRINTER:
        raise HTTPException(status_code=400, detail="PRINTER environment variable is not set")

    width = req.width or DEFAULT_SIZE[0]
    height = req.height or DEFAULT_SIZE[1]
    label = req.label or LABEL

    # Create image
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    font = _load_font(req.font_size)

    # naive center-ish positioning
    text_x = width // 10
    text_y = height // 2 - req.font_size // 2
    draw.text((text_x, text_y), req.text, fill="black", font=font)

    # Save to an in-memory PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # Save a local copy (optional) for debugging - comment out if not wanted
    local_copy = os.environ.get("SAVE_LOCAL_COPY", "1")
    if local_copy == "1":
        try:
            os.makedirs("/tmp", exist_ok=True)
            with open("/tmp/last_label.png", "wb") as f:
                f.write(buf.getvalue())
        except Exception:
            # ignore write errors on platforms without /tmp
            pass

    # Convert and send to Brother QL
    try:
        qlr = BrotherQLRaster(MODEL)
        instructions = convert(
            qlr=qlr,
            images=[buf],
            label=label,
            rotate="auto",
            compress=True,
            hq=True,
            cut=True,
        )

        # send expects pointer to a device. For network printing pass the printer URI
        # e.g. PRINTER=tcp://1.2.3.4:9100
        send(instructions, PRINTER, "network")
    except Exception as e:
        logger.exception("Failed to send to printer")
        raise HTTPException(status_code=500, detail=f"Printer error: {e}")

    return {"status": "sent", "printer": PRINTER}
