from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import io
import os
import base64

app = Flask(__name__)

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
BULLET_COLOR = (185, 185, 185)  # Gris claro para bullets
ORANGE = (255, 107, 53)  # Color naranja para "Prestige"

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


def draw_header(draw, width):
    """Dibuja la franja negra superior con el logo"""
    # Franja negra superior
    draw.rectangle([(0, 0), (width, HEADER_HEIGHT)], fill=BLACK)
    
    # Texto "Prestige" en estilo cursivo/elegante (naranja)
    prestige_text = "Prestige"
    draw.text((30, 18), prestige_text, font=logo_font_prestige, fill=ORANGE)
    
    # Texto "360" 
    draw.text((155, 18), "360", font=logo_font_360, fill=WHITE)
    
    # Tagline
    tagline = "Commercial Design From Concept to Opening"
    draw.text((250, 28), tagline, font=subtitle_font, fill=WHITE)


def draw_footer(draw, width, height, title, bullets):
    """Dibuja la franja negra inferior con título y bullets"""
    footer_y = height - FOOTER_HEIGHT
    
    # Franja negra inferior
    draw.rectangle([(0, footer_y), (width, height)], fill=BLACK)
    
    # Título en blanco
    title_y = footer_y + 15
    draw.text((20, title_y), title.upper(), font=title_font, fill=WHITE)
    
    # Bullets
    bullet_start_y = title_y + 50
    for i, text in enumerate(bullets):
        if text:  # Solo dibujar si hay texto
            line_y = bullet_start_y + (i * BULLET_GAP_Y)
            
            # Punto bullet
            draw.text(
                (BULLET_DOT_OFFSET_X, line_y),
                "•",
                font=bullet_font,
                fill=BULLET_COLOR
            )
            
            # Texto del bullet
            draw.text(
                (BULLET_TEXT_OFFSET_X, line_y),
                text,
                font=bullet_font,
                fill=BULLET_COLOR
            )


def process_image_from_base64(image_base64, title, bullets):
    """Procesa la imagen desde base64 agregando header, footer y texto"""
    # Decodificar imagen base64
    image_data = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(image_data))
    
    # Convertir a RGB si es necesario
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    width, height = img.size
    draw = ImageDraw.Draw(img)
    
    # Dibujar header y footer
    draw_header(draw, width)
    draw_footer(draw, width, height, title, bullets)
    
    return img


def process_image_from_file(image_path, title, bullets):
    """Procesa la imagen desde archivo agregando header, footer y texto"""
    if os.path.exists(image_path):
        img = Image.open(image_path)
    else:
        img = Image.open("template.jpg")
    
    # Convertir a RGB si es necesario
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    width, height = img.size
    draw = ImageDraw.Draw(img)
    
    # Dibujar header y footer
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
    </ul>
    <h3>Ejemplo de uso:</h3>
    <pre>
    POST /generate
    Content-Type: application/json
    
    {
        "title": "Effective Space Planning Essentials",
        "bullets": [
            "Aesthetics don't ensure efficiency.",
            "Easy navigation is crucial for visitors.",
            "Contact us for transformative space design."
        ]
    }
    </pre>
    '''


@app.route('/generate', methods=['POST'])
def generate():
    """Endpoint simple con title y bullets array"""
    try:
        data = request.get_json()
        
        title = data.get('title', 'Title Here')
        bullets = data.get('bullets', ['Bullet point 1', 'Bullet point 2', 'Bullet point 3'])
        
        # Usar template.jpg como base
        img = process_image_from_file("template.jpg", title, bullets)
        
        # Guardar en buffer
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
    """Endpoint para n8n con image_base64, title, bullet1, bullet2, bullet3"""
    try:
        data = request.get_json()
        
        # Obtener datos del JSON (formato n8n)
        image_base64 = data.get('image_base64', '')
        title = data.get('title', 'Title Here')
        bullet1 = data.get('bullet1', '')
        bullet2 = data.get('bullet2', '')
        bullet3 = data.get('bullet3', '')
        
        # Crear lista de bullets
        bullets = [bullet1, bullet2, bullet3]
        
        # Procesar imagen
        if image_base64:
            img = process_image_from_base64(image_base64, title, bullets)
        else:
            img = process_image_from_file("template.jpg", title, bullets)
        
        # Guardar en buffer
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=95)
        img_buffer.seek(0)
        
        # Convertir a base64 para devolver a n8n
        img_buffer_for_base64 = io.BytesIO()
        img.save(img_buffer_for_base64, format='JPEG', quality=95)
        img_buffer_for_base64.seek(0)
        result_base64 = base64.b64encode(img_buffer_for_base64.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image_base64': result_base64,
            'message': 'Image generated successfully'
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
