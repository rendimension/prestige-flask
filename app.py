from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import uuid
import base64
from io import BytesIO

app = Flask(__name__)

# === Configuración de Rutas ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POST_OUTPUT_DIR = os.path.join(BASE_DIR, 'post_output')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.jpg')
os.makedirs(POST_OUTPUT_DIR, exist_ok=True)

def get_system_font(size):
    """Busca fuentes reales en el servidor Railway para poder escalarlas."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        os.path.join(BASE_DIR, 'fonts', 'Montserrat-Bold.ttf')
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def fit_cover(img, target_size=(1080, 1080)):
    """Hace que la imagen llene todo el cuadro sin deformarse."""
    iw, ih = img.size
    tw, th = target_size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img.crop(((nw-tw)//2, (nh-th)//2, (nw+tw)//2, (nh+th)//2))

@app.route("/generate-post", methods=["POST"])
def generate_post():
    data = request.get_json()
    if isinstance(data, list): data = data[0]
    
    title = data.get("title", "PROYECTO COMERCIAL").upper()
    bullets = [data.get("bullet1"), data.get("bullet2"), data.get("bullet3")]
    img_b64 = data.get("image_base64")

    try:
        # 1. CREAR FONDO TOTAL (1080x1080)
        if ',' in img_b64: img_b64 = img_b64.split(',', 1)[1]
        img_data = base64.b64decode(img_b64)
        background = Image.open(BytesIO(img_data)).convert("RGB")
        background = fit_cover(background) # Ahora la imagen es el 100% del post

        # 2. CAPA DE DISEÑO (Bandas translúcidas)
        # Creamos una imagen transparente para dibujar las bandas
        overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        
        # Banda superior (Logo) - Negro con 50% de opacidad
        draw_ov.rectangle([0, 0, 1080, 180], fill=(0, 0, 0, 130))
        # Banda inferior (Texto) - Negro con 75% de opacidad
        draw_ov.rectangle([0, 720, 1080, 1080], fill=(0, 0, 0, 190))
        
        # Fusionar bandas con el fondo
        background.paste(overlay, (0, 0), overlay)

        # 3. PEGAR EL LOGO (Template)
        if os.path.exists(TEMPLATE_PATH):
            logo_layer = Image.open(TEMPLATE_PATH).convert("RGBA")
            logo_layer = logo_layer.resize((1080, 1080))
            background.paste(logo_layer, (0, 0), logo_layer)

        # 4. TEXTOS GIGANTES
        draw = ImageDraw.Draw(background)
        f_title = get_system_font(70)  # Título bien grande
        f_bullet = get_system_font(38) # Bullets legibles

        # Dibujar Título (Sombra ligera para legibilidad extra)
        draw.text((72, 752), title, font=f_title, fill=(0,0,0)) # Sombra
        draw.text((70, 750), title, font=f_title, fill=(255, 255, 255))
        
        # Dibujar Bullets
        y = 850
        for b in bullets:
            if b and "spacer" not in b.lower():
                txt = f"• {str(b).strip()}"
                draw.text((70, y), txt, font=f_bullet, fill=(255, 255, 255))
                y += 60

        # 5. GUARDAR RESULTADO
        fname = f"post_{uuid.uuid4().hex}.jpg"
        out_path = os.path.join(POST_OUTPUT_DIR, fname)
        background.save(out_path, "JPEG", quality=95)
        
        return jsonify({
            "status": "success", 
            "download_url": f"{request.url_root.rstrip('/')}/post_output/{fname}",
            "layout": "creative_full_image"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post_output/<path:filename>')
def send_output(filename):
    return send_from_directory(POST_OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
