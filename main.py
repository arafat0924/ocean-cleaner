import os
import sys
import math
import random

# must be read before "import pgzrun", which replaces __file__ with pgzero's own path
BASE = os.path.dirname(os.path.abspath(__file__))

import pgzrun
from pgzero import loaders

if not os.path.isdir(os.path.join(BASE, 'images')):
    BASE = os.path.abspath(loaders.root)      # started with "pgzrun main.py": use the game folder

WIDTH = 480
HEIGHT = 700
TITLE = 'Ocean Cleaner'

SCORE_FILE = os.path.join(BASE, 'highscore.txt')
BG_H = 852
HUD_H = 46

SUB_SPEED = 5
NET_SPEED = 9
FIRE_DELAY = 10          # frames between two nets
MAX_LIVES = 3
MAX_VACUUM = 3
VACUUM_RANGE = 170

LEVELS = [
    {'name': 'Level 1: The Coast', 'bg': 'bg_sea', 'goal': 25, 'spawn': 55, 'scroll': 1,
     'trash': ['bottle', 'bottle', 'can', 'bag'], 'speed': (1.2, 2.0),
     'animals': ['fish'], 'animal_chance': 0.35, 'oil_chance': 0.0},
    {'name': 'Level 2: Open Sea', 'bg': 'bg_sea', 'goal': 35, 'spawn': 45, 'scroll': 1.5,
     'trash': ['bottle', 'can', 'bag', 'bag'], 'speed': (1.5, 2.6),
     'animals': ['fish', 'turtle', 'turtle'], 'animal_chance': 0.4, 'oil_chance': 0.15},
    {'name': 'Level 3: Deep Sea', 'bg': 'bg_deep', 'goal': 30, 'spawn': 40, 'scroll': 2,
     'trash': ['bottle', 'can', 'bag'], 'speed': (1.8, 3.0),
     'animals': ['fish', 'fish', 'turtle', 'jelly'], 'animal_chance': 0.45, 'oil_chance': 0.2},
]

# points when cleaned, ocean damage when it sinks to the bottom, hits needed
TRASH = {
    'bottle':    {'points': 10, 'damage': 5,  'hp': 1},
    'can':       {'points': 10, 'damage': 4,  'hp': 1},
    'bag':       {'points': 15, 'damage': 8,  'hp': 1},
    'oil_big':   {'points': 30, 'damage': 10, 'hp': 3},
    'oil_small': {'points': 10, 'damage': 5,  'hp': 1},
    'barrel':    {'points': 20, 'damage': 8,  'hp': 2},
}

FACTS = [
    'Around 11 million tonnes of plastic go into the ocean every year.',
    'Sea turtles eat plastic bags, which can look and even smell like their food.',
    'A plastic bottle is estimated to take up to 450 years to break down in the sea.',
    'Oil spills cover the feathers of sea birds and the gills of fish.',
    'More than 800 kinds of sea animals are harmed by ocean litter.',
    'Tiny pieces of plastic have been found in the deepest ocean trench.',
    'Using a reusable bottle and bag is the easiest way to help the ocean.',
]


def has_image(name):
    return os.path.exists(os.path.join(BASE, 'images', name + '.png'))


# ---------------- actors that live for the whole game ----------------
bg1 = Actor('bg_sea')
bg2 = Actor('bg_sea')
sub = Actor('sub')
shield_ring = Actor('shield')
boss = Actor('boss')
logo = Actor('logo', center=(WIDTH / 2, 110))
buttons = {
    'start': Actor('btn_start', center=(WIDTH / 2, 400)),
    'help': Actor('btn_help', center=(WIDTH / 2, 470)),
    'quit': Actor('btn_quit', center=(WIDTH / 2, 540)),
}

# ---------------- game state ----------------
state = 'menu'          # menu, help, intro, play, gameover, win
paused = False
muted = False
music_on = False
level = 0
score = 0
high_score = 0
new_record = False
lives = MAX_LIVES
ocean = 100             # ocean health
cleaned = 0             # trash cleaned in this level
frame = 0
spawn_timer = 0
fire_timer = 0
hurt_timer = 0
slow_timer = 0
triple_timer = 0
shield_timer = 0
vacuum_charges = 1
vacuum_fx = 0
boss_active = False
boss_hp = 0
boss_drop_timer = 0
boss_dead_timer = 0
intro_header = ''
end_reason = ''
fact = ''

