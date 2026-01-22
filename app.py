from flask import Flask, request, jsonify, send_from_directory
import os
from PIL import Image, ImageDraw, ImageFont
import uuid
import base64
from io import BytesIO

app = Flask(__name__)

# Configuración de carpetas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def get_scalable_font(size):
    """Fuerza la carga de una fuente que SÍ permite cambiar el tamaño."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Estándar en Railway
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        os.path.join(BASE_DIR, 'fonts', 'Montserrat-Bold.ttf')
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    # Si no hay ninguna, usamos la básica (pero saldrá pequeña)
    return ImageFont.load_default()

def fit_image(img, size=(1080, 1080)):
    """Ajusta la imagen para llenar el fondo sin deformar."""
    img = img.convert("RGB")
    iw, ih = img.size
    target_w, target_h = size
    scale = max(target_w / iw, target_h / ih)
    new_size = (int(iw * scale), int(ih * scale))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    # Centrar y recortar
    left = (new_size[0] - target_w) / 2
    top = (new_size[1] - target_h) / 2
    return img.crop((left, top, left + target_w, top + target_h))

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "PROYECTO").upper()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Crear el fondo con la imagen de la IA
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        img_data = base64.b64decode(img_b64)
        bg = Image.open(BytesIO(img_data))
        canvas = fit_image(bg, (1080, 1080))

        # 2. Añadir bandas negras translúcidas (Diseño Creativo)
        overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Banda superior (Logo)
        draw_ov.rectangle([0, 0, 1080, 180], fill=(0, 0, 0, 140))
        # Banda inferior (Texto)
        draw_ov.rectangle([0, 720, 1080, 1080], fill=(0, 0, 0, 200))
        canvas.paste(overlay, (0, 0), overlay)

        # 3. Poner el Logo (Template) - Forzando transparencia
        if os.path.exists(TEMPLATE_PATH):
            temp = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp = temp.resize((1080, 1080))
            # Solo pegamos la parte superior del template para no tapar el fondo
            canvas.paste(temp, (0, 0), temp)

        # 4. Escribir Texto Gigante
        draw = ImageDraw.Draw(canvas)
        f_title = get_scalable_font(75)
        f_bullet = get_scalable_font(40)

        # Dibujar Título
        draw.text((80, 750), title, font=f_title, fill=(255, 255, 255))
        
        # Dibujar Bullets
        y_pos = 850
        for b in bullets:
            if b and "spacer" not in str(b).lower():
                draw.text((80, y_pos), f"• {str(b).strip()}", font=f_bullet, fill=(240, 240, 240))
                y_pos += 60

        # 5. Guardar
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
