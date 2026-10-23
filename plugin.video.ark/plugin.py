# -*- coding: utf-8 -*-
"""
Listas usadas pelas fileiras da tela inicial (e navegáveis em Vídeos > Add-ons):
  ?action=continue  -> Continuar assistindo (inclui o próximo episódio de séries já vistas)
  ?action=recent    -> Adicionados recentemente (arquivos mais novos nas suas pastas)
  ?action=play      -> toca e retoma de onde parou, sem perguntar
  ?action=forget    -> remove um item de "Continuar assistindo"
"""
import json
import os
import sys
import time
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib import jk_common as C
from resources.lib import jk_meta as M
from resources.lib import jk_organize as O

BASE = sys.argv[0]
HANDLE = int(sys.argv[1])
PARAMS = dict(parse_qsl(sys.argv[2].lstrip('?')))
RECENT_CACHE = os.path.join(C.PROFILE, 'recent_cache.json')


def url(**kw):
    return BASE + '?' + urlencode(kw)


ITEMS = []          # os cards da fileira; vão todos de uma vez no fim
LIB = None          # mapa caminho -> dados da biblioteca (2 consultas, não 1 por card)


def lib():
    global LIB
    if LIB is None:
        LIB = M.library_index()
    return LIB


def add_video(path, title, sub, pos=0.0, total=0.0, extra_menu=None):
    li = xbmcgui.ListItem(label=title, label2=sub, offscreen=True)
    art = {}
    tag = li.getVideoInfoTag()
    tag.setMediaType('video')
    d = lib().get(path.lower())  # informações que o Kodi buscou na internet (TMDb)
    if d:
        a = d.get('art', {})
        tag.setDbId(int(d['id']))
        tag.setMediaType(d['type'])
        tag.setPlot(d.get('plot', ''))
        if d.get('year'):
            tag.setYear(int(d['year']))
        if d.get('genre'):
            tag.setGenres(d['genre'])
        if d.get('rating'):
            tag.setRating(float(d['rating']))
        if d['type'] == 'episode':
            show = d.get('showtitle') or title
            tag.setTvShowTitle(show)
            tag.setSeason(int(d.get('season', 0)))
            tag.setEpisode(int(d.get('episode', 0)))
            tag.setTitle(d.get('title') or title)
            li.setLabel(show)
            li.setLabel2('T%s:E%s  %s%s' % (d.get('season', ''), d.get('episode', ''), d.get('title', ''),
                                            ('  •  ' + sub.split('•', 1)[-1].strip()) if '•' in sub else ''))
            land = a.get('thumb') or a.get('tvshow.landscape') or a.get('tvshow.fanart')
            fan = a.get('tvshow.fanart') or a.get('fanart') or land
            poster = a.get('tvshow.poster') or a.get('season.poster')
        else:
            tag.setTitle(d.get('title') or title)
            li.setLabel(d.get('title') or title)
            land = a.get('landscape') or a.get('fanart') or a.get('thumb')
            fan = a.get('fanart') or land
            poster = a.get('poster') or a.get('thumb')
        art.update({k: v for k, v in (('landscape', land), ('fanart', fan), ('poster', poster), ('thumb', land)) if v})
        if land:
            art['icon'] = land
    else:
        tag.setTitle(title)
    if not (art.get('landscape') or art.get('fanart') or art.get('thumb')):
        # o Kodi ainda não baixou nada: tenta imagem solta na pasta (só aqui, para não
        # ficar batendo no disco por card quando a biblioteca já tem a arte)
        art.update(C.art_for(path))
    li.setArt(art)
    if total > 0:
        tag.setDuration(int(total))
    if pos > 0 and total > 0:
        tag.setResumePoint(pos, total)
    li.setProperty('IsPlayable', 'true')
    menu = [('Abrir pasta', 'ActivateWindow(Videos,"%s",return)' % C.split_path(path)[0])]
    if d:
        menu.append(('Buscar informações de novo',
                     'RunPlugin(%s)' % url(action='rescrape', type=d['type'], id=str(d['id']), path=path)))
    if extra_menu:
        menu += extra_menu
    li.addContextMenuItems(menu)
    ITEMS.append((url(action='play', path=path, pos=str(pos)), li, False))


