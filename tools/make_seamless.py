# Makes a background picture loop seamlessly from bottom to top, at 480 x 852.
# The picture is scaled to 480 wide (cropped if needed), then the rows below 852
# are faded into the top rows, so the bottom edge flows into the top edge.
#
# Run:  python tools/make_seamless.py my_picture.png images/bg_deep.jpg
#       python tools/make_seamless.py my_picture.png images/bg_deep.jpg 160   (bigger fade)
import os
import sys

os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame

W, H = 480, 852


def make_seamless(src_path, out_path, fade=120):
    pygame.init()
    pygame.display.set_mode((1, 1))
    img = pygame.image.load(src_path).convert()

    # scale so the picture covers 480 x (852 + fade), then crop the middle
    need_h = H + fade
    scale = max(W / img.get_width(), need_h / img.get_height())
    img = pygame.transform.smoothscale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
    left = (img.get_width() - W) // 2
    top = (img.get_height() - need_h) // 2
    img = img.subsurface((left, top, W, need_h)).copy()

    out = img.subsurface((0, 0, W, H)).copy()
    for i in range(fade):
        row = img.subsurface((0, H + i, W, 1)).copy()
        row.set_alpha(round(255 * (1 - i / fade)))
        out.blit(row, (0, i))

    pygame.image.save(out, out_path)
    return out


def seam_difference(surf):
    # average colour jump between the last and the first row (0 = perfect)
    total = 0
    for x in range(surf.get_width()):
        a, b = surf.get_at((x, surf.get_height() - 1)), surf.get_at((x, 0))
        total += abs(a.r - b.r) + abs(a.g - b.g) + abs(a.b - b.b)
    return total / surf.get_width()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: python tools/make_seamless.py input_picture output.jpg [fade]')
        sys.exit(1)
    fade = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    result = make_seamless(sys.argv[1], sys.argv[2], fade)
    print('saved %s  (%dx%d)  seam difference: %.1f' % (sys.argv[2], W, H, seam_difference(result)))
