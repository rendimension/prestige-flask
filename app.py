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
# Intentamos cargar la fuente desde tu carpeta local en GitHub
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'Montserrat-Bold.ttf')

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def get_font(size):
    """Carga la fuente Montserrat o una del sistema que permita escalar tamaño."""
    try:
        if os.path.exists(FONT_PATH):
            return ImageFont.truetype(FONT_PATH, size)
        # Rutas comunes en servidores Linux (Railway)
        for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
                  "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    except:
        pass
    return ImageFont.load_default()

def resize_to_fill(img, target_size=(1080, 1080)):
    """Ajusta la imagen para que llene todo el 1080x1080 sin dejar bandas negras."""
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
    
    title = data.get("title", "DISEÑO COMERCIAL").upper()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64")

    try:
        # 1. Crear el Fondo con la imagen de la IA (1080x1080)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        img_data = base64.b64decode(img_b64)
        bg_image = Image.open(BytesIO(img_data)).convert("RGB")
        canvas = resize_to_fill(bg_image)

        # 2. Crear Capa Creativa de Bandas (RGBA para transparencia)
        overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        
        # Banda superior (Logo) - Opacidad 50%
        draw_ov.rectangle([0, 0, 1080, 180], fill=(0, 0, 0, 130))
        # Banda inferior (Texto) - Opacidad 75%
        draw_ov.rectangle([0, 700, 1080, 1080], fill=(0, 0, 0, 190))
        
        # Unir bandas con la imagen
        canvas.paste(overlay, (0, 0), overlay)

        # 3. Pegar el Template (Logo Prestige 360)
        if os.path.exists(TEMPLATE_PATH):
            template = Image.open(TEMPLATE_PATH).convert("RGBA")
            template = template.resize((1080, 1080))
            canvas.paste(template, (0, 0), template)

        # 4. Dibujar Textos (GIGANTES para legibilidad)
        draw = ImageDraw.Draw(canvas)
        f_title = get_font(75) 
        f_bullet = get_font(42)

        # Título
        draw.text((80, 740), title[:45], font=f_title, fill=(255, 255, 255))
        
        # Bullets (Cambiamos el símbolo para evitar errores de renderizado)
        y = 840
        for b in bullets:
            if b and "spacer" not in str(b).lower():
                clean_text = str(b).strip()
                draw.text((80, y), f"- {clean_text[:55]}", font=f_bullet, fill=(255, 255, 255))
                y += 65

        # 5. Guardar
        fname = f"post_{uuid.uuid4().hex}.jpg"
        out_path = os.path.join(POST_OUTPUT_DIR, fname)
        canvas.save(out_path, "JPEG", quality=95)
        
        return jsonify({"status": "success", "download_url": f"{request.url_root.rstrip('/')}/post_output/{fname}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
