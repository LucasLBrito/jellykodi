# -*- coding: utf-8 -*-
"""
Informações da internet (sinopse, capa, fundo, elenco, nota) usando os buscadores
que já vêm no Kodi 21 (The Movie Database - TMDb), em português do Brasil.

- Detecta se cada pasta de vídeo tem FILMES ou SÉRIES (pelo nome dos arquivos).
- Configura a pasta como o menu "Definir conteúdo" do Kodi faria.
- Manda o Kodi atualizar a biblioteca (ele busca tudo na internet).
- Depois, as fileiras usam essas informações (file_details).
"""
import glob
import json
import os
import sqlite3

import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib import jk_common as C

MOVIE_SCRAPER = 'metadata.themoviedb.org.python'
TV_SCRAPER = 'metadata.tvshows.themoviedb.org.python'
INT_MAX = 2147483647
# idioma gravado na própria pasta (sem isso o Kodi usa o padrão do buscador, em inglês).
# languageDetails é o que manda no buscador de séries 1.7+; language serve para o de filmes.
PTBR_SETTINGS = ('<settings version="2">'
                 '<setting id="language">pt-BR</setting>'
                 '<setting id="languageDetails">pt-BR</setting>'
                 '<setting id="languageImages">pt-BR</setting>'
                 '<setting id="tmdbcertcountry">br</setting>'
                 '</settings>')


def rpc(method, **params):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except Exception:
        return {}


# ---------------------------------------------------------------- idioma dos buscadores
def scrapers_to_portuguese(state):
    """Uma vez só: TMDb em pt-BR e classificação indicativa do Brasil.

    Cuidado: o buscador de séries 1.7 trocou o nome do ajuste. Quem decide o idioma do
    título e da sinopse agora é 'languageDetails'; o antigo 'language' nem existe mais lá.
    Gravar só 'language' deixa tudo em inglês. O de filmes ainda usa 'language'.
    """
    if state.get('scrapers_ptbr_v2'):
        return False
    changed = False
    for sid in (MOVIE_SCRAPER, TV_SCRAPER):
        try:
            a = xbmcaddon.Addon(sid)
        except Exception as exc:
            C.log('buscador %s indisponível: %s' % (sid, exc), xbmc.LOGWARNING)
            continue
        for key, val in (('language', 'pt-BR'), ('languageDetails', 'pt-BR'),
                         ('languageImages', 'pt-BR'), ('tmdbcertcountry', 'br')):
            try:
                atual = a.getSetting(key)
            except Exception:
                continue
            if atual and atual != val:   # vazio = o buscador não tem esse ajuste
                try:
                    a.setSetting(key, val)
                    changed = True
                    C.log('%s: %s = %s' % (sid, key, val))
                except Exception:
                    pass
    state['scrapers_ptbr_v2'] = True
    if changed:
        state['needs_ptbr_refresh'] = True
    return changed


# ---------------------------------------------------------------- detecção
def detect_kind(source):
    """'movies', 'tvshows' (pasta com várias séries) ou 'tvshow_single' (pasta = uma série)."""
    root_eps = root_movies = sub_eps = sub_movies = 0
    try:
        dirs, files = xbmcvfs.listdir(source)
    except Exception:
        return None
    for f in files:
        if C.is_video(f):
            if C.looks_like_episode(f):
                root_eps += 1
            else:
                root_movies += 1
    sep = '\\' if '\\' in source else '/'
    for d in dirs[:40]:
        sub = source + d + sep
        try:
            sdirs, sfiles = xbmcvfs.listdir(sub)
        except Exception:
            continue
        vids = [f for f in sfiles if C.is_video(f)]
        # séries costumam ter "Season 1"/"Temporada 1" dentro
        for sd in sdirs[:10]:
            try:
                _d, ssf = xbmcvfs.listdir(sub + sd + sep)
                vids += [f for f in ssf if C.is_video(f)]
            except Exception:
                pass
        for f in vids:
            if C.looks_like_episode(f):
                sub_eps += 1
            else:
                sub_movies += 1
    if root_eps + root_movies + sub_eps + sub_movies == 0:
        return None
    if root_eps >= 2 and root_eps >= root_movies and sub_eps + sub_movies <= root_eps:
        return 'tvshow_single'
    if sub_eps + root_eps > sub_movies + root_movies:
        return 'tvshows'
    return 'movies'


