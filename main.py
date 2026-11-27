#  OCEAN CLEANER
#  A Pygame Zero game about ocean pollution.
#  The player drives a cleaning submarine, catches falling trash with nets,
#  avoids hurting sea life, and stops the POLLUTER ship on every 10th level.
#
#  How Pygame Zero runs this file:
#    - update() is called 60 times a second: it changes the game (movement, rules)
#    - draw()   is called after it: it paints the screen
#    - on_key_down(), on_mouse_move(), on_mouse_down() are called on input
#  Pictures come from images/, sounds from sounds/, fonts from fonts/ (found by file name).
#
#  File layout:
#    1. settings and data             6. update: one function per part of the game
#    2. game state variables          7. draw: one function per screen
#    3. small helpers                 8. keyboard and mouse input
#    4. levels, progress, end         9. start the game
#    5. spawning trash / animals

import os
import sys
import math
import json
import random

# the folder of this file. It must be read before "import pgzrun",
# because pgzrun replaces __file__ with pgzero's own path
BASE = os.path.dirname(os.path.abspath(__file__))

import pygame
import pgzrun
from pgzero import loaders

if not os.path.isdir(os.path.join(BASE, 'images')):
    BASE = os.path.abspath(loaders.root)      # started with "pgzrun main.py": use the game folder


# 1. SETTINGS AND DATA
WIDTH = 480                 # window size (Pygame Zero reads WIDTH, HEIGHT and TITLE)
HEIGHT = 700
TITLE = 'Ocean Cleaner'

SCORE_FILE = os.path.join(BASE, 'highscore.txt')      # best score of a single level
PROGRESS_FILE = os.path.join(BASE, 'progress.json')   # unlocked level, stars and best score per level
BG_H = 852                  # height of a background picture (taller than the window)
HUD_H = 46                  # height of the information bar at the top

# fonts from the fonts/ folder
TITLE_FONT = 'bungee'       # big titles
UI_FONT = 'lilitaone'       # buttons, panel titles, messages
NUM_FONT = 'righteous'      # numbers in the top bar
TEXT_FONT = 'kanit'         # text you read (help, facts)

SUB_SPEED = 5               # submarine speed, pixels per frame
NET_SPEED = 9               # net speed, pixels per frame
FIRE_DELAY = 10             # frames between two nets
MAX_LIVES = 3
MAX_VACUUM = 3              # vacuum charges you can keep
VACUUM_RANGE = 170          # the vacuum cleans trash closer than this (pixels)

LEVEL_COUNT = 100
LEVELS_PER_PAGE = 20        # level select shows 4 x 5 tiles per page

# the place changes every level: coast, open sea, deep sea, coast again ...
THEMES = [
    {'place': 'The Coast', 'bg': 'bg_coast', 'scroll': 1.0, 'tile': 'coast'},
    {'place': 'Open Sea', 'bg': 'bg_sea', 'scroll': 1.5, 'tile': 'sea'},
    {'place': 'Deep Sea', 'bg': 'bg_deep', 'scroll': 2.0, 'tile': 'deep'},
]


