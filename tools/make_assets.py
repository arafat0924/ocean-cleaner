# Makes the placeholder images and sounds for Ocean Cleaner.
# Only files that do not exist yet are created, so your own pictures are never overwritten.
# Run:  python tools/make_assets.py          (add --force to remake everything)
import os
import sys
import math
import random
import wave
import struct

os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, 'images')
SND = os.path.join(ROOT, 'sounds')
FORCE = '--force' in sys.argv

pygame.init()
pygame.display.set_mode((1, 1))
os.makedirs(IMG, exist_ok=True)
os.makedirs(SND, exist_ok=True)
made = []


def need(path):
    return FORCE or not os.path.exists(path)


def save(surf, name):
    path = os.path.join(IMG, name)
    if need(path):
        pygame.image.save(surf, path)
        made.append(name)


def canvas(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def font(size, bold=True):
    return pygame.font.SysFont('arial', size, bold=bold)


# ---------------- backgrounds (480 x 852, top and bottom edges match) ----------------
def background(name, top, bottom, extra):
    w, h = 480, 852
    s = pygame.Surface((w, h))
    # colour goes top -> bottom -> top again, so the picture loops without a line
    for y in range(h):
        k = math.sin(math.pi * y / h)
        c = [int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)]
        pygame.draw.line(s, c, (0, y), (w, y))
    rnd = random.Random(name)
    # light rays / dots, drawn three times (y, y-h, y+h) so they wrap around
    for _ in range(90):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(1, 3)
        col = [min(255, c + 40) for c in s.get_at((x, y % h))[:3]]
        for dy in (-h, 0, h):
            pygame.draw.circle(s, col, (x, y + dy), r)
    extra(s, rnd)
    path = os.path.join(IMG, name)
    if need(path):
        pygame.image.save(s, path)
        made.append(name)


def sea_extra(s, rnd):
    for _ in range(18):           # waves of light
        x, y = rnd.randint(0, 480), rnd.randint(0, 852)
        for dy in (-852, 0, 852):
            pygame.draw.arc(s, (90, 160, 220), (x, y + dy, 70, 20), 0.3, 2.8, 2)


def deep_extra(s, rnd):
    for _ in range(16):           # rocks and glowing dots
        x, y = rnd.randint(0, 480), rnd.randint(0, 852)
        for dy in (-852, 0, 852):
            pygame.draw.ellipse(s, (20, 30, 60), (x, y + dy, rnd.randint(40, 90), rnd.randint(20, 40)))
            pygame.draw.circle(s, (80, 220, 200), (x + 20, y + dy - 10), 2)


background('bg_sea.jpg', (25, 100, 180), (10, 60, 140), sea_extra)
background('bg_deep.jpg', (10, 40, 90), (5, 15, 45), deep_extra)


# ---------------- player ----------------
def submarine(body):
    s = canvas(64, 80)
    pygame.draw.rect(s, (60, 60, 70), (29, 0, 6, 14))                 # periscope
    pygame.draw.ellipse(s, body, (10, 8, 44, 64))                     # body
    pygame.draw.ellipse(s, tuple(max(0, c - 50) for c in body), (10, 8, 44, 64), 3)
    pygame.draw.circle(s, (180, 230, 255), (32, 32), 10)              # window
    pygame.draw.circle(s, (40, 60, 80), (32, 32), 10, 3)
    pygame.draw.circle(s, (255, 255, 255), (28, 28), 3)
    pygame.draw.rect(s, (60, 60, 70), (2, 44, 10, 18), border_radius=3)   # side engines
    pygame.draw.rect(s, (60, 60, 70), (52, 44, 10, 18), border_radius=3)
    pygame.draw.polygon(s, (90, 90, 100), [(22, 70), (42, 70), (32, 80)])  # propeller
    return s


save(submarine((250, 200, 40)), 'sub.png')
save(submarine((240, 80, 70)), 'sub_hurt.png')

s = canvas(16, 24)
pygame.draw.ellipse(s, (220, 255, 220), (0, 0, 16, 24), 2)
for i in range(4, 16, 4):
    pygame.draw.line(s, (200, 255, 200), (i, 2), (i, 22))
for j in range(5, 22, 5):
    pygame.draw.line(s, (200, 255, 200), (2, j), (14, j))
save(s, 'net.png')

s = canvas(100, 100)
pygame.draw.circle(s, (120, 230, 255, 70), (50, 50), 48)
pygame.draw.circle(s, (160, 240, 255, 220), (50, 50), 48, 3)
save(s, 'shield.png')

s = canvas(12, 12)
pygame.draw.circle(s, (220, 240, 255, 160), (6, 6), 5)
pygame.draw.circle(s, (255, 255, 255, 230), (6, 6), 5, 1)
save(s, 'bubble.png')