def finish(content='videos'):
    """Manda a fileira inteira de uma vez (era um addDirectoryItem por card)."""
    xbmcplugin.addDirectoryItems(HANDLE, ITEMS, len(ITEMS))
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def list_root():
    for label, action, icon in (('Continuar assistindo', 'continue', 'DefaultInProgressShows.png'),
                                ('Adicionados recentemente', 'recent', 'DefaultRecentlyAddedMovies.png')):
        li = xbmcgui.ListItem(label=label, offscreen=True)
        li.setArt({'icon': icon, 'thumb': icon})
        xbmcplugin.addDirectoryItem(HANDLE, url(action=action), li, isFolder=True)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def list_continue():
    st = C.load_state()
    hist = st['history']
    items = sorted(hist.items(), key=lambda kv: kv[1].get('ts', 0), reverse=True)
    seen_folders = set()
    count = 0
    for path, h in items:
        folder = C.split_path(path)[0]
        if folder in seen_folders:
            continue  # uma entrada por pasta/série, como na Netflix
        forget = [('Remover de Continuar assistindo', 'RunPlugin(%s)' % url(action='forget', path=path))]
        if not h.get('done'):
            if not xbmcvfs.exists(path):
                continue
            # só marca a pasta como usada depois de ter certeza de que vai virar card,
            # senão um arquivo apagado escondia a série inteira
            seen_folders.add(folder)
            pos = h.get('pos', 0) if h.get('pos', 0) > 30 else 0
            if pos:
                left = (h.get('total', 0) - pos) / 60.0
                sub = '%s  •  faltam %d min' % (C.folder_name(path), max(1, round(left)))
            else:
                sub = '%s  •  começar' % C.folder_name(path)
            add_video(path, C.nice_title(path), sub, pos, h.get('total', 0), forget)
            count += 1
        else:
            nxt = C.next_video(path)
            if not nxt or hist.get(nxt, {}).get('done'):
                continue
            seen_folders.add(folder)
            h2 = hist.get(nxt, {})
            add_video(nxt, C.nice_title(nxt), '%s  •  próximo episódio' % C.folder_name(nxt),
                      h2.get('pos', 0), h2.get('total', 0), forget)
            count += 1
        if count >= 40:
            break
    finish()


def video_sources():
    res = rpc('Files.GetSources', media='video')
    out = []
    for s in res.get('result', {}).get('sources', []) or []:
        f = s.get('file', '')
        if f and not f.startswith(('plugin://', 'addons://', 'upnp://', 'videodb://', 'multipath://')):
            out.append(f)
    return out


def scan_recent(max_files=4000, max_depth=5):
    found = []
    stack = [(src, 0) for src in video_sources()]
    while stack and len(found) < max_files:
        folder, depth = stack.pop()
        if not folder.endswith(('/', '\\')):
            folder += '\\' if '\\' in folder else '/'
        try:
            dirs, files = xbmcvfs.listdir(folder)
        except Exception:
            continue
        for f in files:
            if C.is_video(f) and 'sample' not in f.lower():
                p = folder + f
                try:
                    found.append((xbmcvfs.Stat(p).st_mtime(), p))
                except Exception:
                    pass
        if depth < max_depth:
            stack.extend((folder + d, depth + 1) for d in dirs if not d.startswith('.'))
    found.sort(reverse=True)
    return [p for _m, p in found[:400]]


def list_recent():
    paths = None
    try:
        with open(RECENT_CACHE, 'r', encoding='utf-8') as fh:
            cache = json.load(fh)
        if time.time() - cache['ts'] < 5 * 60:
            paths = cache['paths']
    except Exception:
        pass
    if paths is None:
        paths = scan_recent()
        os.makedirs(C.PROFILE, exist_ok=True)
        with open(RECENT_CACHE, 'w', encoding='utf-8') as fh:
            json.dump({'ts': time.time(), 'paths': paths}, fh)
    hist = C.load_state()['history']
    seen = set()
    count = 0
    for p in paths:
        folder = C.split_path(p)[0]
        if C.looks_like_episode(p):
            # série: um card por pasta, no próximo episódio não assistido (ordem 1, 2, 3...)
            if folder in seen:
                continue
            seen.add(folder)
            vids = [folder + v for v in C.list_videos(folder)]
            target = next((v for v in vids if not hist.get(v, {}).get('done')), None)
            if not target:
                continue
            h = hist.get(target, {})
            n = vids.index(target) + 1
            add_video(target, C.nice_title(target), '%s  •  episódio %d de %d' % (C.folder_name(target), n, len(vids)),
                      h.get('pos', 0), h.get('total', 0))
        else:
            h = hist.get(p, {})
            if h.get('done'):
                continue
            add_video(p, C.nice_title(p), C.folder_name(p), h.get('pos', 0), h.get('total', 0))
        count += 1
        if count >= 40:
            break
    finish()


