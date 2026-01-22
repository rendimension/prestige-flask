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

# RUTAS DE FUENTES PARA EL MIX
FONT_BOLD_PATH = os.path.join(BASE_DIR, 'Montserrat-Bold.ttf') 
FONT_REGULAR_PATH = os.path.join(BASE_DIR, 'Quicksand-VariableFont_wght.ttf')

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

# GEOMETRÍA ESTRICTA
CANVAS_SIZE = 1080
FRAME_H = 135  
IMG_H = 810    

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    # Limpieza de textos para diseño limpio
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
            main_img = ImageOps.fit(img_raw, (CANVAS_SIZE, IMG_H), Image.Resampling.LANCZOS)
            canvas.paste(main_img, (0, FRAME_H))

        # 3. Logo/Top Frame
        if os.path.exists(TEMPLATE_PATH):
            temp = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp = temp.resize((CANVAS_SIZE, CANVAS_SIZE))
            logo_zone = temp.crop((0, 0, CANVAS_SIZE, FRAME_H))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 4. CARGA DE FUENTES (Mix de Pesos)
        # Título en BOLD (22px)
        f_title = ImageFont.truetype(FONT_BOLD_PATH, 22) if os.path.exists(FONT_BOLD_PATH) else ImageFont.load_default()
        # Bullets en REGULAR (18px para compensar delgadez)
        f_bullet = ImageFont.truetype(FONT_REGULAR_PATH, 18) if os.path.exists(FONT_REGULAR_PATH) else ImageFont.load_default()

        draw = ImageDraw.Draw(canvas)
        
        # Posicionamiento en el marco inferior (945px + margen)
        y_cursor = 945 + 32 
        x_margin = 85
        
        # Dibujar Título
        draw.text((x_margin, y_cursor), title[:75], font=f_title, fill="white")
        
        # Dibujar Bullets con fuente ligera
        y_cursor += 38
        for b in bullets:
            clean_b = str(b).strip()
            if clean_b and "spacer" not in clean_b.lower() and len(clean_b) > 2:
                txt = clean_b.replace("•", "").strip()[:90]
                # Blanco puro para los bullets delgados para mejorar contraste
                draw.text((x_margin, y_cursor), f"•  {txt}", font=f_bullet, fill=(255, 255, 255))
                y_cursor += 24 # Salto de línea elegante

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
