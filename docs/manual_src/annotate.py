from PIL import Image, ImageDraw, ImageFont
import os
B = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
ACC = (255, 122, 0)

def badge(d, x, y, n):
    r = 17
    d.ellipse([x - r, y - r, x + r, y + r], fill=ACC, outline=(255, 255, 255), width=3)
    w = d.textlength(str(n), font=B)
    d.text((x - w / 2, y - 13), str(n), font=B, fill=(255, 255, 255))

def box(d, x0, y0, x1, y1):
    d.rounded_rectangle([x0, y0, x1, y1], radius=6, outline=ACC, width=4)

def make(src, dst, boxes=(), badges=()):
    im = Image.open(src).convert('RGB')
    d = ImageDraw.Draw(im)
    for b in boxes:
        box(d, *b)
    for x, y, n in badges:
        badge(d, x, y, n)
    im.save(dst, quality=90)

for L in ('ja', 'en'):
    s = lambda n: f'shots/{L}_{n}.jpg'
    # overview: numbered parts of the window
    make(s('4_result'), f'fig/{L}_overview.jpg',
         boxes=[(4, 36, 180, 62), (4, 74, 1278, 102), (18, 116, 608, 716), (14, 722, 260, 750),
                (14, 754, 610, 782), (626, 116, 1254, 750), (626, 754, 1060, 782), (1178, 754, 1264, 782)],
         badges=[(196, 49, 1), (1080, 60, 2), (590, 135, 3), (276, 736, 4), (598, 752, 5),
                 (1240, 135, 6), (1052, 752, 7), (1250, 744, 8)])
    make(s('1_loaded'), f'fig/{L}_step1.jpg', boxes=[(4, 74, 1278, 102), (18, 116, 608, 440)],
         badges=[(30, 60, 1), (1265, 60, 2), (590, 135, 3)])
    make(s('2_checked'), f'fig/{L}_step2.jpg', boxes=[(18, 140, 48, 440), (14, 722, 260, 750)],
         badges=[(62, 168, 1), (276, 736, 2)])
    make(s('3_excluded'), f'fig/{L}_step3.jpg', boxes=[(14, 754, 610, 782)], badges=[(598, 752, 1)])
    make(s('4_result'), f'fig/{L}_step4.jpg', boxes=[(626, 116, 1254, 750), (626, 754, 1060, 782)],
         badges=[(1240, 135, 1), (1052, 752, 2)])
    make(s('5_saved'), f'fig/{L}_step5.jpg', boxes=[(1178, 754, 1264, 782)], badges=[(1250, 744, 1)])
    make(s('6_help'), f'fig/{L}_help.jpg', boxes=[(118, 64, 258, 146)], badges=[(272, 80, 1)])
    make(s('7_lang'), f'fig/{L}_lang.jpg', boxes=[(0, 64, 162, 142)], badges=[(176, 80, 1)])
make('shots/en_5a_overwrite.jpg', 'fig/en_overwrite.jpg', boxes=[(452, 340, 808, 472)])
print(sorted(os.listdir('fig')))
