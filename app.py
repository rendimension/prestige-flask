from flask import Flask, request, jsonify, send_from_directory
import os
from PIL import Image, ImageDraw, ImageFont
import uuid
import base64
from io import BytesIO

app = Flask(__name__)

# Configuración de Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
# NOMBRE EXACTO DE TU FUENTE SUBIDA
FONT_PATH = os.path.join(BASE_DIR, 'Montserrat-VariableFont_wght.ttf') 

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def fit_image_to_canvas(img, size=(1080, 1080)):
    """Ajusta la imagen para que llene todo el cuadro sin dejar espacios negros."""
    img = img.convert("RGB")
    iw, ih = img.size
    target_w, target_h = size
    scale = max(target_w / iw, target_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img.crop(((nw - target_w) // 2, (nh - target_h) // 2, (nw + target_w) // 2, (nh + target_h) // 2))

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "PROYECTO PRESTIGE").upper()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Fondo: Imagen de la IA (1080x1080)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        img_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
        canvas = fit_image_to_canvas(img_raw)

        # 2. Capa Creativa: Bandas negras translúcidas
        overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Banda superior (Logo) - Opacidad 55%
        draw_ov.rectangle([0, 0, 1080, 180], fill=(0, 0, 0, 140))
        # Banda inferior (Texto) - Opacidad 80%
        draw_ov.rectangle([0, 700, 1080, 1080], fill=(0, 0, 0, 204))
        canvas.paste(overlay, (0, 0), overlay)

        # 3. Logo (Template) - Pegamos solo la parte superior para no tapar el fondo
        if os.path.exists(TEMPLATE_PATH):
            temp_img = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp_img = temp_img.resize((1080, 1080))
            # Recortamos la zona del logo
            logo_zone = temp_img.crop((0, 0, 1080, 180))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 4. Textos con la FUENTE MONTSERRAT que subiste
        if os.path.exists(FONT_PATH):
            f_title = ImageFont.truetype(FONT_PATH, 75)
            f_bullet = ImageFont.truetype(FONT_PATH, 42)
        else:
            return jsonify({"error": f"No se encontro la fuente en {FONT_PATH}"}), 500

        draw = ImageDraw.Draw(canvas)
        # Dibujar Título
        draw.text((80, 730), title[:40], font=f_title, fill=(255, 255, 255))
        
        # Dibujar Bullets
        y_pos = 835
        for b in bullets:
            if b and "spacer" not in str(b).lower():
                draw.text((80, y_pos), f"• {str(b).strip()[:55]}", font=f_bullet, fill=(245, 245, 245))
                y_pos += 65

        # 5. Guardar y Enviar
        filename = f"post_{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(POST_OUTPUT_DIR, filename)
        canvas.save(save_path, "JPEG", quality=95)
        
        return jsonify({"status": "success", "download_url": f"{request.url_root.rstrip('/')}/post_output/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