def play():
    path = PARAMS.get('path', '')
    pos = float(PARAMS.get('pos', 0) or 0)
    if not pos:
        pos = C.load_state()['history'].get(path, {}).get('pos', 0)
    if pos > 0:
        C.HOME.setProperty('jk_seek', json.dumps({'path': path, 'pos': pos}))
    li = xbmcgui.ListItem(path=path, offscreen=True)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def forget():
    st = C.load_state()
    st['history'].pop(PARAMS.get('path', ''), None)
    C.save_state(st)
    C.bump_widgets()
    xbmc.executebuiltin('Container.Refresh')


def rpc(method, **params):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    return json.loads(xbmc.executeJSONRPC(json.dumps(req)))


def choose_monitor():
    """Lista os monitores conectados e move o Kodi para o escolhido."""
    res = rpc('Settings.GetSettings', level='expert', filter={'section': 'system', 'category': 'display'})
    setting = None
    for s in res.get('result', {}).get('settings', []):
        if s.get('id') == 'videoscreen.monitor':
            setting = s
            break
    options = (setting or {}).get('options') or []
    if not setting or len(options) < 1:
        # Plataforma sem a opção pela API: abre a tela de Configurações > Sistema > Tela
        xbmcgui.Dialog().ok('Ark', 'Não consegui listar os monitores automaticamente.[CR]'
                            'Vou abrir Sistema > Tela: escolha o monitor na opção "Monitor".')
        xbmc.executebuiltin('ActivateWindow(systemsettings)')
        return
    current = setting.get('value')
    labels = []
    for i, opt in enumerate(options):
        mark = '  (atual)' if opt.get('value') == current else ''
        name = opt.get('label') or opt.get('value')
        if opt.get('value') == 'Default':
            name = 'Padrão (monitor principal do Windows)'
        labels.append('Monitor %d: %s%s' % (i + 1, name, mark))
    idx = xbmcgui.Dialog().select('Em qual monitor o Kodi deve ficar?', labels)
    if idx < 0 or options[idx].get('value') == current:
        return
    rpc('Settings.SetSettingValue', setting='videoscreen.monitor', value=options[idx]['value'])
    xbmcgui.Dialog().notification('Ark', 'Kodi movido para: %s' % (options[idx].get('label') or options[idx]['value']),
                                  time=4000, sound=False)


# Ajustes que mais resolvem "travadinha" em MKV (setting -> (valor, explicação))
MKV_TUNING = [
    ('videoplayer.usedxva2', True, 'Decodificação pela placa de vídeo (DXVA2)'),
    ('videoplayer.adjustrefreshrate', 2, 'Ajustar Hz do monitor ao filme (ao iniciar/parar)'),
    ('videoplayer.usedisplayasclock', True, 'Sincronizar o vídeo com a tela'),
    ('filecache.buffermode', 1, 'Buffer para todos os arquivos (HD externo/rede)'),
    ('filecache.memorysize', 256, 'Pré-carregamento de 256 MB na memória'),
    ('filecache.readfactor', 1000, 'Pré-carregar rápido (10x a velocidade do vídeo)'),
    ('videoplayer.seekdelay', 0, 'Avançar/voltar na hora ao apertar o direcional'),
    ('myvideos.extractthumb', False, 'Não abrir cada vídeo só para gerar miniatura'),
    ('myvideos.extractchapterthumbs', False, 'Não gerar miniatura de cada capítulo'),
]


