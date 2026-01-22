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

# === GEOMETRÍA DEL POST (1080x1080) ===
# 12.5% de 1080 = 135px
TOP_FRAME = 135
BOTTOM_FRAME = 135
IMAGE_HEIGHT = 810 # El 75% central

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    # Limpieza de textos (evitar palabras de sistema)
    title = data.get("title", "").upper().replace("STRATEGIC", "").replace("SUCCESS", "").strip()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Crear lienzo NEGRO absoluto
        canvas = Image.new("RGB", (1080, 1080), (0, 0, 0))

        # 2. Pegar IMAGEN en el centro (75%)
        if img_b64:
            if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
            img_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
            # Forzamos el tamaño al 75% del alto
            main_img = ImageOps.fit(img_raw, (1080, IMAGE_HEIGHT), method=Image.Resampling.LANCZOS)
            canvas.paste(main_img, (0, TOP_FRAME))

        # 3. Pegar LOGO en el top (12.5%)
        if os.path.exists(TEMPLATE_PATH):
            temp = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp = temp.resize((1080, 1080))
            logo_crop = temp.crop((0, 0, 1080, TOP_FRAME))
            canvas.paste(logo_crop, (0, 0), logo_crop)

        # 4. Escribir TEXTO en el bottom (12.5%)
        if os.path.exists(FONT_PATH):
            f_title = ImageFont.truetype(FONT_PATH, 35) # Tamaño elegante, no invasivo
            f_bullet = ImageFont.truetype(FONT_PATH, 22) # Tamaño lectura
        else:
            return jsonify({"error": "No se detecta Montserrat-Bold.ttf"}), 500

        draw = ImageDraw.Draw(canvas)
        
        # El área de texto empieza en 945px (1080 - 135)
        text_y = 945 + 25 
        
        # Título
        draw.text((70, text_y), title[:55], font=f_title, fill=(255, 255, 255))
        
        # Bullets (Máximo 2 para que no se vea amontonado)
        y_bullet = text_y + 45
        for b in bullets[:2]:
            if b and "spacer" not in str(b).lower():
                clean_b = str(b).replace("•", "").strip()[:70]
                draw.text((70, y_bullet), f"• {clean_b}", font=f_bullet, fill=(200, 200, 200))
                y_bullet += 30

        # 5. Guardar
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
