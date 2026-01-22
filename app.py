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
# FUENTES
FONT_BOLD = os.path.join(BASE_DIR, 'Montserrat-Bold.ttf') 
FONT_LIGHT = os.path.join(BASE_DIR, 'Quicksand-VariableFont_wght.ttf')

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

CANVAS_SIZE = 1080
FRAME_H = 135  
IMG_H = 810    

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    # Limpieza de textos
    title = data.get("title", "").upper().replace("STRATEGIC", "").replace("SUCCESS", "").replace("PLANNING", "").strip()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0))

        # 1. Imagen Central
        if img_b64:
            if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
            img_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
            main_img = ImageOps.fit(img_raw, (CANVAS_SIZE, IMG_H), method=Image.Resampling.LANCZOS)
            canvas.paste(main_img, (0, FRAME_H))

        # 2. Logo Top
        if os.path.exists(TEMPLATE_PATH):
            temp = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp = temp.resize((CANVAS_SIZE, CANVAS_SIZE))
            logo_zone = temp.crop((0, 0, CANVAS_SIZE, FRAME_H))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 3. Textos con Mix de Fuentes
        # Título en BOLD (13px) y Bullets en LIGHT (11px)
        f_title = ImageFont.truetype(FONT_BOLD, 13) if os.path.exists(FONT_BOLD) else ImageFont.load_default()
        f_bullet = ImageFont.truetype(FONT_LIGHT, 11) if os.path.exists(FONT_LIGHT) else ImageFont.load_default()

        draw = ImageDraw.Draw(canvas)
        y_cursor = 945 + 40 
        x_margin = 100
        
        # Dibujar Título
        draw.text((x_margin, y_cursor), title[:80], font=f_title, fill=(255, 255, 255))
        
        # Dibujar Bullets
        y_cursor += 22
        for b in bullets:
            # Filtro estricto para no mostrar "spacers" o vacíos
            clean_b = str(b).strip()
            if clean_b and "spacer" not in clean_b.lower() and len(clean_b) > 2:
                txt = clean_b.replace("•", "").strip()[:90]
                draw.text((x_margin, y_cursor), f"•  {txt}", font=f_bullet, fill=(180, 180, 180))
                y_cursor += 18

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
