from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import io
import os
import base64
import uuid
import time

app = Flask(__name__)

# =========================
# Storage for generated images (in-memory, temporary)
# =========================
generated_images = {}

# =========================
# Font Configuration
# =========================
FONT_BOLD_PATH = "Montserrat-Bold.ttf"
FONT_REGULAR_PATH = "Montserrat-VariableFont_wght.ttf"

# =========================
# Colors
# =========================
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BULLET_COLOR = (185, 185, 185)

# =========================
# Font Sizes - AJUSTADOS
# =========================
TITLE_FONT_SIZE = 42  # Aumentado de 32 a 38
BULLET_FONT_SIZE = 35  # Reducido de 26 a 24 para mejor legibilidad

# =========================
# Load Fonts
# =========================
try:
    title_font = ImageFont.truetype(FONT_BOLD_PATH, TITLE_FONT_SIZE)
    bullet_font = ImageFont.truetype(FONT_BOLD_PATH, BULLET_FONT_SIZE)
except Exception as e:
    print(f"Error loading fonts: {e}")
    title_font = ImageFont.load_default()
    bullet_font = ImageFont.load_default()

# =========================
# Layout Configuration - AJUSTADOS
# =========================
FOOTER_HEIGHT = 230  # Aumentado de 140 a 160 para más espacio
BULLET_GAP_Y = 40    # Aumentado de 38 a 40 para mejor separación
BULLET_DOT_OFFSET_X = 180  # Aumentado de 20 a 30
BULLET_TEXT_OFFSET_X = 205  # Aumentado de 40 a 55
TITLE_TOP_MARGIN = 10  # Margen superior del título
BULLET_START_OFFSET = 60  # Espacio entre título y primer bullet
RIGHT_TEXT_MARGIN = 100  # margen derecho para alinear título y bullets
FOOTER_BOTTOM_SAFE_PADDING = 60  # nuevo (sube si quieres más aire)


# =========================
# Photo Placement (Template) - NUEVO
# =========================
PHOTO_LEFT_MARGIN = 0
PHOTO_RIGHT_MARGIN = 0
PHOTO_TOP = 230              # <<< OFFSET 210px hacia abajo (deja espacio para header)
PHOTO_BOTTOM_PADDING = 30    # espacio antes del footer



def cleanup_old_images():
    """Remove images older than 10 minutes"""
    current_time = time.time()
    keys_to_delete = []
    for key, value in generated_images.items():
        if current_time - value['timestamp'] > 600:  # 10 minutes
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del generated_images[key]


def wrap_text(text, font, max_width):
    """Divide el texto en múltiples líneas si excede el ancho máximo"""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def place_photo_on_template(template_img, photo_img):
    template_img = template_img.convert("RGB")
    photo_img = photo_img.convert("RGB")

    tpl_w, tpl_h = template_img.size

    left = PHOTO_LEFT_MARGIN
    right = tpl_w - PHOTO_RIGHT_MARGIN
    top = PHOTO_TOP
    bottom = tpl_h - FOOTER_HEIGHT - PHOTO_BOTTOM_PADDING

    box_w = right - left
    box_h = bottom - top

    pw, ph = photo_img.size
    box_ratio = box_w / box_h
    photo_ratio = pw / ph

    # Resize tipo "cover"
    if photo_ratio > box_ratio:
        new_h = box_h
        new_w = int(new_h * photo_ratio)
    else:
        new_w = box_w
        new_h = int(new_w / photo_ratio)

    photo_resized = photo_img.resize((new_w, new_h), Image.LANCZOS)

    # Crop centrado
    crop_left = (new_w - box_w) // 2
    crop_top = (new_h - box_h) // 2
    photo_cropped = photo_resized.crop(
        (crop_left, crop_top, crop_left + box_w, crop_top + box_h)
    )

    template_img.paste(photo_cropped, (left, top))
    return template_img



def draw_footer(draw, width, height, title, bullets):
    """Dibuja la franja negra inferior con título y bullets"""
    footer_y = height - FOOTER_HEIGHT
    
    # Dibujar rectángulo negro del footer
    draw.rectangle([(0, footer_y), (width, height)], fill=BLACK)
    
    # Dibujar título
    title_y = footer_y + TITLE_TOP_MARGIN
    title_text = title.upper()
    bbox = title_font.getbbox(title_text)
    title_w = bbox[2] - bbox[0]

    title_x = BULLET_TEXT_OFFSET_X
    draw.text((title_x, title_y), title_text, font=title_font, fill=WHITE)

    
    # Calcular posición inicial de los bullets
    bullet_start_y = title_y + BULLET_START_OFFSET
    
    # Ancho máximo para el texto de los bullets (deja margen a la derecha)
    max_bullet_width = (width - RIGHT_TEXT_MARGIN) - BULLET_TEXT_OFFSET_X - 40
    
    current_y = bullet_start_y
    max_y = height - FOOTER_BOTTOM_SAFE_PADDING

    
    # Dibujar cada bullet
    for text in bullets:
        if text and text.strip():  # Solo dibujar si hay texto
            # Dividir el texto en líneas si es necesario
            lines = wrap_text(text, bullet_font, max_bullet_width)
            
            # Dibujar el bullet point solo para la primera línea
            draw.text(
                (BULLET_DOT_OFFSET_X, current_y),
                "•",
                font=bullet_font,
                fill=BULLET_COLOR
            )
            
            # Dibujar cada línea del texto
            for i, line in enumerate(lines):
                draw.text(
                    (BULLET_TEXT_OFFSET_X, current_y),
                    line,
                    font=bullet_font,
                    fill=BULLET_COLOR
                )
                current_y += BULLET_GAP_Y  # Mover a la siguiente línea
            
            # Si el bullet solo tenía una línea, aún necesitamos mover el cursor
            if len(lines) == 0:
                current_y += BULLET_GAP_Y


