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

# === REGLA DE PROPORCIONES (12.5% de 1080 = 135px) ===
CANVAS_SIZE = 1080
FRAME_H = 135  # Franja superior e inferior
IMG_H = 810    # 75% central para la imagen

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    # Limpiar textos de palabras no deseadas
    title = data.get("title", "").upper().replace("STRATEGIC", "").replace("SUCCESS", "").strip()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Crear lienzo negro (Marcos perfectos)
        canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0))

        # 2. Insertar Imagen IA en el centro exacto (75%)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        bg_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
        main_img = ImageOps.fit(bg_raw, (CANVAS_SIZE, IMG_H), method=Image.Resampling.LANCZOS)
        canvas.paste(main_img, (0, FRAME_H))

        # 3. Logo (Top 12.5%)
        if os.path.exists(TEMPLATE_PATH):
            temp_img = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp_img = temp_img.resize((CANVAS_SIZE, CANVAS_SIZE))
            logo_zone = temp_img.crop((0, 0, CANVAS_SIZE, FRAME_H))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 4. Texto Minimalista (Bottom 12.5%)
        if os.path.exists(FONT_PATH):
            # Reducción drástica para evitar que sea invasivo
            f_title = ImageFont.truetype(FONT_PATH, 32) 
            f_bullet = ImageFont.truetype(FONT_PATH, 22)
        else:
            return jsonify({"error": "Falta Montserrat-Bold.ttf"}), 500

        draw = ImageDraw.Draw(canvas)
        
        # Posicionamiento centrado verticalmente en la banda inferior (inicia en 945px)
        y_start = 945 + 20 
        draw.text((80, y_start), title[:50], font=f_title, fill=(255, 255, 255))
        
        # Bullets pequeños y elegantes
        y_bullet = y_start + 45
        for b in bullets:
            if b and "spacer" not in str(b).lower():
                clean_b = str(b).replace("•", "").strip()[:65]
                draw.text((80, y_bullet), f"• {clean_b}", font=f_bullet, fill=(180, 180, 180))
                y_bullet += 30 # Espaciado compacto

        # 5. Exportar
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
