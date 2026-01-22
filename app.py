from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import sys
import base64
from io import BytesIO
from urllib.parse import urlparse

app = Flask(__name__)

# === Paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_IMAGE_DIR = os.path.join(BASE_DIR, 'post_image')
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
FONT_BOLD_PATH = os.path.join(BASE_DIR, 'fonts', 'Montserrat-Bold.ttf')
FONT_REG_PATH = os.path.join(BASE_DIR, 'fonts', 'Montserrat-Regular.ttf')

os.makedirs(POST_IMAGE_DIR, exist_ok=True)
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def clear_folder(folder_path):
    for name in os.listdir(folder_path):
        try: os.remove(os.path.join(folder_path, name))
        except: pass

def download_image(url, folder):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    filename = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(folder, filename)
    with open(path, 'wb') as f: f.write(resp.content)
    return path

def save_base64(b64, folder):
    if ',' in b64: b64 = b64.split(',', 1)[1]
    data = base64.b64decode(b64)
    img = Image.open(BytesIO(data)).convert("RGB")
    path = os.path.join(folder, f"{uuid.uuid4().hex}.jpg")
    img.save(path, "JPEG")
    return path

def fit_cover(img, target_w, target_h):
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img.crop(((nw-target_w)//2, (nh-target_h)//2, (nw+target_w)//2, (nh+target_h)//2))

# === CONFIGURACIÓN DE DISEÑO CORREGIDA ===
CANVAS_W, CANVAS_H = 1080, 1080
HEADER_H = 130      # Espacio para el logo
TEXT_BAND_H = 340   # Altura de la banda negra (reducida)
SAFE_PAD = 70       # Margen lateral

# Tamaños de fuente MASIVOS para legibilidad
TITLE_SIZE = 82     
BULLET_SIZE = 44    

def draw_text_section(canvas, title, bullets):
    draw = ImageDraw.Draw(canvas)
    # Cargar fuentes o usar default si fallan
    try:
        f_title = ImageFont.truetype(FONT_BOLD_PATH, TITLE_SIZE)
        f_bullet = ImageFont.truetype(FONT_REG_PATH, BULLET_SIZE)
    except:
        f_title = f_bullet = ImageFont.load_default()

    y_start = CANVAS_H - TEXT_BAND_H + 40
    
    # Dibujar Título
    draw.text((SAFE_PAD, y_start), title.upper()[:45], font=f_title, fill=(255,255,255))
    
    # Dibujar Bullets (Corrigiendo el símbolo extraño)
    y_current = y_start + 100
    for b in bullets:
        if b and str(b).strip():
            clean_txt = str(b).replace('spacer','').strip()
            draw.text((SAFE_PAD, y_current), f"- {clean_txt[:50]}", font=f_bullet, fill=(255,255,255))
            y_current += 65

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "DISEÑO COMERCIAL")
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64")
    img_url = data.get("image_url")

    clear_folder(POST_IMAGE_DIR)
    
    try:
        # 1. Obtener imagen de fondo
        path = save_base64(img_b64, POST_IMAGE_DIR) if img_b64 else download_image(img_url, POST_IMAGE_DIR)
        
        # 2. Preparar el canvas (Template)
        template = Image.open(TEMPLATE_PATH).convert("RGB").resize((CANVAS_W, CANVAS_H))
        
        # 3. Pegar la foto del proyecto (ajustada al centro)
        with Image.open(path) as photo:
            photo_area = fit_cover(photo, CANVAS_W, CANVAS_H - HEADER_H - TEXT_BAND_H)
            template.paste(photo_area, (0, HEADER_H))

        # 4. Dibujar la banda negra y el texto
        overlay = Image.new("RGBA", (CANVAS_W, TEXT_BAND_H), (0, 0, 0, 230))
        template.paste(overlay, (0, CANVAS_H - TEXT_BAND_H), overlay)
        draw_text_section(template, title, bullets)

        # 5. Guardar
        fname = f"post_{uuid.uuid4().hex}.jpg"
        template.save(os.path.join(POST_OUTPUT_DIR, fname), "JPEG", quality=95)
        
        return jsonify({"status": "success", "download_url": f"{request.url_root.rstrip('/')}/post_output/{fname}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
