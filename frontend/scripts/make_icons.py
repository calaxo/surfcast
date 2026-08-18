"""Génère les icônes PWA de Surfcast (fond nuit + soleil couchant + vagues).
   python scripts/make_icons.py   → écrit dans frontend/public/
"""
import math
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
os.makedirs(OUT, exist_ok=True)


def render(size: int) -> Image.Image:
    S = size
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # fond dégradé vertical nuit (haut) -> bleu (bas)
    top, bot = (11, 22, 34), (18, 52, 78)
    for y in range(S):
        t = y / S
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (S, y)], fill=c + (255,))

    # soleil couchant (disque orange) bas-centre
    sun_r = int(S * 0.16)
    cx, cy = S // 2, int(S * 0.60)
    for r in range(sun_r, 0, -1):
        t = r / sun_r
        col = (int(255 - 20 * (1 - t)), int(150 + 60 * (1 - t)), int(40 + 30 * (1 - t)))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,))

    # vagues cyan (3 sinus superposés, opacité décroissante)
    for k, (yc, amp, alpha, col) in enumerate([
        (0.68, 0.045, 255, (56, 189, 248)),
        (0.78, 0.05, 210, (80, 205, 250)),
        (0.88, 0.055, 160, (120, 220, 252)),
    ]):
        pts = []
        for x in range(0, S + 1, max(1, S // 120)):
            y = yc * S + amp * S * math.sin(2 * math.pi * (x / S) * 2 + k)
            pts.append((x, y))
        d.line(pts, fill=col + (alpha,), width=max(2, S // 40), joint="curve")

    return img


def rounded(img: Image.Image, radius_frac=0.22) -> Image.Image:
    """Coins arrondis (icône 'any', non maskable)."""
    S = img.size[0]
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S, S], int(S * radius_frac), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def main():
    base512 = render(512)
    # maskable (fond plein carré, pas de coins arrondis — l'OS applique son masque)
    base512.save(os.path.join(OUT, "maskable-512.png"))
    # 'any' arrondies
    rounded(base512).resize((512, 512)).save(os.path.join(OUT, "pwa-512x512.png"))
    rounded(render(192)).save(os.path.join(OUT, "pwa-192x192.png"))
    rounded(render(180)).save(os.path.join(OUT, "apple-touch-icon.png"))
    render(64).save(os.path.join(OUT, "favicon.png"))
    print("Icônes écrites dans", OUT)
    print(os.listdir(OUT))


if __name__ == "__main__":
    main()