def optimize_mkv():
    if not xbmcgui.Dialog().yesno('Otimizar reprodução de MKV',
                                  'Liga decodificação pela placa de vídeo, ajuste automático de Hz do monitor '
                                  'e pré-carregamento de 256 MB. Continuar?'):
        return
    ok, fail = 0, []
    for key, value, desc in MKV_TUNING:
        res = rpc('Settings.SetSettingValue', setting=key, value=value)
        if res.get('result') is True:
            ok += 1
        else:
            fail.append(desc)
    lines = ['[B]%d de %d ajustes aplicados:[/B]' % (ok, len(MKV_TUNING))]
    lines += ['  • ' + desc for _k, _v, desc in MKV_TUNING if desc not in fail]
    if fail:
        lines += ['', 'Não disponíveis neste sistema:'] + ['  • ' + d for d in fail]
    lines += ['', '[B]Ainda travando?[/B] Durante o vídeo, segure o botão View (ou tecla O):',
              '  • Linha "Video decoder": se não aparecer (dxva2) ou (d3d11), a placa de vídeo',
              '    não decodifica esse formato (comum em HEVC 10-bit/4K em placas antigas).',
              '  • "Skipped/Dropped" subindo sem parar: CPU/GPU no limite, ou o Kodi está num',
              '    monitor com Hz diferente do outro. Use "Trocar monitor" e teste no outro.']
    xbmcgui.Dialog().textviewer('Ark - Otimizar MKV', '[CR]'.join(lines))


def update_info():
    """Botão 'Atualizar': configura pastas novas e busca informações na internet."""
    st = C.load_state()
    M.scrapers_to_portuguese(st)
    for _i in range(90):  # espera alguma busca em andamento terminar
        if not xbmc.getCondVisibility('Library.IsScanning'):
            break
        xbmc.sleep(1000)
    M.rpc('VideoLibrary.Clean', showdialogs=False)  # tira da biblioteca o que não existe mais
    for _i in range(30):
        xbmc.sleep(1000)
        if not xbmc.getCondVisibility('Library.IsScanning'):
            break
    did = M.auto_configure(st, force_scan=True)
    refresh = st.pop('needs_ptbr_refresh', False)
    C.save_state(st)
    if refresh:
        for _i in range(90):
            if not xbmc.getCondVisibility('Library.IsScanning'):
                break
            xbmc.sleep(1000)
        M.refresh_all_ptbr()  # busca tudo de novo, agora em português
    kinds = {'movies': 'Filmes', 'tvshows': 'Séries', 'tvshow_single': 'Série'}
    if did:
        msg = 'Buscando na internet: ' + ', '.join('%s (%s)' % (l, kinds[k]) for l, k in did)
    else:
        msg = 'Atualizando a biblioteca: novos arquivos vão aparecer em instantes.'
    xbmcgui.Dialog().notification('Ark', msg, time=6000, sound=False)
    C.bump_widgets()



# ---------------------------------------------------------------- "Por tema" (franquias)
def _norm(text):
    import unicodedata, re as _re
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return _re.sub(r'[^\w]+', ' ', text).strip()


def _parent_name(path):
    return _norm(C.folder_name(path)) if path else ''


def build_themes():
    """Junta série + filmes da mesma franquia (ex.: Madoka = série + filmes)."""
    shows = M.rpc('VideoLibrary.GetTVShows', properties=['title', 'originaltitle', 'art', 'file', 'year', 'plot'])
    movies = M.rpc('VideoLibrary.GetMovies', properties=['title', 'originaltitle', 'art', 'file', 'set', 'year', 'plot'])
    shows = shows.get('result', {}).get('tvshows', []) or []
    movies = movies.get('result', {}).get('movies', []) or []
    groups = []
    for sh in shows:
        keys = {k for k in (_norm(sh.get('title')), _norm(sh.get('originaltitle')),
                            _norm(C.folder_name(sh.get('file', '').rstrip('/\\') + '/'))) if len(k) >= 4}
        groups.append({'title': sh.get('title'), 'art': sh.get('art', {}), 'plot': sh.get('plot', ''),
                       'keys': keys, 'shows': [sh], 'movies': []})
    sets = {}
    for mv in movies:
        hay = ' | '.join((_norm(mv.get('title')), _norm(mv.get('originaltitle')), _norm(mv.get('set')),
                          _parent_name(mv.get('file'))))
        g = next((g for g in groups if any(k in hay for k in g['keys'])), None)
        if g:
            g['movies'].append(mv)
        elif mv.get('set'):
            sets.setdefault(mv['set'], []).append(mv)
    for name, mvs in sets.items():
        if len(mvs) >= 2:
            groups.append({'title': name, 'art': mvs[0].get('art', {}), 'plot': mvs[0].get('plot', ''),
                           'keys': {_norm(name)}, 'shows': [], 'movies': mvs})
    return [g for g in groups if len(g['shows']) + len(g['movies']) >= 2]


