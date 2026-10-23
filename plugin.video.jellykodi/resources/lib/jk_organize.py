# -*- coding: utf-8 -*-
"""Organizador de pastas: acha os vídeos, descobre série/temporada/episódio e move.

Usado pelo botão "Organizar Downloads" (plugin.py) e pelo organizador automático
do serviço (service.py), por isso mora aqui e não dentro do plugin.
"""
import csv
import os
import re
import shutil
import time
import unicodedata

import xbmc

from resources.lib import jk_common as C

# Download/cópia pela metade: nunca tocar nestes
PARTIAL_EXT = ('.opdownload', '.part', '.crdownload', '.!qb', '.tmp', '.download', '.partial')
SUB_EXT = ('.srt', '.ass', '.ssa', '.sub', '.idx', '.vtt')
MAX_DEPTH = 4

# "Season 02", "S2", "Temporada 3", "Livro 1", "Book 2"
SEASON_DIR_RE = re.compile(r'^(?:season|temporada|livro|book|s)\s*[._-]?\s*(\d{1,2})$', re.I)
# nome do arquivo que é só um número: "01", "05 - titulo", "Ep 7", "Episodio 12"
ONLY_NUMBER_RE = re.compile(r'^(?:ep|epis[oó]dio|episode|cap[ií]tulo)?\s*[._-]*\s*(\d{1,3})(?:\s*[-–]\s*.*)?$', re.I)

LOG_NOME = 'organizacao-log.csv'
LOG_HIST = 'organizacao-historico.csv'


def log_dir():
    """Onde gravar o log de desfazer: a pasta que contém a de Séries (normalmente
    C:\\Kodi). Nada de caminho fixo — o amigo pode ter instalado em outro lugar."""
    series = C.load_state().get('folders', {}).get('series')
    if not series:
        for label, path in _video_sources_quietas():
            if 'serie' in norm(label):
                series = path
                break
    pai = os.path.dirname((series or '').rstrip('/\\'))
    return pai if pai and os.path.isdir(pai) else C.PROFILE


def _video_sources_quietas():
    try:
        from resources.lib import jk_meta as M
        return M.video_sources()
    except Exception:
        return []


def norm(text):
    """Compara nomes sem ligar para acento, maiúscula ou símbolo."""
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r'[^\w]+', ' ', text).strip()


def clean_name(text):
    text = re.sub(r'\[[^\]]*\]|\([^)]*(1080|720|2160|480)[^)]*\)', ' ', text)
    text = re.sub(r'[._]+', ' ', text)
    return re.sub(r'\s{2,}', ' ', text).strip(' -')


def tidy_show(show):
    show = re.sub(r"[^\w\s'&!,.-]", ' ', show or '')
    return re.sub(r'\s{2,}', ' ', show).strip(' -.')


def season_from_dir(name):
    m = SEASON_DIR_RE.match((name or '').strip())
    return int(m.group(1)) if m else None


def is_partial(name):
    low = name.lower()
    return low.endswith(PARTIAL_EXT)


# ---------------------------------------------------------------- leitura do nome do arquivo
def parse_filename(base):
    """(show, temporada, episodio) pelo nome do arquivo, ou None se o nome não disser."""
    m = re.search(r'^(.*?)[ ._-]*[Ss](\d{1,2})[ ._-]*[Ee](\d{1,3})', base)
    if not m:
        m = re.search(r'^(.*?)[ ._-]+(\d{1,2})x(\d{2,3})', base)
    if m:
        return clean_name(m.group(1)), int(m.group(2)), int(m.group(3))
    sem_grupo = re.sub(r'^\[[^\]]*\]\s*', '', base) if '[' in base else clean_name(base)
    a = re.search(r'^(.*?)\s-\s(\d{1,3})(?:\s|\[|v\d|$)', sem_grupo)
    if a:
        return clean_name(a.group(1)), None, int(a.group(2))
    return None


def parse_only_number(base):
    """Só o número do episódio ('01', 'Ep 7'), sem nome de série nenhum."""
    m = ONLY_NUMBER_RE.match(clean_name(base))
    return int(m.group(1)) if m else None


def show_from_folders(path, root):
    """Nome da série e temporada olhando as pastas acima do arquivo.

    'Naruto/01.mkv'            -> ('Naruto', 1)
    'One Piece/Season 2/05.mkv'-> ('One Piece', 2)
    """
    rel = os.path.relpath(os.path.dirname(path), root)
    if rel in ('.', os.curdir, ''):
        return None, None          # solto na raiz: a pasta vigiada não é nome de série
    partes = [p for p in rel.split(os.sep) if p not in ('.', '')]
    season = season_from_dir(partes[-1])
    if season is not None:
        if len(partes) < 2:
            return None, season    # 'Season 2' solto na raiz, sem nome de série
        return tidy_show(clean_name(partes[-2])), season
    return tidy_show(clean_name(partes[-1])), 1