trash = []
animals = []
nets = []
powerups = []
effects = []            # [actor, frames left]
texts = []              # [text, x, y, frames left, color]
bubbles = []            # [x, y, frames left]


def load_high_score():
    global high_score
    try:
        with open(SCORE_FILE) as f:
            high_score = int(f.read().strip() or 0)
    except (OSError, ValueError):
        high_score = 0


def save_high_score():
    global high_score, new_record
    new_record = score > high_score
    if new_record:
        high_score = score
        try:
            with open(SCORE_FILE, 'w') as f:
                f.write(str(high_score))
        except OSError:
            pass


def play(name):
    if muted:
        return
    try:
        getattr(sounds, name).play()
    except Exception:
        pass        # a missing sound file should not stop the game


def start_music():
    global music_on
    if muted:
        return
    try:
        sounds.music_loop.stop()
        sounds.music_loop.play(-1)
        music_on = True
    except Exception:
        pass


def stop_music():
    global music_on
    music_on = False
    try:
        sounds.music_loop.stop()
    except Exception:
        pass


def float_text(text, x, y, color='white'):
    half = len(text) * 6 + 10          # keep the text inside the window
    x = min(max(x, half), WIDTH - half)
    texts.append([text, x, y, 60, color])


def add_effect(image, pos, frames=18):
    effects.append([Actor(image, center=pos), frames])


# ---------------- starting games and levels ----------------
def new_game():
    global level, score, lives, ocean, vacuum_charges, new_record
    level = 0
    score = 0
    lives = MAX_LIVES
    ocean = 100
    vacuum_charges = 1
    new_record = False
    start_level('')
    start_music()


def start_level(header):
    global cleaned, spawn_timer, fire_timer, hurt_timer, slow_timer, triple_timer, shield_timer
    global vacuum_fx, boss_active, boss_dead_timer, state, paused, intro_header, fact
    cfg = LEVELS[level]
    bg1.image = cfg['bg']
    bg2.image = cfg['bg']
    bg1.x = bg2.x = WIDTH / 2
    bg1.y = BG_H / 2
    bg2.y = BG_H / 2 - BG_H
    sub.image = 'sub'
    sub.pos = (WIDTH / 2, HEIGHT - 80)
    for group in (trash, animals, nets, powerups, effects, texts, bubbles):
        group.clear()
    cleaned = 0
    spawn_timer = fire_timer = hurt_timer = slow_timer = 0
    triple_timer = shield_timer = vacuum_fx = 0
    boss_active = False
    boss_dead_timer = 0
    paused = False
    intro_header = header
    fact = random.choice(FACTS)
    state = 'intro'


def level_complete():
    global level, ocean, vacuum_charges
    play('level')
    ocean = min(100, ocean + 20)
    vacuum_charges = min(MAX_VACUUM, vacuum_charges + 1)
    level += 1
    start_level('Level complete!  Ocean +20, Vacuum +1')


def end_game(reason, won=False):
    global state, end_reason, fact
    if state != 'play':
        return
    end_reason = reason
    fact = random.choice(FACTS)
    save_high_score()
    stop_music()
    play('level' if won else 'gameover')
    state = 'win' if won else 'gameover'


# ---------------- spawning ----------------
def spawn_trash(kind=None, x=None, y=None):
    cfg = LEVELS[level]
    if kind is None:
        kind = random.choice(cfg['trash'])
    t = Actor(kind)
    t.kind = kind
    t.hp = TRASH[kind]['hp']
    t.x = x if x is not None else random.randint(30, WIDTH - 30)
    t.y = y if y is not None else HUD_H - 30
    t.vy = random.uniform(*cfg['speed'])
    t.vx = 0
    t.phase = random.uniform(0, 6.28)
    if kind == 'can':
        t.vy *= 1.3
    if kind in ('oil_big', 'oil_small'):
        t.vy *= 0.7
        t.vx = random.choice((-0.6, 0.6))
    trash.append(t)
    return t