# ---------------------------------------------------------------- banco de dados do Kodi
def _video_db():
    dbs = glob.glob(os.path.join(xbmcvfs.translatePath('special://database/'), 'MyVideos*.db'))
    if not dbs:
        return None
    return max(dbs, key=lambda p: int(''.join(ch for ch in os.path.basename(p) if ch.isdigit()) or 0))


def get_content(source):
    db = _video_db()
    if not db:
        return None
    try:
        con = sqlite3.connect(db, timeout=10)
        row = con.execute('SELECT strContent FROM path WHERE strPath=?', (source,)).fetchone()
        con.close()
        return row[0] if row else ''
    except Exception as exc:
        C.log('lendo banco: %s' % exc, xbmc.LOGWARNING)
        return None


def set_content(source, kind):
    """Equivale ao menu 'Definir conteúdo' do Kodi para esta pasta."""
    db = _video_db()
    if not db:
        return False
    if kind == 'movies':
        vals = ('movies', MOVIE_SCRAPER, INT_MAX, 0)
    elif kind == 'tvshows':
        vals = ('tvshows', TV_SCRAPER, 0, 0)
    elif kind == 'tvshow_single':
        vals = ('tvshows', TV_SCRAPER, 0, 1)
    else:
        return False
    try:
        con = sqlite3.connect(db, timeout=15)
        cur = con.execute('SELECT idPath FROM path WHERE strPath=?', (source,))
        row = cur.fetchone()
        if row:
            con.execute('UPDATE path SET strContent=?, strScraper=?, scanRecursive=?, useFolderNames=?, '
                        'strSettings=?, noUpdate=0, exclude=0 WHERE idPath=?', vals + (PTBR_SETTINGS, row[0]))
        else:
            con.execute('INSERT INTO path (strPath, strContent, strScraper, scanRecursive, useFolderNames, '
                        'strSettings, noUpdate, exclude, allAudio) VALUES (?,?,?,?,?,?,0,0,0)', (source,) + vals + (PTBR_SETTINGS,))
        con.commit()
        con.close()
        C.log('pasta %s configurada como %s' % (source, kind))
        return True
    except Exception as exc:
        C.log('não consegui configurar %s: %s' % (source, exc), xbmc.LOGERROR)
        return False


def ensure_ptbr(source):
    """Pastas configuradas antes sem idioma: grava pt-BR. Retorna True se mudou algo."""
    db = _video_db()
    if not db:
        return False
    try:
        con = sqlite3.connect(db, timeout=15)
        # compara com o texto inteiro: assim, quando o Ark muda os ajustes de idioma
        # (ex.: languageDetails novo), a pasta é regravada em vez de passar batido
        cur = con.execute("UPDATE path SET strSettings=? WHERE strPath=? AND strScraper LIKE 'metadata.%themoviedb%' "
                          "AND (strSettings IS NULL OR strSettings<>?)",
                          (PTBR_SETTINGS, source, PTBR_SETTINGS))
        changed = cur.rowcount > 0
        con.commit()
        con.close()
        return changed
    except Exception as exc:
        C.log('ensure_ptbr: %s' % exc, xbmc.LOGWARNING)
        return False


def refresh_all_ptbr():
    """Busca de novo, em português, tudo que já está na biblioteca."""
    for sh in rpc('VideoLibrary.GetTVShows').get('result', {}).get('tvshows', []) or []:
        rpc('VideoLibrary.RefreshTVShow', tvshowid=sh['tvshowid'], ignorenfo=False, refreshepisodes=True)
        xbmc.sleep(250)   # sem isso vira uma rajada de pedidos ao TMDb
    for mv in rpc('VideoLibrary.GetMovies').get('result', {}).get('movies', []) or []:
        rpc('VideoLibrary.RefreshMovie', movieid=mv['movieid'], ignorenfo=False)
        xbmc.sleep(250)


def scan(path=None):
    if path:
        rpc('VideoLibrary.Scan', directory=path, showdialogs=False)
    else:
        rpc('VideoLibrary.Scan', showdialogs=False)


def video_sources():
    res = rpc('Files.GetSources', media='video')
    out = []
    for s in res.get('result', {}).get('sources', []):
        path = s.get('file', '')
        if path.startswith('multipath://'):
            continue  # pasta com vários caminhos: o usuário configura pelo Kodi
        if path.startswith(('plugin://', 'addons://', 'upnp://', 'videodb://')):
            continue
        out.append((s.get('label', path), path))
    return out