# ---------------------------------------------------------------- varredura
def find_videos(root, max_depth=MAX_DEPTH):
    """Todos os vídeos de dentro da pasta, entrando nas subpastas."""
    achados = []
    pilha = [(root, 0)]
    while pilha:
        pasta, nivel = pilha.pop()
        try:
            nomes = sorted(os.listdir(pasta), key=C.natural_key)
        except OSError:
            continue
        for nome in nomes:
            cheio = os.path.join(pasta, nome)
            if os.path.isdir(cheio):
                if nivel < max_depth and not nome.startswith('.'):
                    pilha.append((cheio, nivel + 1))
            elif C.is_video(nome) and not is_partial(nome) and 'sample' not in nome.lower():
                achados.append(cheio)
    return sorted(achados, key=C.natural_key)


def existing_show_folder(series_root, show):
    """Reaproveita a pasta da série se já existir (ignora acento e maiúscula)."""
    try:
        for d in os.listdir(series_root):
            if norm(d) == norm(show) and os.path.isdir(os.path.join(series_root, d)):
                return d
    except OSError:
        pass
    return show


def episode_dest(series_root, show, season, ep, ext):
    show = existing_show_folder(series_root, show)
    return os.path.join(series_root, show, 'Season %02d' % season,
                        '%s S%02dE%02d%s' % (show, season, ep, ext))


def movie_dest(filmes_root, base, ext):
    y = re.search(r'^(.*?)[ ._(\[-]+((?:19|20)\d{2})(?:[ ._)\]-]|$)', base)
    titulo = clean_name(y.group(1)) if y else clean_name(C.JUNK_RE.sub('', base))
    titulo = tidy_show(titulo)
    if not titulo:
        return None
    nome = '%s (%s)%s' % (titulo, y.group(2), ext) if y else titulo + ext
    return os.path.join(filmes_root, nome)


# ---------------------------------------------------------------- o algoritmo
def plan_folder(root, series_root, filmes_root):
    """Lista de (origem, destino) para tudo que está dentro de `root`.

    Ordem de confiança: nome do arquivo (S01E02 / 1x02 / "Nome - 02") > nome das
    pastas acima > decisão por maioria da pasta > filme pelo ano.
    """
    videos = find_videos(root)
    if not videos:
        return []

    # Passada 1 — o que o próprio nome do arquivo entrega, e qual série manda em cada pasta
    pelo_nome = {}
    dono_da_pasta = {}   # pasta -> [show, temporada, quantos confirmaram]
    for v in videos:
        base = os.path.splitext(os.path.basename(v))[0]
        info = parse_filename(base)
        pelo_nome[v] = info
        if info and info[0]:
            show, season, _ep = info
            if season is None:
                season = show_from_folders(v, root)[1] or 1
            pasta = os.path.dirname(v)
            atual = dono_da_pasta.get(pasta)
            if atual is None:
                dono_da_pasta[pasta] = [show, season, 1]
            elif norm(atual[0]) == norm(show):
                atual[2] += 1

    # Passada 2 — decide cada vídeo; o que não der, fica para a passada 3
    episodios, indecisos, pastas_com_episodio = [], [], {}
    for v in videos:
        base, ext = os.path.splitext(os.path.basename(v))
        pasta = os.path.dirname(v)
        info = pelo_nome[v]
        show = season = ep = None

        if info and info[0]:                                  # 1 e 2: o arquivo diz tudo
            show, season, ep = info
            if season is None:
                season = show_from_folders(v, root)[1] or 1
        else:
            numero = info[2] if info else parse_only_number(base)
            if numero is not None:
                dono = dono_da_pasta.get(pasta)
                if dono and dono[2] >= 2:                     # 4: a maioria da pasta manda
                    show, season = dono[0], dono[1]
                else:                                         # 3: o nome vem da pasta
                    show, season = show_from_folders(v, root)
                    season = season or 1
                ep = numero

        show = tidy_show(show) if show else None
        if show and ep is not None and series_root:
            episodios.append((v, episode_dest(series_root, show, season or 1, ep, ext)))
            pastas_com_episodio[pasta] = pastas_com_episodio.get(pasta, 0) + 1
        else:
            indecisos.append((v, base, ext, pasta))

    # Passada 3 — sobrou: numa pasta que já virou série é extra (deixa quieto); senão, filme
    plans = list(episodios)
    for v, base, ext, pasta in indecisos:
        if pastas_com_episodio.get(pasta):
            continue
        if filmes_root:
            dst = movie_dest(filmes_root, base, ext)
            if dst:
                plans.append((v, dst))
    return [(s, d) for s, d in plans if not os.path.exists(d)]