def _theme_sub(g):
    parts = []
    if g['shows']:
        parts.append('%d série%s' % (len(g['shows']), 's' if len(g['shows']) > 1 else ''))
    if g['movies']:
        parts.append('%d filme%s' % (len(g['movies']), 's' if len(g['movies']) > 1 else ''))
    return '  •  '.join(parts)


def list_themes():
    for g in build_themes():
        a = g['art']
        li = xbmcgui.ListItem(label=g['title'], label2=_theme_sub(g), offscreen=True)
        fan = a.get('fanart') or a.get('landscape') or a.get('poster')
        li.setArt({'fanart': fan, 'landscape': a.get('landscape') or fan, 'thumb': a.get('landscape') or fan,
                   'poster': a.get('poster'), 'icon': a.get('poster') or fan})
        tag = li.getVideoInfoTag()
        tag.setPlot(g['plot'])
        tag.setTitle(g['title'])
        xbmcplugin.addDirectoryItem(HANDLE, url(action='theme', name=g['title']), li, isFolder=True)
    _finish_wall()


def list_theme():
    name = PARAMS.get('name', '')
    g = next((g for g in build_themes() if g['title'] == name), None)
    if not g:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    for sh in g['shows']:
        a = sh.get('art', {})
        li = xbmcgui.ListItem(label='Série: %s' % sh['title'], label2='Temporadas e episódios', offscreen=True)
        li.setArt({'fanart': a.get('fanart'), 'poster': a.get('poster'), 'thumb': a.get('poster') or a.get('fanart'),
                   'landscape': a.get('landscape') or a.get('fanart'), 'icon': a.get('poster')})
        tag = li.getVideoInfoTag()
        tag.setPlot(sh.get('plot', ''))
        tag.setMediaType('tvshow')
        tag.setDbId(int(sh['tvshowid']))
        xbmcplugin.addDirectoryItem(HANDLE, 'videodb://tvshows/titles/%d/' % sh['tvshowid'], li, isFolder=True)
    hist = C.load_state()['history']
    for mv in sorted(g['movies'], key=lambda m: m.get('year') or 0):
        h = hist.get(mv['file'], {})
        add_video(mv['file'], mv['title'], 'Filme  •  %s' % (mv.get('year') or ''), h.get('pos', 0), h.get('total', 0))
    _finish_wall()


def rescrape():
    """Tira o item da biblioteca e busca de novo (usa o .nfo da pasta, se existir)."""
    kind, dbid, path = PARAMS.get('type'), int(PARAMS.get('id', 0) or 0), PARAMS.get('path', '')
    if not dbid:
        return
    if not xbmcgui.Dialog().yesno('Ark', 'Buscar as informações deste item de novo na internet?[CR]'
                                  'Dica: um arquivo .nfo com o link do TMDb ao lado do vídeo força a identificação certa.'):
        return
    if kind == 'movie':
        M.rpc('VideoLibrary.RemoveMovie', movieid=dbid)
    elif kind == 'episode':
        M.rpc('VideoLibrary.RemoveEpisode', episodeid=dbid)
    M.scan(C.split_path(path)[0])
    xbmcgui.Dialog().notification('Ark', 'Buscando de novo... aparece em instantes.', time=5000, sound=False)
    C.bump_widgets()
    xbmc.executebuiltin('Container.Refresh')


def _finish_wall():
    """Mantém a ordem (série primeiro, filmes por ano) e mostra em grade de pôsteres."""
    if ITEMS:
        xbmcplugin.addDirectoryItems(HANDLE, ITEMS, len(ITEMS))
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
    # como fileira da tela inicial isso reconfigurava o container que estivesse aberto
    if xbmc.getCondVisibility('Window.IsActive(videos)'):
        xbmc.executebuiltin('Container.SetViewMode(500)')  # visão "Parede" (pôsteres) da skin



# ---------------------------------------------------------------- "Adicionar e organizar"


def _saved_folders():
    return C.load_state().get('folders', {})