def auto_configure(state, force_scan=False):
    """Para cada pasta nova sem conteúdo definido: detecta, configura e busca na internet."""
    handled = state.setdefault('auto_sources', {})
    did = []
    ptbr_done = state.setdefault('ptbr_sources_v2', [])
    if force_scan:
        ptbr_done = state['ptbr_sources_v2'] = []   # "Atualizar" reaplica o pt-BR
    for label, path in video_sources():
        if path not in ptbr_done:   # era uma escrita no banco a cada 120 s, por pasta
            if ensure_ptbr(path):   # vale também para pastas configuradas antes
                state['needs_ptbr_refresh'] = True
            ptbr_done.append(path)
        if path in handled and not force_scan:
            continue
        content = get_content(path)
        if content:  # já configurada (por você ou antes)
            handled[path] = content
            continue
        kind = detect_kind(path)
        if kind and set_content(path, kind):
            handled[path] = kind
            did.append((label, kind))
        # kind None = pasta vazia por enquanto: tenta de novo depois
    if did or force_scan:
        scan()  # uma atualização só (o Kodi ignora pedidos enquanto uma já está rodando)
    return did


# ---------------------------------------------------------------- usar as informações
FILE_FIELDS = ['title', 'plot', 'art', 'showtitle', 'season', 'episode', 'year', 'genre', 'runtime', 'rating']


def file_details(path):
    """Informações da biblioteca para um arquivo (se o Kodi já buscou na internet)."""
    res = rpc('Files.GetFileDetails', file=path, media='video', properties=FILE_FIELDS)
    d = res.get('result', {}).get('filedetails')
    if not d or d.get('type') not in ('movie', 'episode') or not d.get('id'):
        return None
    return d


# O Kodi não aceita as mesmas propriedades para episódio e filme: episódio não tem
# 'year' nem 'genre' (tem 'firstaired'), e pedir isso faz a consulta inteira ser recusada.
EPISODE_FIELDS = ['title', 'plot', 'art', 'runtime', 'rating', 'file', 'showtitle', 'season', 'episode', 'firstaired']
MOVIE_FIELDS = ['title', 'plot', 'art', 'runtime', 'rating', 'file', 'year', 'genre']


def library_index():
    """Mapa caminho -> dados da biblioteca.

    Antes cada card da fileira fazia um Files.GetFileDetails (uns 40 por fileira).
    Aqui são duas consultas no total, e a fileira monta a partir do mapa.
    """
    idx = {}
    for method, key, kind, props in (
            ('VideoLibrary.GetEpisodes', 'episodes', 'episode', EPISODE_FIELDS),
            ('VideoLibrary.GetMovies', 'movies', 'movie', MOVIE_FIELDS)):
        res = rpc(method, properties=props)
        if 'error' in res:
            C.log('%s: %s' % (method, res['error']), xbmc.LOGWARNING)
            continue
        for d in res.get('result', {}).get(key, []) or []:
            path = d.get('file')
            if not path:
                continue
            d['type'] = kind
            d['id'] = d.get('episodeid') or d.get('movieid')
            if kind == 'episode' and d.get('firstaired'):
                d['year'] = d['firstaired'][:4]
            idx[path.lower()] = d
    return idx


# ---------------------------------------------------------------- capa e sinopse
TMDB_SITE = 'https://www.themoviedb.org'


def _escapar(texto):
    return (str(texto or '')
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def _ja_e_nosso(caminho):
    """Só mexemos em .nfo que o próprio Ark escreveu."""
    return caminho in (C.load_state().get('nfos_ark') or [])


def _anotar_nfo(caminho):
    st = C.load_state()
    lista = st.get('nfos_ark') or []
    if caminho not in lista:
        lista.append(caminho)
        st['nfos_ark'] = lista[-2000:]
        C.save_state(st)


def _gravar(caminho, texto):
    if os.path.exists(caminho) and not _ja_e_nosso(caminho):
        # .nfo que o usuário (ou outro programa) pôs ali manda mais que o nosso
        return False
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'w', encoding='utf-8') as fh:
            fh.write(texto)
        _anotar_nfo(caminho)
        return True
    except Exception as exc:
        C.log('não gravei %s: %s' % (caminho, exc), xbmc.LOGWARNING)
        return False