# ---------------------------------------------------------------- mover
def sidecars(video):
    """Legendas com o mesmo nome do vídeo, inclusive com idioma ('.pt-BR.srt')."""
    pasta = os.path.dirname(video)
    base = os.path.splitext(os.path.basename(video))[0]
    fora = []
    try:
        for nome in os.listdir(pasta):
            raiz, ext = os.path.splitext(nome)
            if ext.lower() not in SUB_EXT:
                continue
            if raiz == base or raiz.startswith(base + '.'):
                fora.append((os.path.join(pasta, nome), raiz[len(base):] + ext))
    except OSError:
        pass
    return fora


def _log_moves(moves):
    """Grava o que o 'Desfazer organizacao.bat' lê.

    De propósito **sobrescreve**: o .bat devolve tudo que estiver no arquivo, então se
    fosse acumulativo um "desfazer" levaria de volta organizações antigas que já estão
    assentadas. Aqui o arquivo guarda só a última organização; o histórico completo fica
    no organizacao-historico.csv, que ninguém desfaz automaticamente.
    """
    try:
        destino = log_dir()
        os.makedirs(destino, exist_ok=True)
        alvo = os.path.join(destino, LOG_NOME)
        with open(alvo, 'w', newline='', encoding='utf-8-sig') as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            w.writerow(['De', 'Para'])
            for de, para in moves:
                w.writerow([de, para])
    except Exception as exc:
        C.log('não consegui gravar o log de organização: %s' % exc, xbmc.LOGWARNING)
    try:
        hist = os.path.join(log_dir(), LOG_HIST)
        novo = not os.path.exists(hist)
        with open(hist, 'a', newline='', encoding='utf-8-sig') as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            if novo:
                w.writerow(['Quando', 'De', 'Para'])
            agora = time.strftime('%Y-%m-%d %H:%M:%S')
            for de, para in moves:
                w.writerow([agora, de, para])
    except Exception as exc:
        C.log('histórico de organização: %s' % exc, xbmc.LOGWARNING)


def apply_moves(plans):
    """Move os vídeos (e as legendas). Devolve (quantos, [(de, para)])."""
    feitos = []
    for src, dst in plans:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            feitos.append((src, dst))
            novo_base = os.path.splitext(dst)[0]
            for sub_src, sufixo in sidecars(src):
                sub_dst = novo_base + sufixo
                if not os.path.exists(sub_dst):
                    try:
                        shutil.move(sub_src, sub_dst)
                        feitos.append((sub_src, sub_dst))
                    except Exception as exc:
                        C.log('legenda não movida (%s): %s' % (sub_src, exc), xbmc.LOGWARNING)
        except Exception as exc:
            C.log('não movi %s: %s' % (src, exc), xbmc.LOGWARNING)
    if feitos:
        _log_moves(feitos)
        remap_state(feitos)
    return len([1 for _s, d in feitos if C.is_video(d)]), feitos


def remap_state(moves):
    """O state.json é indexado por caminho: sem isso o 'Continuar assistindo' esvazia."""
    if not moves:
        return
    por_arquivo = {de: para for de, para in moves if C.is_video(para)}
    if not por_arquivo:
        return
    por_pasta = {}
    for de, para in por_arquivo.items():
        por_pasta[C.split_path(de)[0]] = C.split_path(para)[0]
    try:
        st = C.load_state()
        st['history'] = {por_arquivo.get(k, k): v for k, v in st.get('history', {}).items()}
        for chave in ('intros', 'credits'):
            if st.get(chave):
                st[chave] = {por_pasta.get(k, k): v for k, v in st[chave].items()}
        C.save_state(st)
    except Exception as exc:
        C.log('remap do state: %s' % exc, xbmc.LOGWARNING)


def plan_tidy(series_root):
    """Arruma o que já está dentro da pasta de Séries.

    Episódio solto na raiz da série entra na temporada certa; nome fora do padrão vira
    'Série SxxEyy'. O nome da série é o da própria pasta — aqui não se adivinha nada.
    """
    plans = []
    try:
        shows = sorted(os.listdir(series_root), key=C.natural_key)
    except OSError:
        return plans
    for show in shows:
        show_dir = os.path.join(series_root, show)
        if not os.path.isdir(show_dir):
            continue
        for v in find_videos(show_dir, max_depth=2):
            base, ext = os.path.splitext(os.path.basename(v))
            partes = os.path.relpath(v, show_dir).split(os.sep)
            season = season_from_dir(partes[0]) if len(partes) >= 2 else None
            info = parse_filename(base)
            if info:
                ep = info[2]
                season = info[1] or season or 1
            else:
                ep = parse_only_number(base)
                season = season or 1
            if ep is None:
                continue
            dst = os.path.join(show_dir, 'Season %02d' % season,
                               '%s S%02dE%02d%s' % (show, season, ep, ext))
            if os.path.normcase(os.path.abspath(dst)) != os.path.normcase(os.path.abspath(v)) \
                    and not os.path.exists(dst):
                plans.append((v, dst))
    return plans