def _roots():
    """Pastas de Séries e Filmes (o módulo do organizador é quem decide, para o serviço
    e o plugin nunca discordarem sobre onde as coisas ficam)."""
    return O.roots()


def _downloads_root():
    return O.watch_root()


def _sep(path):
    return '\\' if '\\' in path else '/'


def _tidy(path):
    """Sem barra no fim, para comparar e mostrar."""
    return (path or '').rstrip('/\\')


def _write_source(name, path):
    """Troca (ou cria) a fonte de vídeo com esse nome no sources.xml.

    Não existe JSON-RPC para mexer em fontes, e o Kodi só lê este arquivo ao abrir.
    """
    import xml.etree.ElementTree as ET
    f = xbmcvfs.translatePath('special://profile/sources.xml')
    try:
        tree = ET.parse(f)
        root = tree.getroot()
    except Exception:
        root = ET.Element('sources')
        tree = ET.ElementTree(root)
    video = root.find('video')
    if video is None:
        video = ET.SubElement(root, 'video')
    alvo = None
    for src in video.findall('source'):
        n = src.find('name')
        if n is not None and _norm(n.text or '') == _norm(name):
            alvo = src
            break
    if alvo is None:
        alvo = ET.SubElement(video, 'source')
        ET.SubElement(alvo, 'name').text = name
        ET.SubElement(alvo, 'allowsharing').text = 'true'
    p = alvo.find('path')
    if p is None:
        p = ET.SubElement(alvo, 'path')
    p.set('pathversion', '1')
    p.text = path
    try:
        tree.write(f, encoding='utf-8', xml_declaration=False)
        return True
    except Exception as exc:
        C.log('não consegui escrever sources.xml: %s' % exc, xbmc.LOGERROR)
        return False


def _move_videos(origem, destino):
    """Leva os vídeos da pasta antiga para a nova (mesmo disco = instantâneo)."""
    origem, destino = _tidy(origem), _tidy(destino)
    if not origem or not destino or origem == destino or not xbmcvfs.exists(origem + _sep(origem)):
        return 0
    so, sd = _sep(origem), _sep(destino)
    try:
        dirs, files = xbmcvfs.listdir(origem + so)
    except Exception:
        return 0
    tarefas = [(origem + so + d, destino + sd + d) for d in dirs]
    tarefas += [(origem + so + f, destino + sd + f) for f in files if C.is_video(f)]
    if not tarefas:
        return 0
    prog = xbmcgui.DialogProgress()
    prog.create('Ark', 'Movendo seus vídeos para a pasta nova...')
    movidos = 0
    for i, (de, para) in enumerate(tarefas):
        if prog.iscanceled():
            break
        prog.update(int(i * 100 / len(tarefas)), C.split_path(_tidy(de))[1])
        try:
            if xbmcvfs.rename(de, para):
                movidos += 1
            elif xbmcvfs.copy(de, para):
                xbmcvfs.delete(de)
                movidos += 1
        except Exception as exc:
            C.log('não movi %s: %s' % (de, exc), xbmc.LOGWARNING)
    prog.close()
    return movidos


def _pick(titulo, atual):
    escolha = xbmcgui.Dialog().browse(0, titulo, 'files', '', False, True, _tidy(atual) + _sep(atual or 'C:\\'))
    escolha = _tidy(escolha)
    if not escolha or escolha == _tidy(atual):
        return None
    if 'onedrive' in escolha.lower():
        if not xbmcgui.Dialog().yesno('Cuidado com o OneDrive',
                                      'Essa pasta está dentro do OneDrive. Ele fica subindo os vídeos para a '
                                      'internet e pode deixá-los "só na nuvem", e aí o Ark não abre.'
                                      '[CR][CR]Usar mesmo assim?', yeslabel='Usar', nolabel='Escolher outra'):
            return None
    return escolha


