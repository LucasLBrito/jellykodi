# -*- coding: utf-8 -*-
"""Funções compartilhadas entre o serviço (service.py) e o plugin (plugin.py)."""
import json
import os
import re
import time
from urllib.parse import quote

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'plugin.video.ark'
ADDON = xbmcaddon.Addon(ADDON_ID)
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
STATE_FILE = os.path.join(PROFILE, 'state.json')
HOME = xbmcgui.Window(10000)

VIDEO_EXT = {'.mkv', '.mp4', '.m4v', '.avi', '.mov', '.wmv', '.ts', '.m2ts', '.webm', '.mpg', '.mpeg', '.flv', '.vob'}

# Capítulos que podem ser pulados (nome do capítulo dentro do MKV)
INTRO_RE = re.compile(r'\b(intro|opening|abertura|op|vinheta|theme song)\b', re.I)
RECAP_RE = re.compile(r'\b(recap|resumo|previously|anteriormente)\b', re.I)
OUTRO_RE = re.compile(r'\b(credits?|cr[eé]ditos|ending|ed|encerramento|outro|end ?credits|preview|pr[oó]ximo epis[oó]dio)\b', re.I)
# Nome de arquivo com cara de episódio: S01E02, 1x02, "Ep 5", "Episódio 5", "Nome - 05"
EPISODE_RE = re.compile(r'(s\d{1,2}\s*e\d{1,3}|\b\d{1,2}x\d{2,3}\b|\bep(isode|is[oó]dio)?[\s._-]*\d{1,3}\b|\s-\s\d{1,3}\b)', re.I)
JUNK_RE = re.compile(r'(\[[^\]]*\]|\([^)]*(1080|720|2160|480)[^)]*\)|\b(1080p|720p|2160p|4k|x26[45]|h\.?26[45]|hevc|10bit|web-?dl|webrip|bluray|brrip|aac|ac3|dts|dual|multi)\b.*$)', re.I)


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[Ark] %s' % msg, level)


def setting_bool(key, default=False):
    try:
        return ADDON.getSettingBool(key)
    except Exception:
        return default


def setting_int(key, default=0):
    try:
        return ADDON.getSettingInt(key)
    except Exception:
        return default


def setting_string(key, default=''):
    try:
        return (ADDON.getSettingString(key) or '').strip() or default
    except Exception:
        return default


# ---------------------------------------------------------------- estado em disco
def load_state():
    """Lê o state.json. 'utf-8-sig' porque um BOM (comum quando o arquivo é editado por
    fora) faz o json.load falhar — e aí o save_state seguinte gravaria um estado vazio
    por cima, apagando todo o histórico sem avisar."""
    st = {}
    try:
        with open(STATE_FILE, 'r', encoding='utf-8-sig') as fh:
            st = json.load(fh)
        if not isinstance(st, dict):
            raise ValueError('state.json não é um objeto')
    except FileNotFoundError:
        st = {}
    except Exception as exc:
        st = {'state_ilegivel': True}
        try:  # guarda o arquivo torto antes que alguém grave por cima
            ruim = STATE_FILE + '.ruim'
            if os.path.exists(STATE_FILE) and not os.path.exists(ruim):
                import shutil as _sh
                _sh.copy2(STATE_FILE, ruim)
            log('state.json ilegível (%s); copiei para %s' % (exc, ruim), xbmc.LOGERROR)
        except Exception:
            pass
    st.setdefault('history', {})   # caminho -> {pos, total, ts, done}
    st.setdefault('intros', {})    # pasta -> {start, end}
    st.setdefault('credits', {})   # pasta -> segundos antes do fim
    return st


def save_state(st):
    if st.pop('state_ilegivel', False):
        # não sabemos o que havia antes: gravar agora apagaria o histórico de vez
        log('não vou gravar por cima de um state.json ilegível', xbmc.LOGWARNING)
        return
    os.makedirs(PROFILE, exist_ok=True)
    hist = st.get('history', {})
    if len(hist) > 300:  # mantém só os 300 mais recentes
        keep = sorted(hist.items(), key=lambda kv: kv[1].get('ts', 0), reverse=True)[:300]
        st['history'] = dict(keep)
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


def bump_widgets():
    """Força a tela inicial a recarregar as fileiras do Ark."""
    HOME.setProperty('jk_refresh', str(int(time.time())))


# ---------------------------------------------------------------- cache em disco
CACHE_DIR = os.path.join(PROFILE, 'cache')


