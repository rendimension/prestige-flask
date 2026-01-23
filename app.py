from flask import Flask, request, send_file, jsonify, url_for
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
ORANGE = (255, 107, 53)

# =========================
# Font Sizes
# =========================
TITLE_FONT_SIZE = 32
SUBTITLE_FONT_SIZE = 18
BULLET_FONT_SIZE = 26

# =========================
# Load Fonts
# =========================
try:
    title_font = ImageFont.truetype(FONT_BOLD_PATH, TITLE_FONT_SIZE)
    subtitle_font = ImageFont.truetype(FONT_REGULAR_PATH, SUBTITLE_FONT_SIZE)
    bullet_font = ImageFont.truetype(FONT_BOLD_PATH, BULLET_FONT_SIZE)
    logo_font_prestige = ImageFont.truetype("Quicksand-VariableFont_wght.ttf", 36)
    logo_font_360 = ImageFont.truetype(FONT_REGULAR_PATH, 36)
except Exception as e:
    print(f"Error loading fonts: {e}")
    title_font = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()
    bullet_font = ImageFont.load_default()
    logo_font_prestige = ImageFont.load_default()
    logo_font_360 = ImageFont.load_default()

# =========================
# Layout Configuration
# =========================
HEADER_HEIGHT = 70
FOOTER_HEIGHT = 140
BULLET_GAP_Y = 38
BULLET_DOT_OFFSET_X = 20
BULLET_TEXT_OFFSET_X = 40


def cleanup_old_images():
    """Remove images older than 10 minutes"""
    current_time = time.time()
    keys_to_delete = []
    for key, value in generated_images.items():
        if current_time - value['timestamp'] > 600:  # 10 minutes
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del generated_images[key]


def draw_header(draw, width):
    """Dibuja la franja negra superior con el logo"""
    draw.rectangle([(0, 0), (width, HEADER_HEIGHT)], fill=BLACK)
    prestige_text = "Prestige"
    draw.text((30, 18), prestige_text, font=logo_font_prestige, fill=ORANGE)
    draw.text((155, 18), "360", font=logo_font_360, fill=WHITE)
    tagline = "Commercial Design From Concept to Opening"
    draw.text((250, 28), tagline, font=subtitle_font, fill=WHITE)


def draw_footer(draw, width, height, title, bullets):
    """Dibuja la franja negra inferior con título y bullets"""
    footer_y = height - FOOTER_HEIGHT
    draw.rectangle([(0, footer_y), (width, height)], fill=BLACK)
    title_y = footer_y + 15
    draw.text((20, title_y), title.upper(), font=title_font, fill=WHITE)
    
    bullet_start_y = title_y + 50
    for i, text in enumerate(bullets):
        if text:
            line_y = bullet_start_y + (i * BULLET_GAP_Y)
            draw.text(
                (BULLET_DOT_OFFSET_X, line_y),
                "•",
                font=bullet_font,
                fill=BULLET_COLOR
            )
            draw.text(
                (BULLET_TEXT_OFFSET_X, line_y),
                text,
                font=bullet_font,
                fill=BULLET_COLOR
            )


def process_image_from_base64(image_base64, title, bullets):
    """Procesa la imagen desde base64"""
    image_data = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(image_data))
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    width, height = img.size
    draw = ImageDraw.Draw(img)
    
    draw_header(draw, width)
    draw_footer(draw, width, height, title, bullets)
    
    return img


def process_image_from_file(image_path, title, bullets):
    """Procesa la imagen desde archivo"""
    if os.path.exists(image_path):
        img = Image.open(image_path)
    else:
        img = Image.open("template.jpg")
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    width, height = img.size
    draw = ImageDraw.Draw(img)
    
    draw_header(draw, width)
    draw_footer(draw, width, height, title, bullets)
    
    return img


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
    </ul>
    '''


@app.route('/generate', methods=['POST'])
def generate():
    """Endpoint simple con title y bullets array"""
    try:
        data = request.get_json()
        
        title = data.get('title', 'Title Here')
        bullets = data.get('bullets', ['Bullet point 1', 'Bullet point 2', 'Bullet point 3'])
        
        img = process_image_from_file("template.jpg", title, bullets)
        
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
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
