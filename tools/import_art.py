# Copies your own pictures into the game's images folder at the right size.
#   - empty transparent border is cut off (collision uses the picture's rectangle)
#   - the picture is scaled down to fit its box, keeping its shape
#   - square icons (net, heart, power-ups, faces) stay square
# Run:  python tools/import_art.py                 (reads E:\hw\Project\images)
#       python tools/import_art.py other\folder
import os
import sys

os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), 'images')
DST = os.path.join(ROOT, 'images')

# name: (max width, max height, square canvas?)
SIZES = {
    'sub': (64, 80, False), 'sub_hurt': (64, 80, False),
    'net': (24, 24, True), 'shield': (100, 100, True),
    'bottle': (24, 48, False), 'can': (28, 36, False), 'bag': (48, 48, False),
    'oil_big': (96, 64, False), 'oil_small': (48, 32, False), 'barrel': (40, 52, False),
    'fish_left': (56, 32, False), 'fish_right': (56, 32, False),
    'turtle': (64, 56, False), 'turtle_trapped': (64, 56, False), 'jelly': (40, 56, False),
    'boss': (240, 120, False),
    'pu_triple': (36, 36, True), 'pu_vacuum': (36, 36, True), 'pu_shield': (36, 36, True),
    'pu_health': (36, 36, True), 'vac_icon': (20, 20, True), 'heart': (24, 24, True),
    'splash': (64, 64, True), 'boom': (80, 80, True), 'bubble': (12, 12, True),
    'logo': (400, 120, False),
    'face': (128, 128, True), 'face_small': (48, 48, True),
    'face_happy': (48, 48, True), 'face_sad': (48, 48, True),
}
# made from another picture when you did not draw them yourself
DERIVED = {'oil_small': 'oil_big', 'vac_icon': 'pu_vacuum'}
WHITE_BACKGROUND = {'boss'}       # pictures saved without transparency
MAKE_VISIBLE = {'net'}            # thin, see-through pictures that get lost in blue water
GLOW = {'logo'}                   # dark pictures that need a light glow on dark water


def remove_white_background(surf, tol=28):
    # flood fill from the border: near-white pixels connected to the edge become transparent
    w, h = surf.get_size()
    seen = set()
    stack = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] + \
            [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        seen.add((x, y))
        c = surf.get_at((x, y))
        if c.a == 0 or (255 - c.r <= tol and 255 - c.g <= tol and 255 - c.b <= tol):
            surf.set_at((x, y), (0, 0, 0, 0))
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return surf


def make_visible(surf):
    # stronger, brighter strands and a dark outline around them
    w, h = surf.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(surf, 20)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(mask.to_surface(setcolor=(10, 25, 40, 230), unsetcolor=(0, 0, 0, 0)), (dx, dy))
    strong = surf.copy()
    for y in range(h):
        for x in range(w):
            c = strong.get_at((x, y))
            if c.a > 20:
                strong.set_at((x, y), (min(255, c.r + 70), min(255, c.g + 70), min(255, c.b + 60), min(255, c.a * 3)))
    out.blit(strong, (0, 0))
    return out


def add_glow(surf, radius=4):
    w, h = surf.get_size()
    out = pygame.Surface((w + radius * 2, h + radius * 2), pygame.SRCALPHA)
    glow = pygame.mask.from_surface(surf, 20).to_surface(setcolor=(235, 250, 255, 70), unsetcolor=(0, 0, 0, 0))
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                out.blit(glow, (radius + dx, radius + dy))
    out.blit(surf, (radius, radius))
    return out


def trim(surf):
    r = surf.get_bounding_rect(min_alpha=12)
    return surf.subsurface(r).copy() if r.w and r.h else surf


def fit(surf, max_w, max_h, square):
    k = min(max_w / surf.get_width(), max_h / surf.get_height(), 1)
    w, h = max(1, round(surf.get_width() * k)), max(1, round(surf.get_height() * k))
    small = pygame.transform.smoothscale(surf, (w, h)) if (w, h) != surf.get_size() else surf
    if not square:
        return small
    canvas = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
    canvas.blit(small, ((max_w - w) // 2, (max_h - h) // 2))
    return canvas


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    done = []
    for name, (mw, mh, square) in SIZES.items():
        src = os.path.join(SRC, name + '.png')
        if not os.path.exists(src) and name in DERIVED:
            src = os.path.join(SRC, DERIVED[name] + '.png')
        if not os.path.exists(src):
            continue
        surf = pygame.image.load(src).convert_alpha()
        corners = [surf.get_at(p).a for p in ((0, 0), (surf.get_width() - 1, 0),
                                                (0, surf.get_height() - 1), (surf.get_width() - 1, surf.get_height() - 1))]
        if name in WHITE_BACKGROUND and min(corners) == 255:     # only when it has no transparency yet
            surf = remove_white_background(surf)
        if name in MAKE_VISIBLE:
            surf = make_visible(surf)
        if name in GLOW:
            surf = add_glow(fit(trim(surf), mw - 8, mh - 8, square))
        else:
            surf = fit(trim(surf), mw, mh, square)
        pygame.image.save(surf, os.path.join(DST, name + '.png'))
        done.append('%-15s %3dx%-3d  <- %s' % (name, surf.get_width(), surf.get_height(), os.path.basename(src)))
    print('\n'.join(done))
    print('%d pictures copied into %s' % (len(done), DST))


if __name__ == '__main__':
    main()