def spawn_animal():
    cfg = LEVELS[level]
    kind = random.choice(cfg['animals'])
    if kind == 'jelly':
        a = Actor('jelly')
        a.x = random.randint(40, WIDTH - 40)
        a.y = HUD_H - 30
        a.vx = 0
        a.vy = random.uniform(0.8, 1.3)
    else:
        from_left = random.random() < 0.5
        if kind == 'fish':
            a = Actor('fish_right' if from_left else 'fish_left')
            speed = random.uniform(1.5, 2.8)
        else:
            a = Actor('turtle')
            speed = random.uniform(0.8, 1.4)
        a.x = -40 if from_left else WIDTH + 40
        a.y = random.randint(HUD_H + 80, HEIGHT - 220)
        a.vx = speed if from_left else -speed
        a.vy = 0.3
    a.kind = kind
    a.trapped = False
    a.phase = random.uniform(0, 6.28)
    animals.append(a)


def drop_powerup(pos):
    p = Actor(random.choice(['pu_triple', 'pu_vacuum', 'pu_shield', 'pu_health']), center=pos)
    p.kind = p.image
    powerups.append(p)


# ---------------- small helpers ----------------
def touching(a, b, keep=0.75):
    # collide with rectangles a bit smaller than the pictures
    ra = Rect(a.left, a.top, a.width, a.height).inflate(-a.width * (1 - keep), -a.height * (1 - keep))
    rb = Rect(b.left, b.top, b.width, b.height).inflate(-b.width * (1 - keep), -b.height * (1 - keep))
    return ra.colliderect(rb)


def clean(t):
    global score, cleaned
    if t in trash:
        trash.remove(t)
    points = TRASH[t.kind]['points']
    score += points
    if not boss_active:
        cleaned += 1
    float_text('+' + str(points), t.x, t.y, 'yellow')
    add_effect('splash', t.pos)
    play('collect')
    if random.random() < 0.08:
        drop_powerup(t.pos)


def hurt_sub(reason):
    global lives, hurt_timer
    if hurt_timer > 0 or shield_timer > 0:
        return
    lives -= 1
    hurt_timer = 90
    sub.image = 'sub_hurt'
    play('hurt')
    float_text(reason, sub.x, sub.y - 50, 'red')
    if lives <= 0:
        add_effect('boom', sub.pos, 40)
        end_game('Your submarine was destroyed.')


def damage_ocean(amount, x, y):
    global ocean
    ocean = max(0, ocean - amount)
    float_text('Ocean -' + str(amount), x, HEIGHT - 40, 'orange')
    if ocean <= 0:
        end_game('The ocean is too polluted.')


def fire():
    global fire_timer
    fire_timer = FIRE_DELAY
    spread = (-2, 0, 2) if triple_timer > 0 else (0,)
    for dx in spread:
        n = Actor('net', center=(sub.x + dx * 6, sub.top))
        n.vx = dx
        nets.append(n)
    play('shoot')


def use_vacuum():
    global vacuum_charges, vacuum_fx
    if vacuum_charges <= 0 or vacuum_fx > 0:
        return
    vacuum_charges -= 1
    vacuum_fx = 24
    play('vacuum')
    for t in trash[:]:
        if t.kind != 'barrel' and math.hypot(t.x - sub.x, t.y - sub.y) < VACUUM_RANGE:
            clean(t)


def start_boss():
    global boss_active, boss_hp, boss_drop_timer
    boss_active = True
    boss_hp = 40
    boss_drop_timer = 90
    boss.pos = (WIDTH / 2, -70)
    boss.vx = 1.5
    float_text('The POLLUTER is coming!', WIDTH / 2, HEIGHT / 2, 'red')


# ---------------- update ----------------
def update():
    global frame
    frame += 1
    # music also plays on the menu (it is stopped on the game over / win screen)
    if not muted and not music_on and state not in ('gameover', 'win'):
        start_music()
    if state != 'play' or paused:
        return
    if boss_dead_timer > 0:
        update_boss_death()
        return
    update_background()
    update_sub()
    update_spawning()
    update_trash()
    update_animals()
    update_nets()
    update_powerups()
    if boss_active:
        update_boss()
    update_effects()
    if state == 'play':
        check_level_goal()


def update_background():
    speed = LEVELS[level]['scroll']
    bg1.y += speed
    bg2.y += speed
    if bg1.y > BG_H / 2 + BG_H:
        bg1.y = bg2.y - BG_H
    if bg2.y > BG_H / 2 + BG_H:
        bg2.y = bg1.y - BG_H