def process_image_from_base64(image_base64, title, bullets):
    """Procesa la imagen desde base64 - USA TEMPLATE + pega foto + footer"""
    try:
        # 1) Abrir foto (la que viene de n8n)
        image_data = base64.b64decode(image_base64)
        photo = Image.open(io.BytesIO(image_data))

        # 2) Abrir template (con header/logo)
        template = Image.open("template.jpg")

        # 3) Pegar foto dentro del template (con offset PHOTO_TOP=210)
        img = place_photo_on_template(template, photo)

        # 4) Dibujar footer
        width, height = img.size
        draw = ImageDraw.Draw(img)
        draw_footer(draw, width, height, title, bullets)

        return img
    except Exception as e:
        print(f"Error processing base64 image: {e}")
        raise



def process_image_from_file(image_path, title, bullets):
    """Procesa la imagen desde archivo - USA TEMPLATE + pega foto + footer"""
    try:
        template = Image.open("template.jpg")

        # Si te pasan una foto real (no el mismo template), pégala dentro del template
        if os.path.exists(image_path) and image_path != "template.jpg":
            photo = Image.open(image_path)
            img = place_photo_on_template(template, photo)
        else:
            # Si no hay foto, solo usa el template tal cual
            img = template.convert("RGB")

        width, height = img.size
        draw = ImageDraw.Draw(img)
        draw_footer(draw, width, height, title, bullets)

        return img
    except Exception as e:
        print(f"Error processing file image: {e}")
        raise



@app.route('/')
def home():
    return '''
    <h1>Prestige 360 Image Generator</h1>
    <p>API para generar imágenes con branding de Prestige 360</p>
    <h3>Endpoints:</h3>
    <ul>
        <li>POST /generate - Genera imagen con título y bullets</li>
        <li>POST /generate-post - Genera imagen desde base64 (para n8n)</li>
        <li>GET /download/&lt;image_id&gt; - Descarga imagen generada</li>
        <li>GET /health - Health check</li>
    </ul>
    <h3>Estado:</h3>
    <p>Server running OK - ''' + str(len(generated_images)) + ''' images in cache</p>
    '''


@app.route('/generate', methods=['POST'])
def generate():
    """Endpoint simple con title y bullets array"""
    try:
        data = request.get_json()
        
        title = data.get('title', 'Title Here')
        bullets = data.get('bullets', ['Bullet point 1', 'Bullet point 2', 'Bullet point 3'])
        
        # Asegurar que tenemos exactamente 3 bullets
        while len(bullets) < 3:
            bullets.append('')
        
        img = process_image_from_file("template.jpg", title, bullets[:3])
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=95)
        img_buffer.seek(0)
        
        return send_file(
            img_buffer,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name='prestige360_output.jpg'
        )
    
    except Exception as e:
        print(f"Error in /generate: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/generate-post', methods=['POST'])
def generate_post():
    """Endpoint para n8n - devuelve download_url"""
    try:
        cleanup_old_images()
        
        data = request.get_json()
        
        image_base64 = data.get('image_base64', '')
        title = data.get('title', 'Title Here')
        bullet1 = data.get('bullet1', '')
        bullet2 = data.get('bullet2', '')
        bullet3 = data.get('bullet3', '')
        
        bullets = [bullet1, bullet2, bullet3]
        
        # Procesar imagen
        if image_base64:
            img = process_image_from_base64(image_base64, title, bullets)
        else:
            img = process_image_from_file("template.jpg", title, bullets)
        
        # Save to buffer
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=95)
        img_buffer.seek(0)
        
        # Generate unique ID and store image
        image_id = str(uuid.uuid4())
        generated_images[image_id] = {
            'data': img_buffer.getvalue(),
            'timestamp': time.time()
        }
        
        # Build download URL
        base_url = request.host_url.rstrip('/')
        download_url = f"{base_url}/download/{image_id}"
        
        return jsonify({
            'success': True,
            'download_url': download_url,
            'image_id': image_id,
            'message': 'Image generated successfully'
        })
    
    except Exception as e:
        print(f"Error in /generate-post: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/download/<image_id>', methods=['GET'])
def download_image(image_id):
    """Download generated image by ID"""
    try:
        if image_id not in generated_images:
            return jsonify({'error': 'Image not found or expired'}), 404
        
        image_data = generated_images[image_id]['data']
        img_buffer = io.BytesIO(image_data)
        img_buffer.seek(0)
        
        return send_file(
            img_buffer,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'prestige360_{image_id}.jpg'
        )
    
    except Exception as e:
        print(f"Error in /download: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'images_in_cache': len(generated_images),
        'message': 'Prestige 360 Image Generator is running'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