def choose_folders():
    """Escolher, pelo próprio app, onde ficam as séries, os filmes e os downloads."""
    series, filmes = _roots()
    downloads = _downloads_root()
    series0, filmes0 = series, filmes
    while True:
        opcoes = ['Séries:  %s' % (_tidy(series) or '(escolher)'),
                  'Filmes:  %s' % (_tidy(filmes) or '(escolher)'),
                  'De onde organizar:  %s' % _tidy(downloads),
                  '[B]Salvar e aplicar[/B]']
        i = xbmcgui.Dialog().select('Onde ficam seus vídeos', opcoes)
        if i < 0:
            return
        if i == 0:
            series = _pick('Pasta das séries', series) or series
        elif i == 1:
            filmes = _pick('Pasta dos filmes', filmes) or filmes
        elif i == 2:
            downloads = _pick('Pasta de onde organizar (Downloads)', downloads) or downloads
        else:
            break
    if _tidy(series) and _tidy(series) == _tidy(filmes):
        xbmcgui.Dialog().ok('Ark', 'Séries e Filmes não podem ser a mesma pasta.')
        return
    st = C.load_state()
    st['folders'] = {'series': _tidy(series), 'filmes': _tidy(filmes), 'downloads': _tidy(downloads)}
    C.save_state(st)

    mudou = []
    for nome, novo, antigo, tipo in (('Series', series, series0, 'tvshows'), ('Filmes', filmes, filmes0, 'movies')):
        novo_t = _tidy(novo)
        if not novo_t or novo_t == _tidy(antigo):
            continue
        mudou.append(nome)
        alvo = novo_t + _sep(novo_t)
        M.set_content(alvo, tipo)
        _write_source(nome, alvo)
        if _tidy(antigo) and xbmcgui.Dialog().yesno(
                'Mover o que já existe?',
                'Levar os vídeos de[CR][B]%s[/B][CR]para[CR][B]%s[/B]?[CR][CR]'
                'No mesmo disco é instantâneo.' % (_tidy(antigo), novo_t),
                yeslabel='Mover', nolabel='Deixar onde está'):
            n = _move_videos(antigo, novo_t)
            xbmcgui.Dialog().notification('Ark', '%d item(ns) movido(s).' % n, time=4000, sound=False)
        M.scan(alvo)
    if mudou:
        M.rpc('VideoLibrary.Clean', showdialogs=False)
        xbmcgui.Dialog().ok('Pastas salvas',
                            'Pasta de %s atualizada.[CR][CR]Já estou buscando capas e sinopses. '
                            'A aba [B]Pastas[/B] do menu só mostra o caminho novo depois que você fechar e '
                            'abrir o Ark de novo.' % ' e '.join(mudou))
    else:
        xbmcgui.Dialog().notification('Ark', 'Pastas salvas.', time=3000, sound=False)
    C.bump_widgets()


def tidy_library(perguntar=True):
    """Arruma as séries que já estão na pasta de Séries (uma vez só).

    Mexe em arquivos que hoje funcionam, por isso pergunta antes e devolve o
    'assistido'/'retomar' depois — o Kodi guarda isso por caminho e mover zera tudo.
    """
    series_root, _filmes = _roots()
    if not series_root:
        return 0
    plans = O.plan_tidy(series_root)
    if not plans:
        return 0
    if perguntar:
        linhas = O.resumo(plans, series_root, None)
        resto = ''
        if len(linhas) > 4:
            resto = '[CR]... e mais %d pasta(s)' % (len(linhas) - 3)
            linhas = linhas[:3]
        if not xbmcgui.Dialog().yesno(
                'Arrumar %d vídeo(s) nas suas séries?' % len(plans),
                '%s%s' % ('[CR]'.join(linhas), resto),
                yeslabel='Arrumar', nolabel='Deixar como está'):
            return 0
    guarda = O.watched_snapshot()
    _movidos, feitos = O.apply_moves(plans)
    M.rpc('VideoLibrary.Clean', showdialogs=False)
    for _i in range(60):
        if not xbmc.getCondVisibility('Library.IsScanning'):
            break
        xbmc.sleep(1000)
    M.scan()
    for _i in range(10):
        xbmc.sleep(1000)
        if xbmc.getCondVisibility('Library.IsScanning'):
            break
    for _i in range(120):
        if not xbmc.getCondVisibility('Library.IsScanning'):
            break
        xbmc.sleep(1000)
    devolvidos = O.restore_watched(guarda, feitos)
    C.log('arrumei %d arquivo(s) nas séries; devolvi assistido de %d' % (len(feitos), devolvidos))
    C.bump_widgets()
    return len(feitos)


def _tidy_once():
    """A arrumação da biblioteca existente roda uma vez só, no primeiro uso do botão."""
    st = C.load_state()
    if st.get('tidy_v1'):
        return
    st['tidy_v1'] = True
    C.save_state(st)
    tidy_library()


