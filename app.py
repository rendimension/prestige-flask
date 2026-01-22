from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import sys
import base64
from io import BytesIO
from urllib.parse import urlparse

print("🧠 Python executable in use:", sys.executable)

app = Flask(__name__)

# === Paths (Railway compatible) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_IMAGE_DIR = os.path.join(BASE_DIR, 'post_image')
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
FONT_BOLD_PATH = os.path.join(BASE_DIR, 'fonts', 'Montserrat-Bold.ttf')
FONT_REG_PATH = os.path.join(BASE_DIR, 'fonts', 'Montserrat-Regular.ttf')

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)


# === Utils ===
def clear_folder(folder_path: str):
    if not os.path.isdir(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return
    for name in os.listdir(folder_path):
        try:
            os.remove(os.path.join(folder_path, name))
        except Exception:
            pass


def _ext_from_content_type(ct: str) -> str:
    ct = (ct or '').split(';')[0].strip().lower()
    mapping = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
    }
    return mapping.get(ct, '.jpg')


def _pick_ext(url: str, response) -> str:
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
        return '.jpg' if ext == '.jpeg' else ext
    return _ext_from_content_type(response.headers.get('Content-Type', ''))


def download_image_to_folder(image_url: str, save_folder: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
    }
    resp = requests.get(image_url, headers=headers, timeout=30)
    resp.raise_for_status()
    ext = _pick_ext(image_url, resp)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(save_folder, filename)
    with open(path, 'wb') as f:
        f.write(resp.content)
    return path


def save_base64_image(base64_string: str, save_folder: str) -> str:
    if ',' in base64_string:
        base64_string = base64_string.split(',', 1)[1]
    image_data = base64.b64decode(base64_string)
    img = Image.open(BytesIO(image_data))
    ext = '.png' if img.format == 'PNG' else '.jpg'
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(save_folder, filename)
    if ext == '.jpg' and img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.save(path, format='PNG' if ext == '.png' else 'JPEG', quality=95)
    return path


