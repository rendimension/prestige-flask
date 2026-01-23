from PIL import ImageFont

# =========================
# Bullet style only
# =========================

# Gris claro para que no compita con el titulo
BULLET_COLOR = (185, 185, 185)

# Tamaño y fuente bold solo para bullets
BULLET_FONT_SIZE = 30  # deja el que ya usas, o ajusta 28 a 34
bullet_font = ImageFont.truetype(FONT_BOLD_PATH, BULLET_FONT_SIZE)

# Espaciado
BULLET_GAP_Y = 52      # separacion entre lineas
BULLET_DOT_OFFSET_X = 0
BULLET_TEXT_OFFSET_X = 24

def draw_bullets(draw, bullets, x, y):
    """
    bullets: lista de strings
    x, y: posicion inicial del bloque de bullets
    """
    for i, text in enumerate(bullets):
        line_y = y + (i * BULLET_GAP_Y)

        # Punto bullet en bold gris claro
        draw.text(
            (x + BULLET_DOT_OFFSET_X, line_y),
            "•",
            font=bullet_font,
            fill=BULLET_COLOR
        )

        # Texto bullet en bold gris claro
        draw.text(
            (x + BULLET_TEXT_OFFSET_X, line_y),
            text,
            font=bullet_font,
            fill=BULLET_COLOR
        )

# =========================
# Usage example
# =========================
bullets = [bullet1, bullet2, bullet3]
draw_bullets(draw, bullets, x=BULLET_X, y=BULLET_Y)