def nfo_ponteiro(caminho, tmdb_id, serie):
    """.nfo com só o link do TMDb.

    É a forma mais segura: o Kodi reconhece um .nfo que contém apenas uma URL e manda
    o scraper buscar aquele id — ou seja, nós resolvemos a identificação (a parte que
    o scraper erra quando o nome do arquivo está sujo) e ele continua trazendo sinopse,
    elenco, arte e nomes de episódio em pt-BR. Um .nfo *completo* faria o contrário:
    o Kodi ignoraria o scraper e ficaria preso ao que escrevemos.

    É a mesma dica que o Ark já dá ao usuário na ajuda e no LEIA-ME.
    """
    url = '%s/%s/%s' % (TMDB_SITE, 'tv' if serie else 'movie', tmdb_id)
    return _gravar(caminho, url + '\n')


def nfo_completo(caminho, dados, serie):
    """.nfo de verdade, para o que o TMDb não acha (anime obscuro que só o AniList tem).

    Aqui tomar o volante é o certo: sem isto o item fica sem capa e sem sinopse.
    """
    raiz = 'tvshow' if serie else 'movie'
    linhas = ['<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>',
              '<%s>' % raiz,
              '  <title>%s</title>' % _escapar(dados.get('titulo'))]
    if dados.get('ano'):
        linhas.append('  <year>%s</year>' % _escapar(dados['ano']))
        if not serie:
            linhas.append('  <premiered>%s-01-01</premiered>' % _escapar(dados['ano']))
    if dados.get('sinopse'):
        linhas.append('  <plot>%s</plot>' % _escapar(dados['sinopse']))
    for tipo, valor in (dados.get('ids') or {}).items():
        if valor:
            linhas.append('  <uniqueid type="%s">%s</uniqueid>'
                          % (_escapar(tipo), _escapar(valor)))
    linhas.append('</%s>' % raiz)
    return _gravar(caminho, '\n'.join(linhas) + '\n')


def baixar_arte(pasta, dados):
    """poster.jpg e fanart.jpg na pasta, com os nomes que C.folder_art já procura.

    Nunca sobrescreve: se já existe arte local, ou se o TMDb é a fonte (e portanto o
    Kodi vai baixar a dele), não encostamos.
    """
    from resources.lib import jk_net as N
    if not C.setting_bool('meta_download_art', True):
        return 0
    quantas = 0
    for chave, nome in (('poster', 'poster.jpg'), ('fanart', 'fanart.jpg')):
        url = (dados or {}).get(chave)
        alvo = os.path.join(pasta, nome)
        if not url or os.path.exists(alvo):
            continue
        if N.baixar(url, alvo):
            quantas += 1
    if quantas:
        C._FOLDER_ART.clear()     # o cache de arte por pasta ficou velho
    return quantas


def semear_metadados(grupos, progresso=None):
    """Põe .nfo (e arte quando precisa) ao lado do que acabou de ser organizado.

    Roda ANTES do M.scan(): é o scan que lê o .nfo. Devolve quantos grupos receberam
    alguma coisa.
    """
    if not C.setting_bool('meta_write_nfo', True):
        return 0
    feitos = 0
    uteis = [g for g in grupos or [] if not g.pular and g.tipo != 'desconhecido']
    for i, g in enumerate(uteis):
        if progresso:
            progresso(i, len(uteis), g.titulo)
        itens = [it for it in g.itens if it.destino]
        if not itens:
            continue
        serie = g.tipo in ('serie', 'misto')
        dados = dict(g.meta or {})
        dados.setdefault('titulo', g.titulo)
        dados.setdefault('ano', g.ano)
        ids = dados.get('ids') or {}

        if serie:
            # <series_root>/<Show>/Season NN/arquivo -> queremos <series_root>/<Show>
            pasta = os.path.dirname(os.path.dirname(itens[0].destino))
            alvo = os.path.join(pasta, 'tvshow.nfo')
        else:
            pasta = os.path.dirname(itens[0].destino)
            alvo = os.path.join(pasta, 'movie.nfo')

        if ids.get('tmdb'):
            if nfo_ponteiro(alvo, ids['tmdb'], serie):
                feitos += 1
            continue                      # o scraper do Kodi traz o resto em pt-BR
        if ids.get('anilist') or dados.get('sinopse'):
            if nfo_completo(alvo, dados, serie):
                feitos += 1
            baixar_arte(pasta, dados)
    return feitos