# ---------------- trash ----------------
s = canvas(24, 48)
pygame.draw.rect(s, (130, 200, 240, 200), (2, 14, 20, 34), border_radius=6)
pygame.draw.rect(s, (130, 200, 240, 200), (8, 4, 8, 12))
pygame.draw.rect(s, (30, 90, 200), (7, 0, 10, 6))
pygame.draw.rect(s, (240, 240, 255), (2, 26, 20, 8))
save(s, 'bottle.png')

s = canvas(48, 48)
pygame.draw.polygon(s, (240, 240, 245, 210), [(6, 14), (42, 14), (46, 46), (2, 46)])
pygame.draw.arc(s, (230, 230, 235), (8, 0, 12, 20), 0, math.pi, 3)
pygame.draw.arc(s, (230, 230, 235), (28, 0, 12, 20), 0, math.pi, 3)
pygame.draw.line(s, (200, 200, 210), (14, 22), (18, 40), 2)
pygame.draw.line(s, (200, 200, 210), (32, 20), (30, 42), 2)
save(s, 'bag.png')

s = canvas(28, 36)
pygame.draw.rect(s, (210, 40, 40), (2, 4, 24, 28), border_radius=3)
pygame.draw.rect(s, (200, 200, 210), (2, 0, 24, 6), border_radius=3)
pygame.draw.rect(s, (200, 200, 210), (2, 30, 24, 6), border_radius=3)
pygame.draw.rect(s, (255, 255, 255), (5, 12, 18, 6))
save(s, 'can.png')


