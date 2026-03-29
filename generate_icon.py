"""Generate a Win98-style stopwatch icon for WoTiTi."""

from PIL import Image, ImageDraw


def draw_stopwatch(size: int) -> Image.Image:
    """Draw a pixel-art Win98-style stopwatch icon at the given size."""
    # Work at 64x64 base, then resize
    base = 64
    img = Image.new("RGBA", (base, base), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Win98 colors
    face_color = (192, 192, 192)       # #C0C0C0 — classic Win98 gray
    highlight = (255, 255, 255)         # top-left highlight
    shadow = (128, 128, 128)            # bottom-right shadow
    dark_shadow = (64, 64, 64)          # darkest edge
    outline = (0, 0, 0)                 # black outline
    hand_color = (0, 0, 0)             # clock hand
    tick_color = (64, 64, 64)          # hour marks
    button_color = (212, 208, 200)     # #D4D0C8 — Win98 button face
    cyan_accent = (0, 255, 255)        # Synthwave cyan accent

    cx, cy = 32, 35  # center of clock face (shifted down for button on top)
    r = 22           # radius of clock face

    # --- Top button (stopwatch crown) ---
    d.rectangle([28, 6, 36, 14], fill=button_color, outline=outline)
    # 3D effect on button
    d.line([29, 7, 35, 7], fill=highlight)
    d.line([29, 7, 29, 13], fill=highlight)
    d.line([35, 8, 35, 13], fill=shadow)
    d.line([29, 13, 35, 13], fill=shadow)

    # Small stem connecting button to body
    d.rectangle([30, 14, 34, 17], fill=face_color, outline=outline)

    # --- Clock body (circle with 3D bevel) ---
    # Outer dark shadow
    d.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=dark_shadow)
    # Outer highlight (offset)
    d.ellipse([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], fill=shadow)
    # Main outline
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=outline)
    # Face
    d.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=face_color)

    # Inner 3D bevel (sunken effect like Win98 display)
    d.arc([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], 225, 45, fill=shadow, width=1)
    d.arc([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], 45, 225, fill=highlight, width=1)

    # Inner face (slightly lighter)
    d.ellipse([cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4], fill=(212, 208, 200))

    # --- Hour tick marks (12 positions) ---
    import math
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        inner_r = r - 7
        outer_r = r - 4
        x1 = cx + inner_r * math.cos(angle)
        y1 = cy + inner_r * math.sin(angle)
        x2 = cx + outer_r * math.cos(angle)
        y2 = cy + outer_r * math.sin(angle)
        d.line([(x1, y1), (x2, y2)], fill=tick_color, width=1)

    # --- Clock hands ---
    # Minute hand (pointing ~10 o'clock — looks dynamic)
    angle_m = math.radians(300 - 90)
    mx = cx + (r - 8) * math.cos(angle_m)
    my = cy + (r - 8) * math.sin(angle_m)
    d.line([(cx, cy), (mx, my)], fill=hand_color, width=2)

    # Second hand in cyan (pointing ~2 o'clock — synthwave accent)
    angle_s = math.radians(60 - 90)
    sx = cx + (r - 6) * math.cos(angle_s)
    sy = cy + (r - 6) * math.sin(angle_s)
    d.line([(cx, cy), (sx, sy)], fill=cyan_accent, width=1)

    # Center dot
    d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=hand_color)

    # --- Side buttons (left and right, typical stopwatch) ---
    # Right button (start/stop)
    d.polygon([(cx + r + 1, cy - 6), (cx + r + 5, cy - 8), (cx + r + 5, cy - 2), (cx + r + 1, cy - 2)],
              fill=button_color, outline=outline)
    # Left button (reset)
    d.polygon([(cx - r - 1, cy - 6), (cx - r - 5, cy - 8), (cx - r - 5, cy - 2), (cx - r - 1, cy - 2)],
              fill=button_color, outline=outline)

    # Scale to target size with nearest-neighbor for pixel-art look at small sizes
    if size <= 32:
        return img.resize((size, size), Image.NEAREST)
    return img.resize((size, size), Image.LANCZOS)


def main():
    """Generate multi-size ICO file."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    for s in sizes:
        images.append(draw_stopwatch(s))

    output = "src/assets/wotiti.ico"
    # Save as ICO with multiple sizes
    images[0].save(
        output,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Icon saved: {output}")

    # Also save a PNG preview
    preview = draw_stopwatch(256)
    preview.save("src/assets/wotiti_preview.png")
    print("Preview saved: src/assets/wotiti_preview.png")


if __name__ == "__main__":
    main()
