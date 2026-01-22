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
FONT_BOLD_PATH = os.path.join(BASE_DIR, 'Montserrat-Bold.ttf') 

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# GEOMETRÍA FIJA (12.5% - 75% - 12.5%)
CANVAS_SIZE = 1080
FRAME_H = 135  
IMG_H = 810    

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    # Limpieza de textos
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

        # 3. Logo Top
        if os.path.exists(TEMPLATE_PATH):
            temp = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp = temp.resize((CANVAS_SIZE, CANVAS_SIZE))
            logo_zone = temp.crop((0, 0, CANVAS_SIZE, FRAME_H))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 4. Textos - EL PUNTO MEDIO (18px y 15px)
        if os.path.exists(FONT_BOLD_PATH):
            f_title = ImageFont.truetype(FONT_BOLD_PATH, 18) 
            f_bullet = ImageFont.truetype(FONT_BOLD_PATH, 15)
        else:
            return jsonify({"error": "Falta Montserrat-Bold.ttf"}), 500

        draw = ImageDraw.Draw(canvas)
        
        # Posicionamiento: y_cursor inicia en 945px (inicio del marco negro inferior)
        y_cursor = 945 + 35 
        x_margin = 80
        
        # Título
        draw.text((x_margin, y_cursor), title[:70], font=f_title, fill=(255, 255, 255))
        
        # Bullets
        y_cursor += 30
        for b in bullets:
            clean_b = str(b).strip()
            if clean_b and "spacer" not in clean_b.lower() and len(clean_b) > 2:
                txt = clean_b.replace("•", "").strip()[:85]
                draw.text((x_margin, y_cursor), f"•  {txt}", font=f_bullet, fill=(210, 210, 210))
                y_cursor += 22

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