def update_sub():
    global fire_timer, hurt_timer, slow_timer, triple_timer, shield_timer, vacuum_fx
    speed = SUB_SPEED / 2 if slow_timer > 0 else SUB_SPEED
    if keyboard.left or keyboard.a:
        sub.x -= speed
    if keyboard.right or keyboard.d:
        sub.x += speed
    if keyboard.up or keyboard.w:
        sub.y -= speed
    if keyboard.down or keyboard.s:
        sub.y += speed
    sub.left = max(0, sub.left)
    sub.right = min(WIDTH, sub.right)
    sub.top = max(HUD_H + 5, sub.top)
    sub.bottom = min(HEIGHT, sub.bottom)

    if fire_timer > 0:
        fire_timer -= 1
    if keyboard.space and fire_timer == 0:
        fire()

    hurt_timer = max(0, hurt_timer - 1)
    slow_timer = max(0, slow_timer - 1)
    triple_timer = max(0, triple_timer - 1)
    shield_timer = max(0, shield_timer - 1)
    vacuum_fx = max(0, vacuum_fx - 1)
    if hurt_timer == 0 and sub.image == 'sub_hurt':
        sub.image = 'sub'

    if frame % 6 == 0:
        bubbles.append([sub.x + random.randint(-6, 6), sub.bottom, 40])
    for b in bubbles[:]:
        b[1] -= 1.5
        b[2] -= 1
        if b[2] <= 0:
            bubbles.remove(b)


def update_spawning():
    global spawn_timer
    cfg = LEVELS[level]
    spawn_timer += 1
    every = cfg['spawn'] * (1.6 if boss_active else 1)
    if spawn_timer < every:
        return
    spawn_timer = 0
    if random.random() < cfg['oil_chance']:
        spawn_trash('oil_big')
    else:
        spawn_trash()
    if random.random() < cfg['animal_chance']:
        spawn_animal()


def update_trash():
    global slow_timer
    for t in trash[:]:
        t.phase += 0.05
        t.y += t.vy
        t.x += t.vx
        if t.kind == 'bag':
            t.x += math.sin(t.phase) * 1.2        # bags float side to side
        if t.left < 0 or t.right > WIDTH:
            t.vx = -t.vx
            t.x = min(max(t.x, t.width / 2), WIDTH - t.width / 2)

        if touching(t, sub):
            if t.kind == 'barrel':
                trash.remove(t)
                add_effect('boom', t.pos)
                hurt_sub('Toxic barrel!')
            elif t.kind.startswith('oil'):
                if slow_timer == 0:
                    float_text('Oil! Engine slowed', sub.x, sub.y - 50, 'gray')
                    play('oil')
                slow_timer = 120
            else:
                clean(t)          # the submarine scoops small trash
            continue

        if t.kind == 'bag':
            for a in animals:
                if a.kind == 'turtle' and not a.trapped and touching(t, a):
                    a.trapped = True
                    a.image = 'turtle_trapped'
                    a.vx *= 0.5
                    trash.remove(t)
                    float_text('Turtle trapped! Shoot the bag!', a.x, a.y - 40, 'orange')
                    play('penalty')
                    break
            if t not in trash:
                continue

        if t.top > HEIGHT:
            trash.remove(t)
            damage_ocean(TRASH[t.kind]['damage'], t.x, t.y)


def update_animals():
    for a in animals[:]:
        a.phase += 0.08
        a.x += a.vx
        a.y += a.vy
        if a.kind == 'jelly':
            a.x += math.sin(a.phase) * 0.8
            if touching(a, sub, 0.6):
                hurt_sub('Jellyfish sting!')
        if a.right < -60 or a.left > WIDTH + 60 or a.top > HEIGHT:
            animals.remove(a)
            if a.trapped:
                damage_ocean(10, a.x, a.y)
                float_text('A turtle was lost...', WIDTH / 2, HEIGHT / 2, 'orange')