def load_font(path: str, size: int, fallback_bold: str = None):
    try:
        return ImageFont.truetype(path, size=size)
    except Exception:
        if fallback_bold and path != fallback_bold:
            try:
                return ImageFont.truetype(fallback_bold, size=size)
            except Exception:
                return ImageFont.load_default()
        return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw):
    words = (text or "").split()
    if not words:
        return []
    lines, line = [], ""
    for w in words:
        candidate = (line + " " + w).strip()
        if draw.textlength(candidate, font=font) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def fit_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    iw, ih = img.size
    if iw == 0 or ih == 0:
        return Image.new("RGB", (target_w, target_h), (0, 0, 0))
    scale = max(target_w / iw, target_h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - target_w) // 2)
    top = max(0, (nh - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


# =============================================================================
# LAYOUT CONSTANTS - AJUSTADOS PARA MEJOR PROPORCIÓN
# =============================================================================
CANVAS_W, CANVAS_H = 1080, 1080

SAFE_PADDING = 80
HEADER_H = 130      # Altura del logo
TEXT_BAND_H = 320   # Reducido de 380 para dar más espacio a la foto

# Área de la imagen más grande
IMG_AREA_Y = HEADER_H
IMG_AREA_H = CANVAS_H - HEADER_H - 280 
IMG_AREA_X = 0
IMG_AREA_W = CANVAS_W

# =============================================================================
# TEXT STYLES - AJUSTADOS PARA LEGIBILIDAD (MÁS GRANDES)
# =============================================================================
TITLE_SIZE = 85      # Subido de 64 para que destaque
BULLET_SIZE = 46     # Subido de 34 para que sea legible en móviles
PADDING_X = SAFE_PADDING
TITLE_TOP_PAD = 40
LINE_SP = 14
BULLET_GAP = 18
TEXT_COLOR = (255, 255, 255)

TEXT_BAND_OVERLAY = True
BAND_ALPHA = 220     # Un poco más oscuro para resaltar el texto


def draw_text_section(canvas: Image.Image, title: str, bullets: list):
    # Limpieza para evitar que aparezca la palabra "spacer" de n8n
    title = title.replace('spacer', '').strip()
    
    draw = ImageDraw.Draw(canvas)
    font_title = load_font(FONT_BOLD_PATH, TITLE_SIZE, fallback_bold=FONT_BOLD_PATH)
    font_bullet = load_font(FONT_REG_PATH, BULLET_SIZE, fallback_bold=FONT_BOLD_PATH)

    band_y = CANVAS_H - TEXT_BAND_H
    band_rect = (0, band_y, CANVAS_W, CANVAS_H)

    if TEXT_BAND_OVERLAY:
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.rectangle(band_rect, fill=(0, 0, 0, BAND_ALPHA))
        canvas_alpha = canvas.convert("RGBA")
        canvas_rgba = Image.alpha_composite(canvas_alpha, overlay)
        canvas.paste(canvas_rgba.convert("RGB"))

    draw = ImageDraw.Draw(canvas)
    max_w = CANVAS_W - 2 * PADDING_X

    # === TITLE ===
    title_lines = wrap_text(title or "", font_title, max_w, draw)
    line_h_title = font_title.getbbox("Ag")[3] - font_title.getbbox("Ag")[1] + LINE_SP
    y = band_y + TITLE_TOP_PAD
    
    for line in title_lines:
        draw.text((PADDING_X, y), line, font=font_title, fill=TEXT_COLOR)
        y += line_h_title

    # === BULLETS ===
    bullet_items = [b for b in (bullets or []) if (b or "").strip()]
    y += 15
    bullet_prefix = "• "
    line_h_bullet = font_bullet.getbbox("Ag")[3] - font_bullet.getbbox("Ag")[1] + BULLET_GAP

    for b in bullet_items:
        clean_bullet = b.replace('spacer', '').strip()
        if not clean_bullet: continue
        
        wrapped = wrap_text(clean_bullet, font_bullet, max_w - int(draw.textlength(bullet_prefix, font=font_bullet)), draw)
        if not wrapped: continue

        draw.text((PADDING_X, y), bullet_prefix + wrapped[0], font=font_bullet, fill=TEXT_COLOR)
        y += line_h_bullet

        indent_x = PADDING_X + int(draw.textlength(bullet_prefix, font=font_bullet))
        for cont in wrapped[1:]:
            draw.text((indent_x, y), cont, font=font_bullet, fill=TEXT_COLOR)
            y += line_h_bullet


# === Routes ===
@app.route("/")
def home():
    return jsonify({"service": "Prestige 360 Optimized Generator", "status": "running"})

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

@app.route("/generate-post", methods=["POST"])
def generate_post():
    payload = request.get_json(silent=True)
    if isinstance(payload, list) and payload: payload = payload[0]
    if not isinstance(payload, dict): return jsonify({"error": "Expected JSON"}), 400

    image_url = payload.get("image_url") or payload.get("image")
    image_base64 = payload.get("image_base64") or payload.get("base64")
    title = payload.get("title", "").strip()
    bullets = [payload.get("bullet1"), payload.get("bullet2"), payload.get("bullet3")]

    if not image_url and not image_base64: return jsonify({"error": "Missing image"}), 400
    if not os.path.isfile(TEMPLATE_PATH): return jsonify({"error": "Template missing"}), 500

    clear_folder(POST_IMAGE_DIR)
    
    try:
        if image_base64:
            downloaded_path = save_base64_image(image_base64, POST_IMAGE_DIR)
        else:
            downloaded_path = download_image_to_folder(image_url, POST_IMAGE_DIR)
            
        template = Image.open(TEMPLATE_PATH).convert("RGB")
        if template.size != (CANVAS_W, CANVAS_H):
            template = template.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)
        
        with Image.open(downloaded_path) as src:
            src = src.convert("RGB")
            area = fit_cover(src, IMG_AREA_W, IMG_AREA_H)
            template.paste(area, (IMG_AREA_X, IMG_AREA_Y))

        draw_text_section(template, title, bullets)

        filename = f"post_{uuid.uuid4().hex}.jpg"
        out_path = os.path.join(POST_OUTPUT_DIR, filename)
        template.save(out_path, format="JPEG", quality=95)

        return jsonify({
            "status": "success",
            "download_url": f"{request.url_root.rstrip('/')}/post_output/{filename}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
