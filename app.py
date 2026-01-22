from flask import Flask, request, jsonify, send_from_directory
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import uuid
import base64
from io import BytesIO

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
FONT_PATH = os.path.join(BASE_DIR, 'Montserrat-Bold.ttf') 

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# === GEOMETRÍA ESTRICTA 12.5% - 75% - 12.5% ===
CANVAS_SIZE = 1080
FRAME_H = 135  
IMG_H = 810    

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    # Limpieza de texto
    title = data.get("title", "").upper().replace("STRATEGIC", "").replace("SUCCESS", "").strip()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Crear lienzo negro
        canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0))

        # 2. Imagen Central (75%)
        if img_b64:
            if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
            img_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
            main_img = ImageOps.fit(img_raw, (CANVAS_SIZE, IMG_H), method=Image.Resampling.LANCZOS)
            canvas.paste(main_img, (0, FRAME_H))

        # 3. Logo/Top Frame
        if os.path.exists(TEMPLATE_PATH):
            temp = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp = temp.resize((CANVAS_SIZE, CANVAS_SIZE))
            logo_zone = temp.crop((0, 0, CANVAS_SIZE, FRAME_H))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 4. Texto Ultra-Minimalista (Bottom Frame)
        if os.path.exists(FONT_PATH):
            # TAMAÑOS SOLICITADOS: 12px y 10px
            f_title = ImageFont.truetype(FONT_PATH, 12) 
            f_bullet = ImageFont.truetype(FONT_PATH, 10)
        else:
            return jsonify({"error": "Falta Montserrat-Bold.ttf"}), 500

        draw = ImageDraw.Draw(canvas)
        
        # Posicionamiento en el marco inferior (comienza en 945px)
        # Centramos el bloque de texto verticalmente en los 135px disponibles
        y_cursor = 945 + 45 
        x_margin = 120 # Un poco más de margen lateral para que se vea más centrado
        
        # Dibujar Título (12px)
        draw.text((x_margin, y_cursor), title[:80], font=f_title, fill=(255, 255, 255))
        
        # Dibujar Bullets (10px)
        y_cursor += 25
        for b in bullets:
            if b and "spacer" not in str(b).lower():
                clean_b = str(b).replace("•", "").strip()[:100]
                draw.text((x_margin, y_cursor), f"• {clean_b}", font=f_bullet, fill=(150, 150, 150))
                y_cursor += 18 # Espaciado muy fino

        # 5. Guardado
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