def cache_load(nome):
    """Lê um cache em JSON. Nunca levanta: cache ruim é cache vazio."""
    try:
        with open(os.path.join(CACHE_DIR, nome + '.json'), 'r', encoding='utf-8-sig') as fh:
            dados = json.load(fh)
        return dados if isinstance(dados, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        log('cache %s ilegível (%s); começando de novo' % (nome, exc), xbmc.LOGWARNING)
        return {}


def cache_save(nome, dados):
    """Grava o cache com .tmp + os.replace, igual ao state.json."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        alvo = os.path.join(CACHE_DIR, nome + '.json')
        tmp = alvo + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(dados, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, alvo)
    except Exception as exc:
        log('não gravei o cache %s: %s' % (nome, exc), xbmc.LOGWARNING)


def cache_get(nome, chave, dias=30):
    """Valor ainda válido, ou None. Guarda-se {'v': valor, 'ts': quando}."""
    reg = cache_load(nome).get(chave)
    if not isinstance(reg, dict):
        return None
    if dias and (time.time() - reg.get('ts', 0)) > dias * 86400:
        return None
    return reg.get('v')


def cache_put(nome, chave, valor):
    dados = cache_load(nome)
    dados[chave] = {'v': valor, 'ts': int(time.time())}
    cache_save(nome, dados)


# ---------------------------------------------------------------- arquivos
def split_path(path):
    idx = max(path.rfind('/'), path.rfind('\\'))
    return path[:idx + 1], path[idx + 1:]


def is_video(name):
    return os.path.splitext(name)[1].lower() in VIDEO_EXT


def natural_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', text)]


def list_videos(folder):
    try:
        _dirs, files = xbmcvfs.listdir(folder)
    except Exception:
        return []
    vids = [f for f in files if is_video(f) and 'sample' not in f.lower()]
    return sorted(vids, key=natural_key)


SEASON_RE = re.compile(r'^(season|temporada|s)\s*\d+', re.I)


def _first_of_next_season(folder):
    """Acabou a Season 01: emenda no primeiro vídeo da Season 02 (pasta irmã)."""
    parent, here = split_path(folder[:-1])  # folder sempre termina com a barra
    if not parent or not SEASON_RE.match(here):
        return None
    try:
        dirs, _files = xbmcvfs.listdir(parent)
    except Exception:
        return None
    seasons = sorted((d for d in dirs if SEASON_RE.match(d)), key=natural_key)
    if here not in seasons:
        return None
    sep = parent[-1]
    for nxt in seasons[seasons.index(here) + 1:]:
        nf = parent + nxt + sep
        vids = list_videos(nf)
        if vids:
            return nf + vids[0]
    return None


def next_video(path):
    folder, name = split_path(path)
    vids = list_videos(folder)
    if name in vids:
        i = vids.index(name)
        if i + 1 < len(vids):
            return folder + vids[i + 1]
        return _first_of_next_season(folder)
    return None


def looks_like_episode(path):
    return bool(EPISODE_RE.search(split_path(path)[1]))


def nice_title(path):
    name = os.path.splitext(split_path(path)[1])[0]
    name = re.sub(r'[._]+', ' ', name)
    name = JUNK_RE.sub('', name)
    name = re.sub(r'\s{2,}', ' ', name).strip(' -')
    return name or split_path(path)[1]


def folder_name(path):
    """Nome da série/pasta (pula pastas 'Season 01' / 'Temporada 1')."""
    folder = split_path(path)[0].rstrip('/\\')
    name = split_path(folder)[1] or folder
    if re.match(r'^(season|temporada|s)\s*\d+$', name, re.I):
        parent = split_path(folder)[0].rstrip('/\\')
        name = split_path(parent)[1] or name
    return name


def video_thumb(path):
    """URL especial do Kodi 21 que extrai um quadro do próprio vídeo como miniatura."""
    return 'image://video@%s/' % quote(path, safe='')


_KODI_MAJOR = None


def kodi_major():
    global _KODI_MAJOR   # era consultado uma vez por card da fileira
    if _KODI_MAJOR is None:
        try:
            _KODI_MAJOR = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
        except ValueError:
            _KODI_MAJOR = 0
    return _KODI_MAJOR


_FOLDER_ART = {}

ART_NAMES = (('poster', ('poster.jpg', 'poster.png', 'folder.jpg', 'cover.jpg')),
             ('fanart', ('fanart.jpg', 'fanart.png', 'backdrop.jpg', 'background.jpg')))


def _probe_art(folder):
    art = {}
    for key, names in ART_NAMES:
        for n in names:
            if xbmcvfs.exists(folder + n):
                art[key] = folder + n
                break
    return art


def folder_art(folder):
    """Imagem solta na pasta (poster.jpg, folder.jpg, fanart.jpg...).

    O episódio fica em 'Série/Season 01/', mas o poster quase sempre está em 'Série/',
    então quando a pasta é uma temporada olha também a de cima.
    """
    if folder in _FOLDER_ART:
        return _FOLDER_ART[folder]
    art = {}
    if folder[-1:] in ('/', os.sep):
        parent, here = split_path(folder[:-1])
        if parent and SEASON_RE.match(here):
            art.update(_probe_art(parent))
    art.update(_probe_art(folder))  # o que está na própria pasta manda
    _FOLDER_ART[folder] = art
    return art


def art_for(path):
    """Imagem de reserva, para quando o Kodi ainda não baixou nada da internet."""
    fa = folder_art(split_path(path)[0])
    art = {}
    if kodi_major() >= 21 and setting_bool('video_thumbs', False):
        art['thumb'] = art['landscape'] = video_thumb(path)
    elif fa.get('fanart'):
        # poster nunca vira 'landscape': o card é deitado (340x191) e cortaria a imagem no meio
        art['thumb'] = art['landscape'] = fa['fanart']
    art['fanart'] = fa.get('fanart') or art.get('thumb', '')
    if fa.get('poster'):
        art['poster'] = fa['poster']
    art['icon'] = art.get('thumb') or fa.get('poster') or 'DefaultVideo.png'
    return {k: v for k, v in art.items() if v}


def fmt_time(sec):
    sec = int(max(0, sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return '%d:%02d:%02d' % (h, m, s) if h else '%d:%02d' % (m, s)
