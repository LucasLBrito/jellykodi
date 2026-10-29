"""Gera o icone do Ark e as imagens do assistente do Setup (Pillow).

    uv run --no-project --with pillow python instalador/arte/gerar_arte.py

O desenho e geometrico (sem fonte), para nao depender de fonte com licenca propria:
um "A" vermelho em forma de arco, com um "play" branco no lugar da barra do meio.
"""
import os

from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
VERMELHO = (229, 9, 20, 255)      # FFE50914, o foco da skin
FUNDO = (20, 20, 20, 255)         # FF141414, o fundo da skin
BRANCO = (255, 255, 255, 255)


def icone(lado=1024, fundo=True):
    im = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = lado / 100.0
    if fundo:
        d.rounded_rectangle((2 * u, 2 * u, 98 * u, 98 * u), radius=22 * u, fill=FUNDO)
    # o "A": duas pernas grossas que se encontram no alto
    d.polygon([(43 * u, 14 * u), (57 * u, 14 * u), (84 * u, 86 * u), (70 * u, 86 * u),
               (50 * u, 33 * u), (30 * u, 86 * u), (16 * u, 86 * u)],
              fill=VERMELHO)
    # o "play" no lugar da barra
    d.polygon([(44 * u, 54 * u), (44 * u, 76 * u), (62 * u, 65 * u)], fill=BRANCO)
    return im


def main():
    grande = icone(1024)
    ico = os.path.join(AQUI, 'ark.ico')
    grande.save(ico, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    png = grande.resize((256, 256), Image.LANCZOS)
    png.save(os.path.join(AQUI, 'ark-256.png'))
    # icone dos dois addons dentro do Kodi (256x256, sem transparencia)
    for pasta in ('skin.ark', 'plugin.video.ark'):
        alvo = os.path.join(RAIZ, pasta, 'resources', 'icon.png')
        Image.alpha_composite(Image.new('RGBA', (256, 256), FUNDO), png).convert('RGB').save(alvo)

    # imagens do assistente do Inno Setup (BMP 24 bits)
    for escala, (w, h) in ((100, (164, 314)), (200, (328, 628))):
        lateral = Image.new('RGB', (w, h), FUNDO[:3])
        lado = int(w * 0.62)
        marca = icone(lado * 4, fundo=False).resize((lado, lado), Image.LANCZOS)
        lateral.paste(marca, ((w - lado) // 2, int(h * 0.30)), marca)
        faixa = ImageDraw.Draw(lateral)
        faixa.rectangle((0, h - max(3, h // 100), w, h), fill=VERMELHO[:3])
        lateral.save(os.path.join(AQUI, 'assistente-%d.bmp' % escala))
    for escala, lado in ((100, 55), (200, 110)):
        peq = Image.new('RGB', (lado, lado), (255, 255, 255))
        marca = icone(lado * 4).resize((lado, lado), Image.LANCZOS)
        peq.paste(marca, (0, 0), marca)
        peq.save(os.path.join(AQUI, 'assistente-pequeno-%d.bmp' % escala))


if __name__ == '__main__':
    main()
