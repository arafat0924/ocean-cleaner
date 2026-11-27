# Makes the menu buttons, level tiles, stars, lock and arrow pictures.
# Run:  python tools/make_ui.py      (always overwrites the UI pictures it makes)
import os
import math

os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, 'images')
FONT = os.path.join(ROOT, 'fonts', 'lilitaone.ttf')
K = 3                       # draw 3x bigger, then shrink: smooth edges

pygame.init()
pygame.display.set_mode((1, 1))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def lighter(c, k):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def darker(c, k):
    return tuple(int(v * (1 - k)) for v in c)


def rounded_gradient(w, h, top, bottom, radius):
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        pygame.draw.line(grad, lerp(top, bottom, y / max(1, h - 1)) + (255,), (0, y), (w, y))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return grad


def glow(surf, rect, color, radius, steps=8):
    for i in range(steps, 0, -1):
        a = int(70 * (1 - i / steps) + 10)
        r = pygame.Rect(rect).inflate(i * 2 * K, i * 2 * K)
        s = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(s, color + (a,), r, border_radius=radius + i * K)
        surf.blit(s, (0, 0))


def text_outline(surf, text, size, center, color=(255, 255, 255), outline=(10, 30, 50)):
    f = pygame.font.Font(FONT, size)
    base = f.render(text, True, color)
    edge = f.render(text, True, outline)
    x, y = center[0] - base.get_width() // 2, center[1] - base.get_height() // 2
    for dx in range(-K * 2, K * 2 + 1, K):
        for dy in range(-K * 2, K * 3 + 1, K):
            surf.blit(edge, (x + dx, y + dy))
    surf.blit(base, (x, y))


