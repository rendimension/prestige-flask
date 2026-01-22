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
# RUTA A LA NUEVA FUENTE ESTÁTICA
FONT_PATH = os.path.join(BASE_DIR, 'Montserrat-Bold.ttf') 

os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def fit_image(img, size=(1080, 1080)):
    """Ajusta la imagen de la IA para que llene todo el post perfectamente."""
    img = img.convert("RGB")
    # ImageOps.fit recorta y centra automáticamente para llenar el espacio
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "").upper()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64", "")

    try:
        # 1. Fondo: Imagen de la IA (1080x1080)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        bg_raw = Image.open(BytesIO(base64.b64decode(img_b64)))
        canvas = fit_image(bg_raw)

        # 2. Diseño Creativo: Bandas translúcidas
        overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        # Banda superior para el Logo (Opacidad 50%)
        draw_ov.rectangle([0, 0, 1080, 180], fill=(0, 0, 0, 130))
        # Banda inferior para el Texto (Opacidad 85% para legibilidad máxima)
        draw_ov.rectangle([0, 720, 1080, 1080], fill=(0, 0, 0, 215))
        canvas.paste(overlay, (0, 0), overlay)

        # 3. Logo (Template) - Pegamos solo la cabecera para no tapar el centro
        if os.path.exists(TEMPLATE_PATH):
            temp_img = Image.open(TEMPLATE_PATH).convert("RGBA")
            temp_img = temp_img.resize((1080, 1080))
            logo_zone = temp_img.crop((0, 0, 1080, 180))
            canvas.paste(logo_zone, (0, 0), logo_zone)

        # 4. Textos con MONTSERRAT BOLD (Nitidez extrema)
        if os.path.exists(FONT_PATH):
            f_title = ImageFont.truetype(FONT_PATH, 70) 
            f_bullet = ImageFont.truetype(FONT_PATH, 38)
        else:
            return jsonify({"error": "No se encontro Montserrat-Bold.ttf en el repo"}), 500

        draw = ImageDraw.Draw(canvas)
        # Dibujar Título
        draw.text((75, 755), title[:42], font=f_title, fill=(255, 255, 255))
        
        # Dibujar Bullets
        y = 855
        for b in bullets:
            if b and "spacer" not in str(b).lower():
                txt = f"•  {str(b).strip()[:55]}"
                draw.text((75, y), txt, font=f_bullet, fill=(240, 240, 240))
                y += 60

        # 5. Guardar con calidad de impresión
        filename = f"post_{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(POST_OUTPUT_DIR, filename)
        # Calidad 100 y subsampling 0 eliminan cualquier ruido en las letras
        canvas.save(save_path, "JPEG", quality=100, subsampling=0)
        
        return jsonify({"status": "success", "download_url": f"{request.url_root.rstrip('/')}/post_output/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