def watched_snapshot():
    """Guarda assistido/retomada ANTES de mover: o Kodi marca isso por caminho, então
    mover um arquivo zera o 12/12 da série se ninguém devolver depois."""
    from resources.lib import jk_meta as M
    res = M.rpc('VideoLibrary.GetEpisodes',
                properties=['playcount', 'lastplayed', 'resume', 'file'])
    guarda = {}
    for d in res.get('result', {}).get('episodes', []) or []:
        arq = d.get('file')
        if arq:
            guarda[arq.lower()] = {'playcount': d.get('playcount', 0),
                                   'lastplayed': d.get('lastplayed', ''),
                                   'resume': d.get('resume') or {}}
    return guarda


def restore_watched(guarda, moves):
    """Devolve assistido/retomada depois do scan, casando pelo caminho novo."""
    from resources.lib import jk_meta as M
    novo_de = {de.lower(): para.lower() for de, para in moves if C.is_video(para)}
    res = M.rpc('VideoLibrary.GetEpisodes', properties=['file'])
    id_de = {}
    for d in res.get('result', {}).get('episodes', []) or []:
        if d.get('file'):
            id_de[d['file'].lower()] = d['episodeid']
    devolvidos = 0
    for antigo, dados in guarda.items():
        novo = novo_de.get(antigo)
        eid = id_de.get(novo) if novo else None
        if not eid:
            continue
        p = {'episodeid': eid, 'playcount': int(dados.get('playcount') or 0)}
        if dados.get('lastplayed'):
            p['lastplayed'] = dados['lastplayed']
        r = dados.get('resume') or {}
        if r.get('position'):
            p['resume'] = {'position': r['position'], 'total': r.get('total', 0)}
        M.rpc('VideoLibrary.SetEpisodeDetails', **p)
        devolvidos += 1
    return devolvidos


def tidy_path(path):
    return (path or '').rstrip('/\\')


def roots():
    """(Séries, Filmes): o que foi escolhido no app manda; senão, o rótulo da fonte."""
    from resources.lib import jk_meta as M
    saved = C.load_state().get('folders', {})
    series, filmes = saved.get('series'), saved.get('filmes')
    for label, path in M.video_sources():
        low = norm(label)
        if 'serie' in low and not series:
            series = path
        elif 'filme' in low and not filmes:
            filmes = path
    return tidy_path(series), tidy_path(filmes)


def watch_root():
    """A pasta que o organizador automático fica de olho."""
    saved = C.load_state().get('folders', {})
    return tidy_path(saved.get('downloads') or os.path.join(os.path.expanduser('~'), 'Downloads'))


def folder_signature(root, max_depth=MAX_DEPTH, max_itens=3000):
    """Retrato barato da pasta (quantos, tamanho, mais recente).

    É o que roda a cada poucos segundos: enquanto o retrato não mudar, não há nada novo e
    o organizador nem olha o conteúdo. Também serve para saber se um download terminou —
    enquanto o tamanho cresce, o retrato muda e nada é movido.
    """
    conta = tamanho = 0
    recente = 0.0
    pilha = [(root, 0)]
    try:
        while pilha and conta < max_itens:
            pasta, nivel = pilha.pop()
            with os.scandir(pasta) as it:
                for e in it:
                    if e.name.startswith('.'):
                        continue
                    try:
                        if e.is_dir():
                            if nivel < max_depth:
                                pilha.append((e.path, nivel + 1))
                            continue
                        st = e.stat()
                    except OSError:
                        continue
                    conta += 1
                    tamanho += st.st_size
                    recente = max(recente, st.st_mtime)
    except OSError:
        return None
    return conta, tamanho, int(recente)


def resumo(plans, series_root, filmes_root):
    """Agrupa por série/temporada para a tela de confirmação."""
    grupos = {}
    for _src, dst in plans:
        raiz = series_root if series_root and dst.startswith(series_root.rstrip('/\\')) else filmes_root
        partes = os.path.relpath(dst, raiz).split(os.sep)
        if len(partes) >= 3:
            chave = '%s  ›  %s' % (partes[0], re.sub(r'^Season\s*0?', 'Temporada ', partes[1]))
        elif len(partes) == 2:
            chave = partes[0]
        else:
            chave = 'Filmes'
        grupos[chave] = grupos.get(chave, 0) + 1
    return ['[B]%s[/B]:  %d vídeo(s)' % (k, v) for k, v in sorted(grupos.items())]