def update_nets():
    global score, boss_hp
    for n in nets[:]:
        n.y -= NET_SPEED
        n.x += n.vx
        if n.bottom < HUD_H or n.right < 0 or n.left > WIDTH:
            nets.remove(n)
            continue

        hit = False
        for t in trash[:]:
            if touching(n, t, 0.9):
                hit = True
                t.hp -= 1
                if t.hp <= 0:
                    if t.kind == 'oil_big':
                        spawn_trash('oil_small', t.x - 20, t.y).vx = -1.2
                        spawn_trash('oil_small', t.x + 20, t.y).vx = 1.2
                    clean(t)
                else:
                    add_effect('splash', n.pos, 8)
                    play('oil')
                break

        if not hit:
            for a in animals[:]:
                if touching(n, a, 0.8):
                    hit = True
                    if a.trapped:
                        a.trapped = False
                        a.image = 'turtle'
                        a.vx *= 2
                        score += 50
                        float_text('Turtle saved! +50', a.x, a.y - 40, 'lightgreen')
                        add_effect('splash', a.pos)
                        play('rescue')
                    else:
                        score = max(0, score - 20)
                        float_text("Don't hurt sea life! -20", a.x, a.y - 40, 'red')
                        play('penalty')
                    break

        if not hit and boss_active and boss_hp > 0 and touching(n, boss, 0.85):
            hit = True
            boss_hp -= 1
            add_effect('boom', n.pos, 6)
            play('boss_hit')
            if boss_hp <= 0:
                boss_defeated()

        if hit and n in nets:
            nets.remove(n)


def update_powerups():
    global lives, ocean, vacuum_charges, triple_timer, shield_timer
    for p in powerups[:]:
        p.y += 1.5
        if p.top > HEIGHT:
            powerups.remove(p)
        elif touching(p, sub, 0.9):
            powerups.remove(p)
            play('powerup')
            if p.kind == 'pu_triple':
                triple_timer = 600
                float_text('Triple net!', sub.x, sub.y - 50, 'orange')
            elif p.kind == 'pu_vacuum':
                vacuum_charges = min(MAX_VACUUM, vacuum_charges + 1)
                float_text('Vacuum +1  (press V)', sub.x, sub.y - 50, 'violet')
            elif p.kind == 'pu_shield':
                shield_timer = 480
                float_text('Shield!', sub.x, sub.y - 50, 'cyan')
            else:
                if lives < MAX_LIVES:
                    lives += 1
                    float_text('+1 life', sub.x, sub.y - 50, 'pink')
                else:
                    ocean = min(100, ocean + 15)
                    float_text('Ocean +15', sub.x, sub.y - 50, 'lightgreen')


def check_level_goal():
    if not boss_active and cleaned >= LEVELS[level]['goal']:
        if level < len(LEVELS) - 1:
            level_complete()
        else:
            start_boss()


def update_boss():
    global boss_drop_timer
    if boss.y < 110:
        boss.y += 1
        return
    boss.x += boss.vx
    if boss.left < 0 or boss.right > WIDTH:
        boss.vx = -boss.vx
    boss_drop_timer -= 1
    if boss_drop_timer <= 0:
        boss_drop_timer = 70 if boss_hp > 20 else 50     # angrier when weak
        kind = 'oil_small' if random.random() < 0.3 else 'barrel'
        b = spawn_trash(kind, boss.x, boss.bottom)
        b.vy = 3


def boss_defeated():
    global boss_dead_timer, score
    score += 500
    boss_dead_timer = 90
    float_text('POLLUTER defeated! +500', WIDTH / 2, HEIGHT / 2, 'yellow')
    trash.clear()


def update_boss_death():
    global boss_dead_timer
    boss_dead_timer -= 1
    if boss_dead_timer % 10 == 0:
        add_effect('boom', (boss.x + random.randint(-90, 90), boss.y + random.randint(-40, 40)), 20)
        play('boss_hit')
    boss.y -= 0.5
    update_effects()
    if boss_dead_timer <= 0:
        end_game('You stopped the POLLUTER and saved the ocean!', won=True)


def update_effects():
    for e in effects[:]:
        e[1] -= 1
        if e[1] <= 0:
            effects.remove(e)
    for t in texts[:]:
        t[2] -= 0.6
        t[3] -= 1
        if t[3] <= 0:
            texts.remove(t)


# ---------------- draw ----------------
def draw():
    if state == 'menu':
        draw_menu()
    elif state == 'help':
        draw_help()
    else:
        draw_world()
        draw_hud()
        if state == 'intro':
            draw_intro()
        elif state == 'gameover' or state == 'win':
            draw_end()
        elif paused:
            draw_panel('Paused', ['Press P to continue', 'R to restart,  ESC for menu'])


