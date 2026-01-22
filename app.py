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
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# GEOMETRÍA
CANVAS_SIZE = 1080
FRAME_H = 135  
IMG_H = 810    

def get_font(size):
    """Busca la fuente en el repo o usa una de sistema que SÍ escale"""
    paths = [
        os.path.join(BASE_DIR, 'Montserrat-Bold.ttf'),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Estándar en Railway
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default() # Último recurso (se verá pequeño)

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "").upper().replace("STRATEGIC", "").strip()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0))

        if img_b64:
            if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
            img_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
            main_img = ImageOps.fit(img_raw, (CANVAS_SIZE, IMG_H), Image.Resampling.LANCZOS)
            canvas.paste(main_img, (0, FRAME_H))

        if os.path.exists(TEMPLATE_PATH):
            temp = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp = temp.resize((CANVAS_SIZE, CANVAS_SIZE))
            logo_zone = temp.crop((0, 0, CANVAS_SIZE, FRAME_H))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # FUENTES INCREMENTADAS PARA FORZAR VISIBILIDAD
        f_title = get_font(26) 
        f_bullet = get_font(20)

        draw = ImageDraw.Draw(canvas)
        y_cursor = 945 + 30 
        x_margin = 80
        
        # Título
        draw.text((x_margin, y_cursor), title[:65], font=f_title, fill="white")
        
        # Bullets
        y_cursor += 35
        for b in bullets:
            clean_b = str(b).strip()
            if clean_b and "spacer" not in clean_b.lower():
                txt = clean_b.replace("•", "").strip()[:80]
                draw.text((x_margin, y_cursor), f"• {txt}", font=f_bullet, fill=(220, 220, 220))
                y_cursor += 28

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