def organize_downloads():
    series_root, filmes_root = _roots()
    if not series_root and not filmes_root:
        xbmcgui.Dialog().ok('Ark', 'Não achei as pastas Séries/Filmes cadastradas no Kodi.')
        return
    plans = O.plan_folder(_downloads_root(), _tidy(series_root), _tidy(filmes_root))
    if not plans:
        xbmcgui.Dialog().ok('Ark', 'Nenhum vídeo novo para organizar.[CR][CR]'
                            'Pode arrastar a pasta inteira da série para a pasta de downloads: '
                            'o Ark entra nas subpastas e usa o nome da pasta quando o '
                            'nome do arquivo não diz qual é a série.')
        _tidy_once()
        return
    # Resumo agrupado por série/temporada. Nada de multiselect aqui: a skin (como a Estuary)
    # não desenha visto nenhum, dava para desmarcar sem perceber e o arquivo ficava para trás.
    linhas = O.resumo(plans, _tidy(series_root), _tidy(filmes_root))
    resto = ''
    if len(linhas) > 4:   # o diálogo Sim/Não do Kodi só mostra 4 linhas e corta o resto calado
        resto = '[CR]... e mais %d pasta(s)' % (len(linhas) - 3)
        linhas = linhas[:3]
    if not xbmcgui.Dialog().yesno('Organizar %d vídeo(s)' % len(plans),
                                  '%s%s' % ('[CR]'.join(linhas), resto),
                                  yeslabel='Organizar', nolabel='Agora não'):
        return
    moved, _feitos = O.apply_moves(plans)
    st = C.load_state()
    M.scrapers_to_portuguese(st)
    M.auto_configure(st)
    C.save_state(st)
    M.scan()
    xbmcgui.Dialog().notification('Ark', '%d vídeo(s) organizados. Buscando capas e sinopses...' % moved,
                                  time=6000, sound=False)
    C.bump_widgets()

    _tidy_once()


def open_folder():
    series_root, filmes_root = _roots()
    path = series_root if PARAMS.get('which') == 'series' else filmes_root
    if not path:
        return
    try:
        import subprocess
        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', path])
        else:
            subprocess.Popen(['xdg-open', path])
    except Exception:
        xbmc.executebuiltin('ActivateWindow(Videos,"%s",return)' % path)


def show_help():
    series_root, filmes_root = _roots()
    series_root = (series_root or 'C:\\Kodi\\Series').rstrip('/\\')
    filmes_root = (filmes_root or 'C:\\Kodi\\Filmes').rstrip('/\\')
    txt = """[B]Como colocar séries e filmes novos[/B]

[B]Jeito fácil:[/B] baixe normalmente para a pasta Downloads e aperte [B]Organizar Downloads[/B]
na tela inicial. O Ark coloca cada vídeo na pasta certa e busca capa, fundo e sinopse.

[B]Jeito manual:[/B]
  • Série:  %s\\Nome da Série\\Season 01\\Nome da Série S01E01.mkv
  • Filme:  %s\\Nome do Filme (2021).mkv
  Depois aperte [B]Atualizar capas[/B].

[B]Dicas para as imagens aparecerem:[/B]
  • O nome tem que ser o da série/filme (em português ou inglês).
  • Episódios com S01E01, S01E02...; filmes com o ano entre parênteses.
  • Não misture filmes e séries na mesma pasta.
  • Identificou errado? Menu (botão X / tecla C) no item > [B]Buscar informações de novo[/B].
  • Precisa de internet. As imagens aparecem em 1 a 2 minutos.""" % (series_root or 'C:\\Kodi\\Series', filmes_root or 'C:\\Kodi\\Filmes')
    xbmcgui.Dialog().textviewer('Ark - Como adicionar', txt)


ROUTES = {'organize': organize_downloads, 'open_folder': open_folder, 'help': show_help, 'folders': choose_folders, 'rescrape': rescrape, 'themes': list_themes, 'theme': list_theme, 'continue': list_continue, 'update': update_info, 'recent': list_recent, 'play': play, 'forget': forget,
          'monitor': choose_monitor, 'optimize': optimize_mkv}

if __name__ == '__main__':
    ROUTES.get(PARAMS.get('action'), list_root)()
