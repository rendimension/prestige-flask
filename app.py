from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import base64
from io import BytesIO

app = Flask(__name__)

# === Configuración de Rutas ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def get_huge_font(size):
    """Intenta cargar fuentes estándar de Linux que Railway suele tener."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        os.path.join(BASE_DIR, 'fonts', 'Montserrat-Bold.ttf') # Tu fuente actual
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default() # Si todo falla, vuelve a la pequeña (pero intentaremos que no pase)

def fit_cover(img, target_size):
    iw, ih = img.size
    tw, th = target_size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img.crop(((nw-tw)//2, (nh-th)//2, (nw+tw)//2, (nh+th)//2))

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "DISEÑO ESTRATÉGICO").upper()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64")

    try:
        # 1. IMAGEN DE FONDO (1080x1080 completo)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        img_data = base64.b64decode(img_b64)
        canvas = Image.open(BytesIO(img_data)).convert("RGB")
        canvas = fit_cover(canvas, (1080, 1080))
        
        # 2. CAPA CREATIVA (Bandas con Opacidad)
        overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        
        # Banda Superior para Logo (Negro 50% opacidad)
        draw_ov.rectangle([0, 0, 1080, 180], fill=(0, 0, 0, 128))
        # Banda Inferior para Texto (Negro 75% opacidad)
        draw_ov.rectangle([0, 700, 1080, 1080], fill=(0, 0, 0, 190))
        
        canvas.paste(overlay, (0, 0), overlay)

        # 3. LOGO (Template transparente encima)
        if os.path.exists(TEMPLATE_PATH):
            logo = Image.open(TEMPLATE_PATH).convert("RGBA")
            logo = logo.resize((1080, 1080))
            canvas.paste(logo, (0, 0), logo)

        # 4. TEXTO GIGANTE (Obedeciendo el setting)
        draw = ImageDraw.Draw(canvas)
        # Usamos fuentes que el sistema Linux sí reconoce
        f_title = get_huge_font(85) 
        f_bullet = get_huge_font(45)

        # Título
        draw.text((80, 735), title[:40], font=f_title, fill=(255, 255, 255))
        
        # Bullets
        y = 840
        for b in bullets:
            if b and "spacer" not in b.lower():
                draw.text((80, y), f"• {b[:55]}", font=f_bullet, fill=(255, 255, 255))
                y += 65

        # 5. Guardar
        fname = f"post_{uuid.uuid4().hex}.jpg"
        canvas.save(os.path.join(POST_OUTPUT_DIR, fname), "JPEG", quality=95)
        
        return jsonify({"status": "success", "download_url": f"{request.url_root.rstrip('/')}/post_output/{fname}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