def icon(surf, kind, cx, cy, r, color=(255, 255, 255)):
    if kind == 'play':
        pygame.draw.polygon(surf, color, [(cx - r * 0.45, cy - r * 0.62), (cx - r * 0.45, cy + r * 0.62), (cx + r * 0.65, cy)])
    elif kind == 'help':
        f = pygame.font.Font(FONT, int(r * 1.7))
        q = f.render('?', True, color)
        surf.blit(q, (cx - q.get_width() // 2, cy - q.get_height() // 2 + r * 0.05))
    elif kind == 'quit':
        w = max(3, int(r * 0.28))
        pygame.draw.line(surf, color, (cx - r * 0.5, cy - r * 0.5), (cx + r * 0.5, cy + r * 0.5), w)
        pygame.draw.line(surf, color, (cx - r * 0.5, cy + r * 0.5), (cx + r * 0.5, cy - r * 0.5), w)
    elif kind in ('next', 'prev', 'back'):
        s = 1 if kind == 'next' else -1
        w = max(3, int(r * 0.3))
        pygame.draw.line(surf, color, (cx - s * r * 0.15, cy - r * 0.55), (cx + s * r * 0.4, cy), w)
        pygame.draw.line(surf, color, (cx + s * r * 0.4, cy), (cx - s * r * 0.15, cy + r * 0.55), w)
        if kind == 'back':
            pygame.draw.line(surf, color, (cx + r * 0.4, cy), (cx - r * 0.3, cy), w)
    elif kind == 'retry':
        w = max(3, int(r * 0.26))
        rect = pygame.Rect(0, 0, r * 1.2, r * 1.2)
        rect.center = (cx, cy)
        pygame.draw.arc(surf, color, rect, 0.6, 5.6, w)
        tip = (cx + r * 0.5, cy - r * 0.35)
        pygame.draw.polygon(surf, color, [tip, (tip[0] - r * 0.45, tip[1] - r * 0.15), (tip[0] - r * 0.05, tip[1] + r * 0.35)])
    elif kind == 'grid':
        q = r * 0.3
        for dx in (-1, 1):
            for dy in (-1, 1):
                pygame.draw.rect(surf, color, (cx + dx * q * 1.15 - q * 0.9, cy + dy * q * 1.15 - q * 0.9, q * 1.8, q * 1.8),
                                 border_radius=int(q * 0.4))


def save(surf, name):
    w, h = surf.get_size()
    pygame.image.save(pygame.transform.smoothscale(surf, (w // K, h // K)), os.path.join(IMG, name))


def big_button(name, label, kind, top, bottom, w=250, h=66):
    for hover in (False, True):
        W, H = w * K, h * K
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        pad = 7 * K
        body = pygame.Rect(pad, pad - (2 * K if hover else 0), W - pad * 2, H - pad * 2 - 4 * K)
        rad = body.h // 2
        if hover:
            glow(s, body, (255, 230, 120), rad, 6)
        shadow = body.move(0, 5 * K)
        pygame.draw.rect(s, (5, 20, 40, 170), shadow, border_radius=rad)
        t, b = (lighter(top, 0.25), lighter(bottom, 0.15)) if hover else (top, bottom)
        s.blit(rounded_gradient(body.w, body.h, t, b, rad), body.topleft)
        gloss = pygame.Surface((body.w, body.h // 2), pygame.SRCALPHA)
        pygame.draw.rect(gloss, (255, 255, 255, 55), (body.h * 0.25, 4 * K, body.w - body.h * 0.5, body.h // 2 - 6 * K),
                         border_radius=body.h // 4)
        s.blit(gloss, body.topleft)
        pygame.draw.rect(s, (255, 255, 255, 255 if hover else 200), body, 3 * K, border_radius=rad)
        cr = body.h * 0.34
        c = (body.left + body.h * 0.55, body.centery)
        pygame.draw.circle(s, darker(bottom, 0.35) + (230,), c, cr)
        pygame.draw.circle(s, (255, 255, 255, 220), c, cr, 2 * K)
        icon(s, kind, c[0], c[1], cr * 0.75)
        text_outline(s, label, int(body.h * 0.52), (body.centerx + body.h * 0.28, body.centery - K), )
        save(s, name + ('_hover' if hover else '') + '.png')


def round_button(name, kind, color, size=56):
    for hover in (False, True):
        S = size * K
        s = pygame.Surface((S, S), pygame.SRCALPHA)
        c = (S // 2, S // 2 - (K if hover else 0))
        r = S // 2 - 5 * K
        if hover:
            for i in range(5, 0, -1):
                pygame.draw.circle(s, (255, 230, 120, 40), c, r + i * K)
        pygame.draw.circle(s, (5, 20, 40, 160), (c[0], c[1] + 3 * K), r)
        top = lighter(color, 0.3 if hover else 0.1)
        g = rounded_gradient(r * 2, r * 2, top, darker(color, 0.2), r)
        s.blit(g, (c[0] - r, c[1] - r))
        pygame.draw.circle(s, (255, 255, 255, 255 if hover else 210), c, r, 2 * K)
        icon(s, kind, c[0], c[1], r * 0.62)
        save(s, name + ('_hover' if hover else '') + '.png')


THEME_COLORS = {'coast': ((60, 210, 200), (15, 120, 140)),
                'sea': ((70, 150, 240), (20, 70, 170)),
                'deep': ((80, 80, 170), (25, 25, 80))}


def tile(name, top, bottom, locked=False, hover=False, size=82):
    S = size * K
    s = pygame.Surface((S, S), pygame.SRCALPHA)
    body = pygame.Rect(4 * K, 3 * K - (2 * K if hover else 0), S - 8 * K, S - 10 * K)
    rad = 16 * K
    if hover:
        glow(s, body, (255, 230, 120), rad, 5)
    pygame.draw.rect(s, (5, 20, 40, 170), body.move(0, 5 * K), border_radius=rad)
    if locked:
        top, bottom = (95, 105, 120), (55, 62, 75)
    s.blit(rounded_gradient(body.w, body.h, lighter(top, 0.2) if hover else top, bottom, rad), body.topleft)
    gloss = pygame.Surface((body.w, body.h), pygame.SRCALPHA)
    pygame.draw.rect(gloss, (255, 255, 255, 45), (8 * K, 5 * K, body.w - 16 * K, body.h * 0.4), border_radius=rad)
    s.blit(gloss, body.topleft)
    pygame.draw.rect(s, (255, 255, 255, 255 if hover else 190), body, 2 * K, border_radius=rad)
    if locked:
        cx, cy = body.centerx, body.centery + 2 * K
        pygame.draw.arc(s, (230, 235, 240), (cx - 11 * K, cy - 22 * K, 22 * K, 26 * K), 0, math.pi, 4 * K)
        pygame.draw.rect(s, (230, 235, 240), (cx - 15 * K, cy - 8 * K, 30 * K, 24 * K), border_radius=5 * K)
        pygame.draw.circle(s, (70, 78, 92), (cx, cy + 3 * K), 4 * K)
    save(s, name)


def star(name, on, size=18):
    S = size * K
    s = pygame.Surface((S, S), pygame.SRCALPHA)
    pts = []
    for i in range(10):
        r = S * 0.48 if i % 2 == 0 else S * 0.21
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((S / 2 + r * math.cos(a), S / 2 + 1 * K + r * math.sin(a)))
    pygame.draw.polygon(s, (255, 205, 40) if on else (40, 55, 80), pts)
    pygame.draw.polygon(s, (130, 80, 10) if on else (110, 125, 150), pts, 2 * K)
    save(s, name)


big_button('btn_start', 'START', 'play', (95, 225, 150), (20, 150, 95))
big_button('btn_help', 'HELP', 'help', (90, 175, 245), (25, 95, 200))
big_button('btn_quit', 'QUIT', 'quit', (255, 135, 110), (205, 60, 60))
big_button('pb_next', 'NEXT', 'next', (95, 225, 150), (20, 150, 95), 170, 58)
big_button('pb_retry', 'RETRY', 'retry', (255, 195, 80), (225, 120, 25), 170, 58)
big_button('pb_levels', 'LEVELS', 'grid', (90, 175, 245), (25, 95, 200), 170, 58)
round_button('btn_prev', 'prev', (40, 140, 220))
round_button('btn_next', 'next', (40, 140, 220))
round_button('btn_back', 'back', (230, 100, 70))
for theme, (top, bottom) in THEME_COLORS.items():
    tile('tile_%s.png' % theme, top, bottom)
    tile('tile_%s_hover.png' % theme, top, bottom, hover=True)
tile('tile_locked.png', None, None, locked=True)
star('star_on.png', True)
star('star_off.png', False)
star('star_big_on.png', True, 44)
star('star_big_off.png', False, 44)
print('UI pictures made')