def oil(w, h):
    s = canvas(w, h)
    rnd = random.Random(w)
    for _ in range(9):
        ew, eh = rnd.randint(w // 3, w // 2), rnd.randint(h // 3, h // 2)
        x, y = rnd.randint(0, w - ew), rnd.randint(0, h - eh)
        pygame.draw.ellipse(s, (15, 15, 20), (x, y, ew, eh))
    pygame.draw.ellipse(s, (15, 15, 20), (w // 6, h // 6, w * 2 // 3, h * 2 // 3))
    pygame.draw.arc(s, (120, 60, 200), (w // 4, h // 4, w // 2, h // 3), 0.5, 2.6, 2)
    pygame.draw.arc(s, (40, 180, 120), (w // 3, h // 3, w // 3, h // 4), 0.5, 2.6, 2)
    return s


save(oil(96, 64), 'oil_big.png')
save(oil(48, 32), 'oil_small.png')

s = canvas(40, 52)
pygame.draw.rect(s, (200, 160, 30), (0, 2, 40, 48), border_radius=6)
for y in (10, 40):
    pygame.draw.line(s, (120, 90, 20), (0, y), (39, y), 3)
pygame.draw.circle(s, (20, 20, 20), (20, 25), 10)
for a in (90, 210, 330):
    r = math.radians(a)
    pts = [(20, 25), (20 + 10 * math.cos(r - 0.5), 25 - 10 * math.sin(r - 0.5)),
           (20 + 10 * math.cos(r + 0.5), 25 - 10 * math.sin(r + 0.5))]
    pygame.draw.polygon(s, (230, 200, 40), pts)
pygame.draw.circle(s, (20, 20, 20), (20, 25), 3)
save(s, 'barrel.png')

# ---------------- sea life ----------------
s = canvas(56, 32)
pygame.draw.polygon(s, (240, 130, 30), [(40, 16), (56, 2), (56, 30)])
pygame.draw.ellipse(s, (255, 160, 40), (0, 2, 46, 28))
pygame.draw.ellipse(s, (255, 255, 255), (8, 8, 10, 10))
pygame.draw.circle(s, (0, 0, 0), (12, 13), 3)
pygame.draw.line(s, (220, 110, 20), (24, 6), (24, 26), 3)
save(s, 'fish_left.png')
save(pygame.transform.flip(s, True, False), 'fish_right.png')


def turtle(trapped):
    s = canvas(64, 56)
    for x, y in ((6, 6), (46, 6), (6, 40), (46, 40)):
        pygame.draw.ellipse(s, (110, 170, 90), (x, y, 14, 12))
    pygame.draw.ellipse(s, (130, 190, 100), (24, 0, 16, 14))       # head
    pygame.draw.circle(s, (0, 0, 0), (28, 5), 2)
    pygame.draw.circle(s, (0, 0, 0), (36, 5), 2)
    pygame.draw.ellipse(s, (60, 120, 60), (12, 10, 40, 40))         # shell
    for cx, cy in ((32, 22), (24, 32), (40, 32), (32, 40)):
        pygame.draw.circle(s, (90, 150, 80), (cx, cy), 6)
    if trapped:
        pygame.draw.ellipse(s, (240, 240, 245, 190), (4, 8, 56, 44))
        for i in range(8, 60, 10):
            pygame.draw.line(s, (255, 255, 255), (i, 10), (i - 6, 50), 2)
    return s


save(turtle(False), 'turtle.png')
save(turtle(True), 'turtle_trapped.png')

s = canvas(40, 56)
pygame.draw.ellipse(s, (240, 130, 210, 200), (2, 0, 36, 28))
pygame.draw.rect(s, (0, 0, 0, 0), (0, 18, 40, 12))
for i, x in enumerate(range(8, 36, 6)):
    pts = [(x + int(3 * math.sin(y / 4 + i)), y) for y in range(16, 56, 4)]
    pygame.draw.lines(s, (250, 170, 230, 220), False, pts, 2)
pygame.draw.circle(s, (255, 255, 255, 230), (14, 9), 3)
save(s, 'jelly.png')

# ---------------- boss ----------------
s = canvas(240, 120)
pygame.draw.rect(s, (90, 90, 95), (150, 0, 26, 40))                # chimney
pygame.draw.rect(s, (200, 50, 40), (150, 8, 26, 8))
pygame.draw.polygon(s, (70, 70, 80), [(0, 50), (240, 50), (210, 105), (30, 105)])   # hull
pygame.draw.rect(s, (110, 110, 120), (40, 30, 140, 22))
for x in range(52, 170, 22):
    pygame.draw.rect(s, (250, 220, 120), (x, 36, 12, 10))
pygame.draw.rect(s, (40, 40, 45), (100, 100, 40, 20))              # waste pipe
pygame.draw.ellipse(s, (20, 20, 20), (104, 108, 32, 12))
txt = font(18).render('POLLUTER', True, (230, 230, 230))
s.blit(txt, (120 - txt.get_width() // 2, 70))
save(s, 'boss.png')

# ---------------- power-ups ----------------
def badge(color, draw_symbol, name, size=36):
    s = canvas(size, size)
    pygame.draw.circle(s, color, (size // 2, size // 2), size // 2 - 1)
    pygame.draw.circle(s, (255, 255, 255), (size // 2, size // 2), size // 2 - 1, 2)
    draw_symbol(s, size)
    save(s, name)


def sym_triple(s, n):
    for dx in (-8, 0, 8):
        pygame.draw.line(s, (255, 255, 255), (n // 2, n - 9), (n // 2 + dx, 9), 3)


def sym_vacuum(s, n):
    pts = [(n / 2 + (t / 2) * math.cos(t), n / 2 + (t / 2) * math.sin(t)) for t in [i / 3 for i in range(40)]]
    pygame.draw.lines(s, (255, 255, 255), False, pts, 2)


def sym_shield(s, n):
    pygame.draw.polygon(s, (255, 255, 255), [(n / 2, 7), (n - 9, 11), (n - 11, n - 13), (n / 2, n - 6), (11, n - 13), (9, 11)], 3)


def sym_heart(s, n):
    pygame.draw.circle(s, (255, 255, 255), (n // 2 - 5, n // 2 - 3), 6)
    pygame.draw.circle(s, (255, 255, 255), (n // 2 + 5, n // 2 - 3), 6)
    pygame.draw.polygon(s, (255, 255, 255), [(n // 2 - 11, n // 2 - 1), (n // 2 + 11, n // 2 - 1), (n // 2, n // 2 + 11)])


badge((240, 140, 30), sym_triple, 'pu_triple.png')
badge((140, 80, 220), sym_vacuum, 'pu_vacuum.png')
badge((40, 160, 230), sym_shield, 'pu_shield.png')
badge((220, 50, 80), sym_heart, 'pu_health.png')
badge((140, 80, 220), sym_vacuum, 'vac_icon.png', 20)

s = canvas(24, 24)
pygame.draw.circle(s, (230, 40, 60), (7, 8), 6)
pygame.draw.circle(s, (230, 40, 60), (17, 8), 6)
pygame.draw.polygon(s, (230, 40, 60), [(1, 10), (23, 10), (12, 22)])
save(s, 'heart.png')

# ---------------- effects ----------------
s = canvas(64, 64)
for a in range(0, 360, 30):
    r = math.radians(a)
    pygame.draw.circle(s, (200, 240, 255, 220), (32 + int(22 * math.cos(r)), 32 + int(22 * math.sin(r))), 4)
pygame.draw.circle(s, (230, 250, 255, 160), (32, 32), 12, 3)
save(s, 'splash.png')

s = canvas(80, 80)
pts = []
for i in range(16):
    r = 38 if i % 2 == 0 else 18
    a = math.pi * 2 * i / 16
    pts.append((40 + r * math.cos(a), 40 + r * math.sin(a)))
pygame.draw.polygon(s, (255, 150, 30), pts)
pygame.draw.circle(s, (255, 240, 120), (40, 40), 14)
save(s, 'boom.png')

# ---------------- menu ----------------
s = canvas(400, 120)
t1 = font(54).render('OCEAN', True, (255, 255, 255))
t2 = font(54).render('CLEANER', True, (120, 240, 200))
for dx, dy in ((3, 3),):
    s.blit(font(54).render('OCEAN', True, (10, 40, 80)), (200 - t1.get_width() // 2 + dx, 2 + dy))
    s.blit(font(54).render('CLEANER', True, (10, 40, 80)), (200 - t2.get_width() // 2 + dx, 52 + dy))
s.blit(t1, (200 - t1.get_width() // 2, 2))
s.blit(t2, (200 - t2.get_width() // 2, 52))
pts = [(x, 112 + 5 * math.sin(x / 15)) for x in range(20, 381, 4)]
pygame.draw.lines(s, (120, 240, 200), False, pts, 3)
save(s, 'logo.png')


def button(label, name, hover):
    s = canvas(200, 60)
    fill = (60, 200, 170) if hover else (30, 130, 170)
    pygame.draw.rect(s, (10, 40, 70), (0, 4, 200, 56), border_radius=18)
    pygame.draw.rect(s, fill, (0, 0, 200, 54), border_radius=18)
    pygame.draw.rect(s, (255, 255, 255) if hover else (180, 230, 255), (0, 0, 200, 54), 3, border_radius=18)
    t = font(26).render(label, True, (255, 255, 255))
    s.blit(t, (100 - t.get_width() // 2, 27 - t.get_height() // 2))
    save(s, name)


for label in ('START', 'HELP', 'QUIT'):
    button(label, 'btn_%s.png' % label.lower(), False)
    button(label, 'btn_%s_hover.png' % label.lower(), True)


# ---------------- sounds (22050 Hz, 16 bit mono wav) ----------------
RATE = 22050


def write_wav(name, samples):
    path = os.path.join(SND, name)
    if not need(path):
        return
    with wave.open(path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, v)) * 30000)) for v in samples))
    made.append(name)


def tone(freqs, length, vol=0.5, wave_type='sine', fade=True):
    n = int(RATE * length)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        f = freqs[0] + (freqs[-1] - freqs[0]) * t if len(freqs) == 2 else freqs[min(len(freqs) - 1, int(t * len(freqs)))]
        phase += 2 * math.pi * f / RATE
        if wave_type == 'square':
            v = 1 if math.sin(phase) > 0 else -1
        elif wave_type == 'noise':
            v = random.uniform(-1, 1)
        else:
            v = math.sin(phase)
        env = (1 - t) if fade else 1
        out.append(v * vol * env * min(1, i / 200))
    return out


random.seed(7)
write_wav('shoot.wav', tone([900, 400], 0.12, 0.35, 'square'))
write_wav('collect.wav', tone([660, 880, 1320], 0.18, 0.4))
write_wav('hurt.wav', [a * 0.6 + b * 0.4 for a, b in zip(tone([200, 80], 0.35, 0.6, 'square'), tone([0], 0.35, 0.5, 'noise'))])
write_wav('oil.wav', tone([160, 60], 0.2, 0.6))
write_wav('powerup.wav', tone([523, 659, 784, 1046], 0.4, 0.4, 'square'))
swoosh = tone([0], 0.6, 0.5, 'noise', False)
write_wav('vacuum.wav', [v * (0.3 + 0.7 * i / len(swoosh)) for i, v in enumerate(swoosh)])
write_wav('rescue.wav', tone([784, 988, 1175, 1568], 0.45, 0.4))
write_wav('penalty.wav', tone([300, 200], 0.3, 0.45, 'square'))
write_wav('boss_hit.wav', tone([120, 70], 0.15, 0.7, 'square'))
write_wav('level.wav', tone([523, 523, 659, 784, 1046, 1046], 0.9, 0.4, 'square'))
write_wav('gameover.wav', tone([440, 392, 330, 262], 1.0, 0.45, 'square'))


def music_loop():
    notes = [220, 261.6, 329.6, 261.6, 196, 246.9, 293.7, 246.9,
             174.6, 220, 261.6, 220, 196, 246.9, 293.7, 329.6]
    beat = 0.5
    out = []
    for n in notes:
        k = int(RATE * beat)
        for i in range(k):
            t = i / RATE
            env = math.exp(-3 * i / k)
            v = 0.25 * env * math.sin(2 * math.pi * n * t) + 0.08 * math.sin(2 * math.pi * n / 2 * t)
            out.append(v)
    return out


write_wav('music_loop.wav', music_loop())

print('created %d files' % len(made))
for m in made:
    print('  ' + m)