def draw_world():
    bg1.draw()
    bg2.draw()
    for b in bubbles:
        screen.draw.circle((b[0], b[1]), 3, (220, 240, 255))
    for p in powerups:
        p.draw()
    for t in trash:
        t.draw()
    for a in animals:
        a.draw()
    if boss_active:
        boss.draw()
    for n in nets:
        n.draw()
    blink = hurt_timer > 0 and (frame // 5) % 2 == 0
    if state != 'gameover' and not blink:
        sub.draw()
    if shield_timer > 0 and (shield_timer > 90 or (frame // 6) % 2 == 0):
        shield_ring.pos = sub.pos
        shield_ring.draw()
    if vacuum_fx > 0:
        r = VACUUM_RANGE * (1 - vacuum_fx / 24)
        screen.draw.circle(sub.pos, r, (200, 150, 255))
        screen.draw.circle(sub.pos, r * 0.7, (220, 190, 255))
    for e in effects:
        e[0].draw()
    for text, x, y, left, color in texts:
        screen.draw.text(text, center=(x, y), fontsize=24, color=color, owidth=1, ocolor='black')


def draw_hud():
    screen.draw.filled_rect(Rect(0, 0, WIDTH, HUD_H), (8, 30, 60))
    screen.draw.line((0, HUD_H), (WIDTH, HUD_H), (120, 240, 200))
    for i in range(lives):
        screen.blit('heart', (8 + i * 26, 4))
    screen.draw.text('Score ' + str(score), topleft=(90, 4), fontsize=24, color='white')
    screen.draw.text('L' + str(level + 1), topleft=(205, 4), fontsize=24, color=(120, 240, 200))

    # ocean health bar
    screen.draw.text('Ocean', topleft=(8, 28), fontsize=17, color='white')
    screen.draw.rect(Rect(52, 30, 112, 12), 'white')
    color = (60, 200, 90) if ocean > 60 else (230, 200, 40) if ocean > 30 else (230, 60, 50)
    screen.draw.filled_rect(Rect(53, 31, int(110 * ocean / 100), 10), color)

    if boss_active:
        screen.draw.text('POLLUTER', topleft=(180, 27), fontsize=17, color='red')
        screen.draw.rect(Rect(255, 30, 102, 12), 'white')
        screen.draw.filled_rect(Rect(256, 31, int(100 * max(0, boss_hp) / 40), 10), (220, 50, 50))
    else:
        screen.draw.text('Trash %d/%d' % (cleaned, LEVELS[level]['goal']), topleft=(180, 27),
                         fontsize=18, color='white')

    for i in range(vacuum_charges):
        screen.blit('vac_icon', (250 + i * 22, 4))
    timers = []
    if triple_timer > 0:
        timers.append('x3 %d' % (triple_timer // 60 + 1))
    if shield_timer > 0:
        timers.append('S %d' % (shield_timer // 60 + 1))
    screen.draw.text('  '.join(timers), topleft=(320, 6), fontsize=20, color='orange')
    if muted:
        screen.draw.text('Sound off', topleft=(372, 30), fontsize=15, color='orange')

    face = 'face_small'
    if hurt_timer > 0 and has_image('face_sad'):
        face = 'face_sad'
    elif triple_timer > 0 and has_image('face_happy'):
        face = 'face_happy'
    if has_image(face):
        screen.blit(face, (WIDTH - 46, -1))


def draw_panel(title, lines, title_color='white'):
    screen.draw.filled_rect(Rect(30, 190, WIDTH - 60, 300), (8, 30, 60))
    screen.draw.rect(Rect(30, 190, WIDTH - 60, 300), (120, 240, 200))
    screen.draw.text(title, center=(WIDTH / 2, 235), fontsize=44, color=title_color)
    y = 285
    for line in lines:
        screen.draw.text(line, midtop=(WIDTH / 2, y), width=WIDTH - 100, align='center',
                         fontsize=24, color='white')
        y += 34 if len(line) < 38 else 56


def draw_intro():
    cfg = LEVELS[level]
    lines = []
    if intro_header:
        lines.append(intro_header)
    lines.append('Clean %d pieces of trash' % cfg['goal'] + (' and stop the POLLUTER' if level == 2 else ''))
    lines.append('Did you know? ' + fact)
    lines.append('Press ENTER to start')
    draw_panel(cfg['name'], lines, (120, 240, 200))


def draw_end():
    won = state == 'win'
    lines = [end_reason, 'Score: %d   Best: %d' % (score, high_score)]
    if new_record:
        lines.append('New high score!')
    lines.append(fact)
    lines.append('ENTER: play again   ESC: menu')
    draw_panel('You saved the ocean!' if won else 'Game Over', lines, 'yellow' if won else 'red')


def draw_menu():
    # the sea scrolls slowly behind the menu
    bg1.image = 'bg_sea'
    bg2.image = 'bg_sea'
    bg1.pos = (WIDTH / 2, BG_H / 2 + (frame * 0.5) % BG_H)
    bg2.pos = (WIDTH / 2, bg1.y - BG_H)
    bg1.draw()
    bg2.draw()
    logo.draw()
    if has_image('face'):
        screen.blit('face', (WIDTH / 2 - 64, 190))
        screen.draw.text("Let's save the ocean!", center=(WIDTH / 2, 335), fontsize=26,
                         color='white', owidth=1, ocolor='black')
    else:
        screen.blit('sub', (WIDTH / 2 - 32, 205))
        screen.draw.text("Let's save the ocean!", center=(WIDTH / 2, 320), fontsize=26,
                         color='white', owidth=1, ocolor='black')
    for b in buttons.values():
        b.draw()
    screen.draw.text('High score: ' + str(high_score), center=(WIDTH / 2, 610), fontsize=26, color='yellow',
                     owidth=1.2, ocolor='black')
    screen.draw.text('M: sound ' + ('OFF' if muted else 'ON'), center=(WIDTH / 2, 650), fontsize=20,
                     color='orange' if muted else 'white', owidth=1, ocolor='black')


def draw_help():
    screen.fill((8, 30, 60))
    screen.draw.text('How to play', center=(WIDTH / 2, 40), fontsize=44, color=(120, 240, 200))
    rows = [
        ('sub', 'Arrows / WASD move,  SPACE throw net'),
        ('bottle', 'Catch trash with nets or touch it'),
        ('oil_small', 'Oil: 3 hits, splits. Touching slows you'),
        ('turtle_trapped', 'Shoot the bag to save the turtle'),
        ('fish_left', "Don't hit sea life (-20 points)"),
        ('jelly', 'Jellyfish sting: avoid them'),
        ('barrel', 'Toxic barrels from the POLLUTER hurt'),
        ('pu_vacuum', 'V: vacuum all trash around you'),
        ('pu_triple', 'Triple net, shield and health power-ups'),
    ]
    y = 95
    for image, text in rows:
        a = Actor(image, center=(50, y))
        a.draw()
        screen.draw.text(text, midleft=(95, y), fontsize=22, color='white')
        y += 58
    screen.draw.text('Trash that sinks hurts the ocean. P pause, R restart', center=(WIDTH / 2, 625),
                     fontsize=20, color='orange')
    screen.draw.text('Press ESC or click to go back', center=(WIDTH / 2, 665), fontsize=22, color='yellow')


# ---------------- input ----------------
def on_key_down(key):
    global state, paused, muted
    if key == keys.M:
        muted = not muted
        if muted:
            stop_music()
        elif state not in ('gameover', 'win'):
            start_music()
        if state == 'play':
            float_text('Sound OFF' if muted else 'Sound ON', WIDTH / 2, HUD_H + 40, 'orange')
        return

    if state == 'menu':
        if key == keys.RETURN:
            new_game()
    elif state == 'help':
        state = 'menu'
    elif state == 'intro':
        if key == keys.RETURN:
            state = 'play'
        elif key == keys.ESCAPE:
            go_menu()
    elif state == 'play':
        if key == keys.P:
            paused = not paused
        elif key == keys.R:
            new_game()
        elif key == keys.ESCAPE:
            go_menu()
        elif key == keys.V and not paused:
            use_vacuum()
    elif state in ('gameover', 'win'):
        if key == keys.RETURN:
            new_game()
        elif key == keys.ESCAPE:
            go_menu()


def go_menu():
    global state
    state = 'menu'


def on_mouse_move(pos):
    if state != 'menu':
        return
    for name, b in buttons.items():
        b.image = 'btn_%s_hover' % name if b.collidepoint(pos) else 'btn_%s' % name


def on_mouse_down(pos):
    global state
    if state == 'help':
        state = 'menu'
    elif state == 'menu':
        if buttons['start'].collidepoint(pos):
            new_game()
        elif buttons['help'].collidepoint(pos):
            state = 'help'
        elif buttons['quit'].collidepoint(pos):
            sys.exit()


load_high_score()
os.environ['SDL_VIDEO_CENTERED'] = '1'
pgzrun.go()
