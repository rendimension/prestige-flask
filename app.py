from flask import Flask, request, jsonify, send_from_directory
import os
from PIL import Image, ImageDraw, ImageFont
import uuid
import base64
from io import BytesIO

app = Flask(__name__)

# Configuración de carpetas y archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
# USANDO TU NUEVA FUENTE QUICKSAND
FONT_PATH = os.path.join(BASE_DIR, 'Quicksand-VariableFont_wght.ttf') 

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def fit_image(img, size=(1080, 1080)):
    """Ajusta la imagen de la IA para que llene todo el post 1080x1080."""
    img = img.convert("RGB")
    iw, ih = img.size
    scale = max(size[0] / iw, size[1] / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img.crop(((nw - size[0])//2, (nh - size[1])//2, (nw + size[0])//2, (nh + size[1])//2))

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "").upper()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Crear Fondo (Imagen de la IA)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        bg = Image.open(BytesIO(base64.b64decode(img_b64)))
        canvas = fit_image(bg)

        # 2. Capa de diseño: Bandas translúcidas (Creativas)
        overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Banda Logo (Superior) - Opacidad suave
        draw_ov.rectangle([0, 0, 1080, 180], fill=(0, 0, 0, 140)) 
        # Banda Texto (Inferior) - Opacidad más fuerte para lectura
        draw_ov.rectangle([0, 710, 1080, 1080], fill=(0, 0, 0, 215)) 
        canvas.paste(overlay, (0, 0), overlay)

        # 3. Poner el Logo (Parte superior del Template)
        if os.path.exists(TEMPLATE_PATH):
            logo_img = Image.open(TEMPLATE_PATH).convert("RGBA")
            logo_img = logo_img.resize((1080, 1080))
            logo_crop = logo_img.crop((0, 0, 1080, 180))
            canvas.paste(logo_crop, (0, 0), logo_crop)

        # 4. Textos con QUICKSAND (Ajuste de nitidez)
        if os.path.exists(FONT_PATH):
            # Quicksand es un poco más delgada, subimos un punto el tamaño
            f_title = ImageFont.truetype(FONT_PATH, 68) 
            f_bullet = ImageFont.truetype(FONT_PATH, 38)
        else:
            return jsonify({"error": f"Archivo {os.path.basename(FONT_PATH)} no encontrado en el repo"}), 500

        draw = ImageDraw.Draw(canvas)
        
        # Título
        draw.text((80, 740), title[:45], font=f_title, fill=(255, 255, 255))
        
        # Bullets
        y = 835
        for b in bullets:
            if b and "spacer" not in str(b).lower():
                txt = str(b).strip()[:55]
                draw.text((80, y), f"•  {txt}", font=f_bullet, fill=(245, 245, 245))
                y += 65

        # 5. Guardar con calidad máxima para evitar lo "difuso"
        filename = f"post_{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(POST_OUTPUT_DIR, filename)
        # Usamos calidad 100 y desactivamos el subsampling para bordes perfectos
        canvas.save(save_path, "JPEG", quality=100, subsampling=0) 
        
        return jsonify({"status": "success", "download_url": f"{request.url_root.rstrip('/')}/post_output/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