def level_config(n):
    # the 100 levels are made from a few formulas: each level is a little harder,
    # and every number has a limit so the late levels stay playable
    theme = THEMES[(n - 1) % len(THEMES)]       # coast, sea, deep, coast, sea ... (a new place every level)
    boss = n % 10 == 0
    animals = ['fish']
    if n >= 3:
        animals += ['turtle']                 # turtles (and the bag rescue) from level 3
    if n >= 8:
        animals += ['jelly']                  # jellyfish from level 8
    goal = min(36, 15 + n // 4)
    return {
        'n': n,
        'name': 'Level %d' % n,
        'place': theme['place'],
        'bg': theme['bg'],
        'scroll': theme['scroll'],
        'tile': theme['tile'],
        'boss': boss,
        'goal': goal // 2 if boss else goal,  # boss levels: less trash, then the boss
        'spawn': max(30, round(56 - n * 0.3)),              # frames between new trash
        'speed': (min(2.2, 1.1 + n * 0.012), min(3.1, 1.9 + n * 0.013)),
        'trash': ['bottle', 'bottle', 'can', 'bag'] if n < 8 else ['bottle', 'can', 'bag', 'bag'],
        'animals': animals,
        'animal_chance': min(0.45, 0.3 + n * 0.003),
        'oil_chance': 0 if n < 5 else min(0.25, 0.06 + n * 0.0025),
        'boss_hp': 25 + (n // 10) * 3,       # 28 on level 10 ... 55 on level 100
        'boss_drop': max(56, 80 - (n // 10) * 2),           # frames between barrels
    }


# points when cleaned, ocean damage when it sinks to the bottom, hits needed
TRASH = {
    'bottle':    {'points': 10, 'damage': 5,  'hp': 1},
    'can':       {'points': 10, 'damage': 4,  'hp': 1},
    'bag':       {'points': 15, 'damage': 8,  'hp': 1},
    'oil_big':   {'points': 30, 'damage': 10, 'hp': 3},
    'oil_small': {'points': 10, 'damage': 5,  'hp': 1},
    'barrel':    {'points': 20, 'damage': 8,  'hp': 2},
}

# real ocean facts, one is shown before every level and at the end (sources in docs/game_data.txt)
FACTS = [
    'Around 11 million tonnes of plastic go into the ocean every year.',
    'Sea turtles eat plastic bags, which can look and even smell like their food.',
    'A plastic bottle is estimated to take up to 450 years to break down in the sea.',
    'Oil spills cover the feathers of sea birds and the gills of fish.',
    'More than 800 kinds of sea animals are harmed by ocean litter.',
    'Tiny pieces of plastic have been found in the deepest ocean trench.',
    'Using a reusable bottle and bag is the easiest way to help the ocean.',
]

# help pages: (title, rows of (picture, heading, text))
HELP_PAGES = [
    ('Controls', [
        ('sub', 'Move', 'Arrow keys or W A S D'),
        ('net', 'Throw nets', 'Hold SPACE, up to 6 nets a second'),
        ('pu_vacuum', 'Vacuum', 'Press V to clean all trash near you'),
        ('heart', 'Other keys', 'P pause,  R restart,  M sound,  ESC back'),
    ]),
    ('Trash', [
        ('bottle', 'Bottle and can  +10', 'If they sink, the ocean loses health'),
        ('bag', 'Plastic bag  +15', 'Careful: it can trap a turtle'),
        ('oil_big', 'Oil spill  +30', '3 hits, splits in two, touching it slows you'),
        ('barrel', 'Toxic barrel', 'Dropped by the boss, it costs a life'),
    ]),
    ('Sea life', [
        ('fish_left', 'Fish', 'Never hit it with a net: -20 points'),
        ('turtle', 'Turtle', 'Never hit it with a net: -20 points'),
        ('turtle_trapped', 'Trapped turtle', 'Hit the bag to free it: +50 points'),
        ('jelly', 'Jellyfish', 'Its sting costs you a life, swim around it'),
    ]),
    ('Power-ups', [
        ('pu_triple', 'Triple net', '3 nets at once for 10 seconds'),
        ('pu_shield', 'Shield', 'No damage for 8 seconds'),
        ('pu_vacuum', 'Vacuum', '+1 charge (keep up to 3), press V'),
        ('pu_health', 'Health', '+1 life, or ocean +15 when lives are full'),
    ]),
    ('Goal', [
        ('heart', '3 lives per level', 'Jellyfish and barrels take a life'),
        ('splash', 'Ocean health 100', 'Sinking trash lowers it. At 0 you lose'),
        ('star_big_on', 'Stars', 'More ocean health left = more stars'),
        ('boss', '100 levels', 'Every 10th level the POLLUTER ship attacks'),
    ]),
]


def has_image(name):
    # optional pictures (the face) are only drawn if the file exists
    return os.path.exists(os.path.join(BASE, 'images', name + '.png'))


# actors that live for the whole game
# An Actor is a picture with a position. Pygame Zero loads 'bg_sea' from images/bg_sea.jpg
bg1 = Actor('bg_sea')       # two copies of the background, one above the other,
bg2 = Actor('bg_sea')       # so it can scroll forever (same idea as the course aircraft game)
menu_bg = Actor('bg_menu', midtop=(WIDTH / 2, -76))
sub = Actor('sub')          # the player's submarine
shield_ring = Actor('shield')
boss = Actor('boss')
logo = Actor('logo', center=(WIDTH / 2, 92))
buttons = {
    'start': Actor('btn_start', center=(WIDTH / 2, 404)),
    'help': Actor('btn_help', center=(WIDTH / 2, 476)),
    'quit': Actor('btn_quit', center=(WIDTH / 2, 548)),
}
back_btn = Actor('btn_back', center=(38, 40))
prev_btn = Actor('btn_prev', center=(130, 630))
next_btn = Actor('btn_next', center=(350, 630))
panel_buttons = {
    'next': Actor('pb_next', center=(WIDTH / 2, 470)),
    'retry': Actor('pb_retry', center=(WIDTH / 2 - 95, 535)),
    'levels': Actor('pb_levels', center=(WIDTH / 2 + 95, 535)),
}


# 2. GAME STATE
# Pygame Zero's update() and draw() take no arguments, so the state is kept
# in module variables (functions change them with "global").
# All timers count frames: 60 frames = 1 second.
state = 'menu'          # menu, help, levels, intro, play, clear, gameover
paused = False
muted = False
music_on = False
cfg = level_config(1)   # settings of the level being played
level = 1               # number of the level being played (1 to 100)
unlocked = 1            # highest level you may play
stars = {}              # level number -> best stars (1 to 3)
best = {}               # level number -> best score
high_score = 0
new_record = False
level_page = 0          # page of the level select screen
help_page = 0
hover_tile = None       # level tile under the mouse
clear_frame = 0         # frame when the level was cleared (stars pop in after it)
earned_stars = 0
score = 0
lives = MAX_LIVES
ocean = 100             # ocean health
cleaned = 0             # trash cleaned in this level
frame = 0               # counts every update(), used for blinking and animations
spawn_timer = 0         # frames since the last new trash
fire_timer = 0          # frames until the next net can be thrown
hurt_timer = 0          # after a hit the submarine is safe while this is above 0
slow_timer = 0          # oil makes the submarine slow while this is above 0
triple_timer = 0        # power-up: 3 nets at once while above 0
shield_timer = 0        # power-up: no damage while above 0
vacuum_charges = 1
vacuum_fx = 0           # frames left of the vacuum circle animation
boss_active = False
boss_hp = 0
boss_max_hp = 0
boss_drop_timer = 0     # frames until the boss drops the next barrel
boss_dead_timer = 0     # boss explosion animation at the end
end_reason = ''         # why the game ended (shown on the end screen)
fact = ''               # the fact shown now

# lists of objects on the screen; new ones are appended, finished ones removed
trash = []
animals = []
nets = []
powerups = []
effects = []            # [actor, frames left]
texts = []              # [text, x, y, frames left, color]
bubbles = []            # [x, y, frames left]


# 3. SMALL HELPERS: saving, sound, text, panels, effects
def load_progress():
    global high_score, unlocked, stars, best
    try:
        with open(SCORE_FILE) as f:
            high_score = int(f.read().strip() or 0)
    except (OSError, ValueError):
        high_score = 0          # no file yet, or a broken file
    try:
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
        unlocked = max(1, min(LEVEL_COUNT, int(data.get('unlocked', 1))))
        # json keys are text, the game uses numbers
        stars = {int(k): v for k, v in data.get('stars', {}).items()}
        best = {int(k): v for k, v in data.get('best', {}).items()}
    except (OSError, ValueError, AttributeError):
        unlocked, stars, best = 1, {}, {}


def save_progress():
    global high_score, new_record
    new_record = score > high_score
    if new_record:
        high_score = score
    try:
        with open(SCORE_FILE, 'w') as f:
            f.write(str(high_score))
        with open(PROGRESS_FILE, 'w') as f:
            json.dump({'unlocked': unlocked, 'stars': stars, 'best': best}, f)
    except OSError:
        pass


def play(name):
    # play a sound effect from sounds/<name>.wav
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
        sounds.music_loop.play(-1)      # -1 = repeat forever
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


def say(text, size, font=UI_FONT, color='white', outline=1.2, **where):
    # draw text with a dark outline so it is easy to read on any background
    screen.draw.text(text, fontname=font, fontsize=size, color=color,
                     owidth=outline, ocolor=(5, 20, 40), **where)


def glass(x, y, w, h, color=(8, 30, 60), alpha=215, border=(120, 240, 200), radius=18):
    # a rounded, see-through panel (drawn with pygame because Pygame Zero has no rounded boxes)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, color + (alpha,), s.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(s, border + (255,), s.get_rect(), 2, border_radius=radius)
    screen.blit(s, (x, y))


def hover_image(actor, base, pos):
    # button hover effect: switch to the _hover picture when the mouse is over it
    actor.image = base + '_hover' if actor.collidepoint(pos) else base


def float_text(text, x, y, color='white'):
    # a short message ("+10", "Shield!") that floats up for 60 frames
    half = len(text) * 6 + 10          # keep the text inside the window
    x = min(max(x, half), WIDTH - half)
    texts.append([text, x, y, 60, color])


def add_effect(image, pos, frames=18):
    # a picture (splash, explosion) shown for a few frames
    effects.append([Actor(image, center=pos), frames])


# 4. LEVELS, PROGRESS AND THE END OF A LEVEL
def start_level(n):
    # reset everything for level n and show the intro screen
    global cfg, level, score, lives, ocean, vacuum_charges, new_record
    global cleaned, spawn_timer, fire_timer, hurt_timer, slow_timer, triple_timer, shield_timer
    global vacuum_fx, boss_active, boss_dead_timer, state, paused, fact
    level = n
    cfg = level_config(n)
    score = 0
    lives = MAX_LIVES
    ocean = 100
    vacuum_charges = 1
    new_record = False
    bg1.image = cfg['bg']
    bg2.image = cfg['bg']
    bg1.x = bg2.x = WIDTH / 2
    bg1.y = BG_H / 2                # bg1 fills the screen,
    bg2.y = BG_H / 2 - BG_H         # bg2 waits just above it
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
    fact = random.choice(FACTS)     # awareness: a random real fact for this level
    state = 'intro'


def stars_for(ocean_left):
    # more ocean health left at the end = more stars
    if ocean_left >= 75:
        return 3
    if ocean_left >= 45:
        return 2
    return 1


def level_clear():
    # the level is finished: give stars, unlock the next level and save
    global state, unlocked, earned_stars, clear_frame, fact
    if state != 'play':
        return
    earned_stars = stars_for(ocean)
    stars[level] = max(stars.get(level, 0), earned_stars)
    best[level] = max(best.get(level, 0), score)
    unlocked = max(unlocked, min(LEVEL_COUNT, level + 1))
    save_progress()
    fact = random.choice(FACTS)
    clear_frame = frame
    play('level')
    state = 'clear'


def game_over(reason):
    global state, end_reason, fact
    if state != 'play':             # the game can only end once
        return
    end_reason = reason
    fact = random.choice(FACTS)
    stop_music()
    play('gameover')
    state = 'gameover'


def open_levels():
    # level select screen, opened on the page of the highest unlocked level
    global state, level_page, hover_tile
    level_page = (unlocked - 1) // LEVELS_PER_PAGE
    hover_tile = None
    state = 'levels'


def tile_rect(i):
    # position of the i-th tile (0 to 19) on a level select page: 4 columns, 5 rows
    col, row = i % 4, i // 4
    return Rect(55 + col * 96, 100 + row * 96, 82, 82)


def tile_at(pos):
    for i in range(LEVELS_PER_PAGE):
        if tile_rect(i).collidepoint(pos):
            n = level_page * LEVELS_PER_PAGE + i + 1
            return n if n <= LEVEL_COUNT else None
    return None


# 5. SPAWNING (making new trash, animals and power-ups)
# Extra values are stored on the Actor itself (t.kind, t.hp, t.vy ...).
def spawn_trash(kind=None, x=None, y=None):
    if kind is None:
        kind = random.choice(cfg['trash'])                  # random kind for this level
    t = Actor(kind)
    t.kind = kind
    t.hp = TRASH[kind]['hp']                                 # hits needed
    t.x = x if x is not None else random.randint(30, WIDTH - 30)   # random x at the top
    t.y = y if y is not None else HUD_H - 30
    t.vy = random.uniform(*cfg['speed'])                     # random falling speed
    t.vx = 0
    t.phase = random.uniform(0, 6.28)                        # start of the side-to-side wave
    if kind == 'can':
        t.vy *= 1.3                                          # cans are heavy, they sink faster
    if kind in ('oil_big', 'oil_small'):
        t.vy *= 0.7                                          # oil floats slowly and drifts
        t.vx = random.choice((-0.6, 0.6))
    trash.append(t)
    return t


def spawn_animal():
    kind = random.choice(cfg['animals'])
    if kind == 'jelly':
        # jellyfish come from the top and float down
        a = Actor('jelly')
        a.x = random.randint(40, WIDTH - 40)
        a.y = HUD_H - 30
        a.vx = 0
        a.vy = random.uniform(0.8, 1.3)
    else:
        # fish and turtles swim across from a random side
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
    a.trapped = False                # a turtle becomes trapped when a bag touches it
    a.phase = random.uniform(0, 6.28)
    animals.append(a)


def drop_powerup(pos):
    # step 2 of the power-up chance: pick one of the four, 25% each
    p = Actor(random.choice(['pu_triple', 'pu_vacuum', 'pu_shield', 'pu_health']), center=pos)
    p.kind = p.image
    powerups.append(p)


# GAME RULES USED BY THE UPDATE FUNCTIONS
def touching(a, b, keep=0.75):
    # collision detection: collide with rectangles a bit smaller than the pictures
    # (keep=0.75 keeps 75% of the size), so empty picture corners do not count as a hit
    ra = Rect(a.left, a.top, a.width, a.height).inflate(-a.width * (1 - keep), -a.height * (1 - keep))
    rb = Rect(b.left, b.top, b.width, b.height).inflate(-b.width * (1 - keep), -b.height * (1 - keep))
    return ra.colliderect(rb)


def clean(t):
    # a piece of trash was cleaned (by a net, by touching it, or by the vacuum)
    global score, cleaned
    if t in trash:
        trash.remove(t)
    points = TRASH[t.kind]['points']
    score += points
    if not boss_active:
        cleaned += 1                 # counts towards the level goal
    float_text('+' + str(points), t.x, t.y, 'yellow')
    add_effect('splash', t.pos)
    play('collect')
    # step 1 of the power-up chance: random.random() gives 0.0 to 1.0,
    # below 0.08 happens 8% of the time
    if random.random() < 0.08:
        drop_powerup(t.pos)


def hurt_sub(reason):
    # the submarine loses a life (jellyfish, toxic barrel)
    global lives, hurt_timer
    if hurt_timer > 0 or shield_timer > 0:
        return                       # safe right after a hit, or protected by the shield
    lives -= 1
    hurt_timer = 90                  # 1.5 seconds without new damage
    sub.image = 'sub_hurt'
    play('hurt')
    float_text(reason, sub.x, sub.y - 50, 'red')
    if lives <= 0:
        add_effect('boom', sub.pos, 40)
        game_over('Your submarine was destroyed.')


def damage_ocean(amount, x, y):
    # trash reached the bottom (or a trapped turtle was lost)
    global ocean
    ocean = max(0, ocean - amount)
    float_text('Ocean -' + str(amount), x, HEIGHT - 40, 'orange')
    if ocean <= 0:
        game_over('The ocean is too polluted.')


def fire():
    # throw one net, or three nets with the triple power-up
    global fire_timer
    fire_timer = FIRE_DELAY
    spread = (-2, 0, 2) if triple_timer > 0 else (0,)
    for dx in spread:
        n = Actor('net', center=(sub.x + dx * 6, sub.top))
        n.vx = dx                    # side speed: left, straight, right
        nets.append(n)
    play('shoot')


def use_vacuum():
    # V key: clean all trash within VACUUM_RANGE (not barrels)
    global vacuum_charges, vacuum_fx
    if vacuum_charges <= 0 or vacuum_fx > 0:
        return
    vacuum_charges -= 1
    vacuum_fx = 24                   # frames of the circle animation
    play('vacuum')
    for t in trash[:]:
        if t.kind != 'barrel' and math.hypot(t.x - sub.x, t.y - sub.y) < VACUUM_RANGE:
            clean(t)


def start_boss():
    global boss_active, boss_hp, boss_max_hp, boss_drop_timer
    boss_active = True
    boss_hp = boss_max_hp = cfg['boss_hp']   # nets needed to defeat it
    boss_drop_timer = 90
    boss.pos = (WIDTH / 2, -70)              # starts above the screen and moves in
    boss.vx = 1.5
    float_text('The POLLUTER is coming!', WIDTH / 2, HEIGHT / 2, 'red')


# 6. UPDATE: called 60 times a second by Pygame Zero
# Each part of the game has its own small update function.
def update():
    global frame
    frame += 1
    # music plays on every screen except game over
    if not muted and not music_on and state != 'gameover':
        start_music()
    if state != 'play' or paused:
        return                       # nothing moves on menus or while paused
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
    # both pictures move down; the one that leaves the screen jumps above the other
    speed = cfg['scroll']
    bg1.y += speed
    bg2.y += speed
    if bg1.y > BG_H / 2 + BG_H:
        bg1.y = bg2.y - BG_H
    if bg2.y > BG_H / 2 + BG_H:
        bg2.y = bg1.y - BG_H


def update_sub():
    global fire_timer, hurt_timer, slow_timer, triple_timer, shield_timer, vacuum_fx
    # movement (keys held down), half speed after touching oil
    speed = SUB_SPEED / 2 if slow_timer > 0 else SUB_SPEED
    if keyboard.left or keyboard.a:
        sub.x -= speed
    if keyboard.right or keyboard.d:
        sub.x += speed
    if keyboard.up or keyboard.w:
        sub.y -= speed
    if keyboard.down or keyboard.s:
        sub.y += speed
    # stay inside the window and below the HUD
    sub.left = max(0, sub.left)
    sub.right = min(WIDTH, sub.right)
    sub.top = max(HUD_H + 5, sub.top)
    sub.bottom = min(HEIGHT, sub.bottom)

    # hold SPACE to throw nets, one every FIRE_DELAY frames
    if fire_timer > 0:
        fire_timer -= 1
    if keyboard.space and fire_timer == 0:
        fire()

    # every timer goes down by 1 each frame; an effect is active while its timer is above 0
    hurt_timer = max(0, hurt_timer - 1)
    slow_timer = max(0, slow_timer - 1)
    triple_timer = max(0, triple_timer - 1)
    shield_timer = max(0, shield_timer - 1)
    vacuum_fx = max(0, vacuum_fx - 1)
    if hurt_timer == 0 and sub.image == 'sub_hurt':
        sub.image = 'sub'

    # small bubbles behind the submarine (only decoration)
    if frame % 6 == 0:
        bubbles.append([sub.x + random.randint(-6, 6), sub.bottom, 40])
    for b in bubbles[:]:
        b[1] -= 1.5
        b[2] -= 1
        if b[2] <= 0:
            bubbles.remove(b)


def update_spawning():
    # every 'spawn' frames a new trash appears, sometimes with an animal
    global spawn_timer
    spawn_timer += 1
    every = cfg['spawn'] * (1.6 if boss_active else 1)   # less trash during the boss
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
    for t in trash[:]:              # loop over a copy, because items are removed inside
        # move
        t.phase += 0.05
        t.y += t.vy
        t.x += t.vx
        if t.kind == 'bag':
            t.x += math.sin(t.phase) * 1.2        # bags float side to side
        if t.left < 0 or t.right > WIDTH:
            t.vx = -t.vx                          # bounce off the sides
            t.x = min(max(t.x, t.width / 2), WIDTH - t.width / 2)

        # trash touches the submarine
        if touching(t, sub):
            if t.kind == 'barrel':
                trash.remove(t)
                add_effect('boom', t.pos)
                hurt_sub('Toxic barrel!')
            elif t.kind.startswith('oil'):
                if slow_timer == 0:
                    float_text('Oil! Engine slowed', sub.x, sub.y - 50, 'gray')
                    play('oil')
                slow_timer = 120                  # 2 seconds at half speed
            else:
                clean(t)          # the submarine scoops small trash
            continue

        # a plastic bag that touches a free turtle traps it
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

        # trash that sinks to the bottom hurts the ocean
        if t.top > HEIGHT:
            trash.remove(t)
            damage_ocean(TRASH[t.kind]['damage'], t.x, t.y)


def update_animals():
    for a in animals[:]:
        a.phase += 0.08
        a.x += a.vx
        a.y += a.vy
        if a.kind == 'jelly':
            a.x += math.sin(a.phase) * 0.8        # jellyfish wobble
            if touching(a, sub, 0.6):
                hurt_sub('Jellyfish sting!')
        # animal left the screen
        if a.right < -60 or a.left > WIDTH + 60 or a.top > HEIGHT:
            animals.remove(a)
            if a.trapped:
                damage_ocean(10, a.x, a.y)        # a turtle we did not save
                float_text('A turtle was lost...', WIDTH / 2, HEIGHT / 2, 'orange')


def update_nets():
    # move every net and check what it hits: trash first, then animals, then the boss
    global score, boss_hp
    for n in nets[:]:
        n.y -= NET_SPEED
        n.x += n.vx
        if n.bottom < HUD_H or n.right < 0 or n.left > WIDTH:
            nets.remove(n)
            continue

        hit = False
        # net hits trash
        for t in trash[:]:
            if touching(n, t, 0.9):
                hit = True
                t.hp -= 1
                if t.hp <= 0:
                    if t.kind == 'oil_big':
                        # a big oil spill splits into two small ones
                        spawn_trash('oil_small', t.x - 20, t.y).vx = -1.2
                        spawn_trash('oil_small', t.x + 20, t.y).vx = 1.2
                    clean(t)
                else:
                    add_effect('splash', n.pos, 8)   # hit, but it needs more hits
                    play('oil')
                break

        # net hits a sea animal
        if not hit:
            for a in animals[:]:
                if touching(n, a, 0.8):
                    hit = True
                    if a.trapped:
                        # freeing a trapped turtle is good
                        a.trapped = False
                        a.image = 'turtle'
                        a.vx *= 2
                        score += 50
                        float_text('Turtle saved! +50', a.x, a.y - 40, 'lightgreen')
                        add_effect('splash', a.pos)
                        play('rescue')
                    else:
                        # hitting a free animal is bad
                        score = max(0, score - 20)
                        float_text("Don't hurt sea life! -20", a.x, a.y - 40, 'red')
                        play('penalty')
                    break

        # net hits the boss
        if not hit and boss_active and boss_hp > 0 and touching(n, boss, 0.85):
            hit = True
            boss_hp -= 1
            add_effect('boom', n.pos, 6)
            play('boss_hit')
            if boss_hp <= 0:
                boss_defeated()

        if hit and n in nets:
            nets.remove(n)           # a net is used up after one hit


def update_powerups():
    global lives, ocean, vacuum_charges, triple_timer, shield_timer
    for p in powerups[:]:
        p.y += 1.5                   # falls slowly
        if p.top > HEIGHT:
            powerups.remove(p)       # missed
        elif touching(p, sub, 0.9):
            # collected: start the timer or give the reward
            powerups.remove(p)
            play('powerup')
            if p.kind == 'pu_triple':
                triple_timer = 600               # 10 seconds
                float_text('Triple net!', sub.x, sub.y - 50, 'orange')
            elif p.kind == 'pu_vacuum':
                vacuum_charges = min(MAX_VACUUM, vacuum_charges + 1)
                float_text('Vacuum +1  (press V)', sub.x, sub.y - 50, 'violet')
            elif p.kind == 'pu_shield':
                shield_timer = 480               # 8 seconds
                float_text('Shield!', sub.x, sub.y - 50, 'cyan')
            else:
                # health: one more life, or ocean health if lives are full
                if lives < MAX_LIVES:
                    lives += 1
                    float_text('+1 life', sub.x, sub.y - 50, 'pink')
                else:
                    ocean = min(100, ocean + 15)
                    float_text('Ocean +15', sub.x, sub.y - 50, 'lightgreen')


def check_level_goal():
    # enough trash cleaned: the level is done, or the boss comes on every 10th level
    if not boss_active and cleaned >= cfg['goal']:
        if cfg['boss']:
            start_boss()
        else:
            level_clear()


def update_boss():
    global boss_drop_timer
    if boss.y < 110:
        boss.y += 1                  # moving in from the top
        return
    boss.x += boss.vx
    if boss.left < 0 or boss.right > WIDTH:
        boss.vx = -boss.vx           # back and forth
    boss_drop_timer -= 1
    if boss_drop_timer <= 0:
        # angrier when weak: drops faster below half health
        boss_drop_timer = cfg['boss_drop'] if boss_hp > boss_max_hp // 2 else cfg['boss_drop'] - 20
        kind = 'oil_small' if random.random() < 0.3 else 'barrel'
        b = spawn_trash(kind, boss.x, boss.bottom)
        b.vy = 3


def boss_defeated():
    global boss_dead_timer, score
    score += 500
    boss_dead_timer = 90             # 1.5 seconds of explosions before the clear screen
    float_text('POLLUTER defeated! +500', WIDTH / 2, HEIGHT / 2, 'yellow')
    trash.clear()


def update_boss_death():
    global boss_dead_timer
    boss_dead_timer -= 1
    if boss_dead_timer % 10 == 0:    # an explosion every 10 frames at a random spot
        add_effect('boom', (boss.x + random.randint(-90, 90), boss.y + random.randint(-40, 40)), 20)
        play('boss_hit')
    boss.y -= 0.5
    update_effects()
    if boss_dead_timer <= 0:
        level_clear()


def update_effects():
    # count down splash/explosion pictures and floating texts, remove finished ones
    for e in effects[:]:
        e[1] -= 1
        if e[1] <= 0:
            effects.remove(e)
    for t in texts[:]:
        t[2] -= 0.6                  # float up
        t[3] -= 1
        if t[3] <= 0:
            texts.remove(t)


# 7. DRAW: called by Pygame Zero after update()
# Things drawn later appear on top.
def draw():
    if state == 'menu':
        draw_menu()
    elif state == 'help':
        draw_help()
    elif state == 'levels':
        draw_levels()
    else:
        draw_world()
        draw_hud()
        if state == 'intro':
            draw_intro()
        elif state == 'clear':
            draw_clear()
        elif state == 'gameover':
            draw_gameover()
        elif paused:
            glass(50, 240, WIDTH - 100, 200)
            say('PAUSED', 44, TITLE_FONT, 'yellow', center=(WIDTH / 2, 295))
            say('P  continue', 26, UI_FONT, center=(WIDTH / 2, 355))
            say('R  restart     ESC  levels', 22, UI_FONT, center=(WIDTH / 2, 395))


def draw_world():
    # background, objects, submarine and effects
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
    blink = hurt_timer > 0 and (frame // 5) % 2 == 0     # blink after a hit
    if state != 'gameover' and not blink:
        sub.draw()
    # the shield blinks in its last 1.5 seconds as a warning
    if shield_timer > 0 and (shield_timer > 90 or (frame // 6) % 2 == 0):
        shield_ring.pos = sub.pos
        shield_ring.draw()
    if vacuum_fx > 0:
        r = VACUUM_RANGE * (1 - vacuum_fx / 24)          # growing circle
        screen.draw.circle(sub.pos, r, (200, 150, 255))
        screen.draw.circle(sub.pos, r * 0.7, (220, 190, 255))
    for e in effects:
        e[0].draw()
    for text, x, y, left, color in texts:
        say(text, 20, UI_FONT, color, center=(x, y))


def draw_hud():
    # information bar at the top
    screen.draw.filled_rect(Rect(0, 0, WIDTH, HUD_H), (8, 30, 60))
    screen.draw.line((0, HUD_H), (WIDTH, HUD_H), (120, 240, 200))
    for i in range(lives):
        screen.blit('heart', (8 + i * 26, 4))
    screen.draw.text('Score ' + str(score), topleft=(88, 4), fontname=NUM_FONT, fontsize=19, color='white')
    screen.draw.text('Lv ' + str(level), topright=(250, 4), fontname=NUM_FONT, fontsize=19, color=(120, 240, 200))

    # ocean health bar: green, then yellow, then red
    screen.draw.text('Ocean', topleft=(8, 28), fontname=NUM_FONT, fontsize=13, color='white')
    screen.draw.rect(Rect(56, 30, 108, 12), 'white')
    color = (60, 200, 90) if ocean > 60 else (230, 200, 40) if ocean > 30 else (230, 60, 50)
    screen.draw.filled_rect(Rect(57, 31, int(106 * ocean / 100), 10), color)

    # boss health bar, or the level goal
    if boss_active:
        screen.draw.text('POLLUTER', topleft=(178, 27), fontname=NUM_FONT, fontsize=15, color='red')
        screen.draw.rect(Rect(262, 30, 96, 12), 'white')
        screen.draw.filled_rect(Rect(263, 31, int(94 * max(0, boss_hp) / max(1, boss_max_hp)), 10), (220, 50, 50))
    else:
        screen.draw.text('Trash %d/%d' % (cleaned, cfg['goal']), topleft=(178, 26),
                         fontname=NUM_FONT, fontsize=16, color='white')

    # vacuum charges and seconds left of the timed power-ups
    for i in range(vacuum_charges):
        screen.blit('vac_icon', (258 + i * 22, 4))
    timers = []
    if triple_timer > 0:
        timers.append('x3 %d' % (triple_timer // 60 + 1))
    if shield_timer > 0:
        timers.append('S %d' % (shield_timer // 60 + 1))
    screen.draw.text('  '.join(timers), topleft=(326, 5), fontname=NUM_FONT, fontsize=18, color='orange')
    if muted:
        screen.draw.text('Sound off', topleft=(368, 29), fontname=NUM_FONT, fontsize=13, color='orange')

    # pilot face: sad after a hit, happy with triple net
    face = 'face_small'
    if hurt_timer > 0 and has_image('face_sad'):
        face = 'face_sad'
    elif triple_timer > 0 and has_image('face_happy'):
        face = 'face_happy'
    if has_image(face):
        screen.blit(face, (WIDTH - 46, -1))


def draw_star_row(n, cx, y, big=False):
    # 3 stars, the first n are gold
    name, step = ('star_big', 50) if big else ('star', 20)
    for i in range(3):
        img = name + ('_on' if i < n else '_off')
        screen.blit(img, (cx - step * 1.5 + i * step, y))


def draw_intro():
    glass(30, 170, WIDTH - 60, 350)
    say(cfg['name'], 40, TITLE_FONT, (120, 240, 200), center=(WIDTH / 2, 215))
    say(cfg['place'], 26, UI_FONT, 'white', center=(WIDTH / 2, 258))
    goal = 'Clean %d pieces of trash' % cfg['goal']
    if cfg['boss']:
        goal = 'Clean %d trash, then stop the POLLUTER!' % cfg['goal']
    say(goal, 20, UI_FONT, 'yellow', center=(WIDTH / 2, 298))
    screen.draw.text('Did you know? ' + fact, midtop=(WIDTH / 2, 330), width=WIDTH - 110, align='center',
                     fontname=TEXT_FONT, fontsize=20, color='white')
    if (frame // 30) % 2 == 0:       # blinking hint
        say('Press ENTER or click to start', 22, UI_FONT, (120, 240, 200), center=(WIDTH / 2, 485))


def draw_clear():
    glass(30, 120, WIDTH - 60, 470)
    title = 'ALL LEVELS DONE!' if level == LEVEL_COUNT else 'LEVEL CLEAR!'
    say(title, 34 if level == LEVEL_COUNT else 38, TITLE_FONT, 'yellow', center=(WIDTH / 2, 165))
    # stars pop in one after another
    shown = min(earned_stars, (frame - clear_frame) // 20)
    draw_star_row(shown, WIDTH / 2, 195, big=True)
    say('Score %d      Best %d' % (score, best.get(level, score)), 24, UI_FONT, center=(WIDTH / 2, 268))
    say('Ocean health left: %d' % ocean, 20, UI_FONT, (120, 240, 200), center=(WIDTH / 2, 300))
    if new_record:
        say('New high score!', 22, UI_FONT, 'orange', center=(WIDTH / 2, 330))
    screen.draw.text(fact, midtop=(WIDTH / 2, 350), width=WIDTH - 110, align='center',
                     fontname=TEXT_FONT, fontsize=18, color='white')
    if level < LEVEL_COUNT:
        panel_buttons['next'].draw()
    panel_buttons['retry'].draw()
    panel_buttons['levels'].draw()


def draw_gameover():
    glass(30, 150, WIDTH - 60, 430, border=(255, 110, 110))
    say('GAME OVER', 42, TITLE_FONT, (255, 90, 90), center=(WIDTH / 2, 200))
    say(end_reason, 22, UI_FONT, center=(WIDTH / 2, 250))
    say('Level %d     Score %d' % (level, score), 24, UI_FONT, 'yellow', center=(WIDTH / 2, 290))
    screen.draw.text(fact, midtop=(WIDTH / 2, 330), width=WIDTH - 110, align='center',
                     fontname=TEXT_FONT, fontsize=18, color='white')
    panel_buttons['retry'].draw()
    panel_buttons['levels'].draw()


def draw_menu():
    menu_bg.draw()
    logo.draw()
    if has_image('face'):
        screen.blit('face', (WIDTH / 2 - 64, 175))
        say("Let's save the ocean!", 26, UI_FONT, center=(WIDTH / 2, 325))
    else:
        screen.blit('sub', (WIDTH / 2 - 32, 205))
        say("Let's save the ocean!", 26, UI_FONT, center=(WIDTH / 2, 320))
    # the START button bobs a little to catch the eye
    buttons['start'].y = 404 + math.sin(frame / 15) * 3
    for b in buttons.values():
        b.draw()
    glass(90, 590, WIDTH - 180, 88, alpha=170)
    screen.blit('star_on', (150, 600))
    say('%d / %d' % (sum(stars.values()), LEVEL_COUNT * 3), 22, UI_FONT, 'yellow', midleft=(176, 609))
    say('Level %d unlocked' % unlocked, 18, UI_FONT, midleft=(150, 636))
    say('M: sound ' + ('OFF' if muted else 'ON'), 16, UI_FONT, 'orange' if muted else 'white',
        midleft=(150, 660))


def draw_levels():
    menu_bg.draw()
    glass(15, 75, WIDTH - 30, 515, alpha=150, border=None)
    back_btn.draw()
    say('SELECT LEVEL', 30, TITLE_FONT, center=(WIDTH / 2 + 20, 42))
    for i in range(LEVELS_PER_PAGE):
        n = level_page * LEVELS_PER_PAGE + i + 1
        if n > LEVEL_COUNT:
            break
        r = tile_rect(i)
        c = level_config(n)
        if n > unlocked:
            screen.blit('tile_locked', r.topleft)
            continue
        img = 'tile_%s' % c['tile'] + ('_hover' if n == hover_tile else '')
        lift = -2 if n == hover_tile else 0
        screen.blit(img, (r.x, r.y + lift))
        say(str(n), 30, UI_FONT, center=(r.centerx, r.centery - 8 + lift))
        if c['boss']:
            say('BOSS', 13, UI_FONT, (255, 120, 90), center=(r.centerx, r.top + 12 + lift))
        if n in stars:
            draw_star_row(stars[n], r.centerx, r.bottom - 27 + lift)
        elif n == unlocked and (frame // 20) % 2 == 0:
            say('NEW', 13, UI_FONT, 'yellow', center=(r.centerx, r.bottom - 18 + lift))
    pages = (LEVEL_COUNT - 1) // LEVELS_PER_PAGE + 1
    if level_page > 0:
        prev_btn.draw()
    if level_page < pages - 1:
        next_btn.draw()
    say('%d / %d' % (level_page + 1, pages), 24, UI_FONT, center=(WIDTH / 2, 630))
    screen.blit('star_on', (180, 666))
    say('%d / %d stars' % (sum(stars.values()), LEVEL_COUNT * 3), 18, UI_FONT, 'yellow', midleft=(204, 675))


def draw_help():
    menu_bg.draw()
    back_btn.draw()
    say('HOW TO PLAY', 30, TITLE_FONT, center=(WIDTH / 2 + 20, 42))
    # tabs: click one, or use the arrow keys
    for i, (name, rows) in enumerate(HELP_PAGES):
        r = help_tab_rect(i)
        active = i == help_page
        glass(r.x, r.y, r.w, r.h, (247, 134, 30) if active else (8, 30, 60), 240 if active else 190,
              (255, 255, 255) if active else (120, 240, 200), 14)
        say(name, 15, UI_FONT, center=r.center, outline=1)
    title, rows = HELP_PAGES[help_page]
    glass(20, 120, WIDTH - 40, 470, alpha=215)
    for i, (image, head, text) in enumerate(rows):
        y = 175 + i * 108
        # every picture bobs gently, each one a little later than the one above
        bob = math.sin(frame / 18 + i) * 4
        glass(36, y - 42, 84, 84, (20, 60, 100), 200, None, 16)
        draw_fitted(image, (78, y + bob), 70)
        say(head, 24, UI_FONT, 'yellow', topleft=(136, y - 34))
        screen.draw.text(text, topleft=(136, y - 2), width=WIDTH - 180, fontname=TEXT_FONT,
                         fontsize=19, color='white')
    prev_btn.draw()
    next_btn.draw()
    say('%d / %d' % (help_page + 1, len(HELP_PAGES)), 24, UI_FONT, center=(WIDTH / 2, 630))
    say('Arrow keys or click the tabs', 16, UI_FONT, (120, 240, 200), center=(WIDTH / 2, 672))


fitted = {}     # pictures already shrunk for the help page


def draw_fitted(name, center, size):
    # draw a picture shrunk to fit a size x size box (the boss is too big for the help box)
    if name not in fitted:
        surf = getattr(images, name)
        k = min(1, size / surf.get_width(), size / surf.get_height())
        fitted[name] = pygame.transform.smoothscale(
            surf, (int(surf.get_width() * k), int(surf.get_height() * k)))
    s = fitted[name]
    screen.blit(s, (center[0] - s.get_width() / 2, center[1] - s.get_height() / 2))


def help_tab_rect(i):
    return Rect(14 + i * 91, 74, 86, 34)


# 8. INPUT (Pygame Zero calls these when a key or the mouse is used)
# Keys held down (movement, SPACE) are read in update_sub() with "keyboard".
# Single presses are handled here, depending on the current state.
def on_key_down(key):
    global state, paused, muted, level_page, help_page
    # M works on every screen
    if key == keys.M:
        muted = not muted
        if muted:
            stop_music()
        elif state != 'gameover':
            start_music()
        if state == 'play':
            float_text('Sound OFF' if muted else 'Sound ON', WIDTH / 2, HUD_H + 40, 'orange')
        return

    enter = key in (keys.RETURN, keys.KP_ENTER)
    if state == 'menu':
        if enter:
            open_levels()
    elif state == 'help':
        if key == keys.LEFT:
            help_page = (help_page - 1) % len(HELP_PAGES)
        elif key == keys.RIGHT:
            help_page = (help_page + 1) % len(HELP_PAGES)
        elif key in (keys.ESCAPE, keys.BACKSPACE):
            state = 'menu'
    elif state == 'levels':
        pages = (LEVEL_COUNT - 1) // LEVELS_PER_PAGE + 1
        if key == keys.LEFT:
            level_page = max(0, level_page - 1)
        elif key == keys.RIGHT:
            level_page = min(pages - 1, level_page + 1)
        elif enter:
            start_level(unlocked)            # ENTER plays the newest level
        elif key == keys.ESCAPE:
            state = 'menu'
    elif state == 'intro':
        if enter:
            state = 'play'
        elif key == keys.ESCAPE:
            open_levels()
    elif state == 'play':
        if key == keys.P:
            paused = not paused
        elif key == keys.R:
            start_level(level)
        elif key == keys.ESCAPE:
            open_levels()
        elif key == keys.V and not paused:
            use_vacuum()
    elif state == 'clear':
        if enter and level < LEVEL_COUNT:
            start_level(level + 1)
        elif key == keys.R:
            start_level(level)
        elif key == keys.ESCAPE:
            open_levels()
    elif state == 'gameover':
        if enter or key == keys.R:
            start_level(level)
        elif key == keys.ESCAPE:
            open_levels()


def on_mouse_move(pos):
    global hover_tile
    if state == 'menu':
        for name, b in buttons.items():
            hover_image(b, 'btn_' + name, pos)
    elif state in ('levels', 'help'):
        hover_image(back_btn, 'btn_back', pos)
        hover_image(prev_btn, 'btn_prev', pos)
        hover_image(next_btn, 'btn_next', pos)
        if state == 'levels':
            n = tile_at(pos)
            hover_tile = n if n is not None and n <= unlocked else None
    elif state in ('clear', 'gameover'):
        for name, b in panel_buttons.items():
            hover_image(b, 'pb_' + name, pos)


def on_mouse_down(pos):
    global state, level_page, help_page
    if state == 'menu':
        if buttons['start'].collidepoint(pos):
            open_levels()
        elif buttons['help'].collidepoint(pos):
            state = 'help'
        elif buttons['quit'].collidepoint(pos):
            sys.exit()
    elif state == 'help':
        if back_btn.collidepoint(pos):
            state = 'menu'
        elif prev_btn.collidepoint(pos):
            help_page = (help_page - 1) % len(HELP_PAGES)
        elif next_btn.collidepoint(pos):
            help_page = (help_page + 1) % len(HELP_PAGES)
        for i in range(len(HELP_PAGES)):
            if help_tab_rect(i).collidepoint(pos):
                help_page = i
    elif state == 'levels':
        pages = (LEVEL_COUNT - 1) // LEVELS_PER_PAGE + 1
        if back_btn.collidepoint(pos):
            state = 'menu'
        elif prev_btn.collidepoint(pos) and level_page > 0:
            level_page -= 1
        elif next_btn.collidepoint(pos) and level_page < pages - 1:
            level_page += 1
        else:
            n = tile_at(pos)
            if n is not None and n <= unlocked:      # locked levels cannot be played yet
                start_level(n)
    elif state == 'intro':
        state = 'play'
    elif state == 'clear':
        if level < LEVEL_COUNT and panel_buttons['next'].collidepoint(pos):
            start_level(level + 1)
        elif panel_buttons['retry'].collidepoint(pos):
            start_level(level)
        elif panel_buttons['levels'].collidepoint(pos):
            open_levels()
    elif state == 'gameover':
        if panel_buttons['retry'].collidepoint(pos):
            start_level(level)
        elif panel_buttons['levels'].collidepoint(pos):
            open_levels()


# 9. START
load_progress()
os.environ['SDL_VIDEO_CENTERED'] = '1'      # open the window in the middle of the screen
pgzrun.go()                                 # start the Pygame Zero game loop
