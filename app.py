from flask import Flask, request, jsonify, send_from_directory
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import uuid
import base64
from io import BytesIO

app = Flask(__name__)

# Configuración de Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
FONT_PATH = os.path.join(BASE_DIR, 'Montserrat-Bold.ttf') 

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# Medidas exactas basadas en tus porcentajes (12.5% de 1080 = 135px)
CANVAS_SIZE = 1080
FRAME_H = 135  # 12.5% para el top y para el bottom

def fit_image(img, target_w, target_h):
    """Ajusta la imagen para que llene el 75% central (810px de alto)."""
    img = img.convert("RGB")
    return ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    # Limpiamos el texto de palabras extrañas si n8n las envía
    title = data.get("title", "").upper().replace("SPACER", "").strip()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Crear lienzo base (Negro puro para los frames)
        canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0))

        # 2. Insertar Imagen en el centro (75% = 810px de alto)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        bg_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
        main_img = fit_image(bg_raw, CANVAS_SIZE, 810)
        canvas.paste(main_img, (0, FRAME_H)) # Empezamos después del frame superior

        # 3. Logo (Top Frame - 12.5%)
        if os.path.exists(TEMPLATE_PATH):
            temp_img = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp_img = temp_img.resize((CANVAS_SIZE, CANVAS_SIZE))
            logo_zone = temp_img.crop((0, 0, CANVAS_SIZE, FRAME_H))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 4. Textos (Bottom Frame - 12.5%)
        # Reducimos tamaño para que quepa perfecto en los 135px de abajo
        if os.path.exists(FONT_PATH):
            f_title = ImageFont.truetype(FONT_PATH, 42) # Tamaño más elegante
            f_bullet = ImageFont.truetype(FONT_PATH, 24)
        else:
            return jsonify({"error": "Falta Montserrat-Bold.ttf"}), 500

        draw = ImageDraw.Draw(canvas)
        
        # Posicionamos el título dentro del frame inferior (que empieza en 945px)
        y_text_start = CANVAS_SIZE - FRAME_H + 25
        draw.text((60, y_text_start), title[:50], font=f_title, fill=(255, 255, 255))
        
        # Bullets en una sola línea o muy compactos
        y_bullet = y_text_start + 55
        bullet_list = [str(b).replace("spacer", "").strip() for b in bullets if b and "spacer" not in str(b).lower()]
        
        # Dibujamos solo los primeros 2 bullets para no saturar el 12.5%
        for b in bullet_list[:2]:
            draw.text((60, y_bullet), f"• {b[:70]}", font=f_bullet, fill=(200, 200, 200))
            y_bullet += 35

        # 5. Guardar con máxima nitidez
        filename = f"post_{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(POST_OUTPUT_DIR, filename)
        canvas.save(save_path, "JPEG", quality=100, subsampling=0)
        
        return jsonify({"status": "success", "download_url": f"{request.url_root.rstrip('/')}/post_output/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
