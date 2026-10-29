# -*- coding: utf-8 -*-
"""Organizador de pastas: acha os vídeos, descobre série/temporada/episódio e move.

Usado pelo botão "Organizar Downloads" (plugin.py) e pelo organizador automático
do serviço (service.py), por isso mora aqui e não dentro do plugin.
"""
import csv
import errno
import json
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

# Onde vai o que ninguém conseguiu identificar, ao lado de Séries e Filmes
UNKNOWN_DIR = '_Nao_Identificado'

# transfer_mode: 0 hardlink, 1 copiar, 2 mover
MODOS = ('link', 'copia', 'move')

# O que já foi organizado, para não refazer. Ver ledger_tem().
LEDGER_FILE = os.path.join(C.PROFILE, 'organizados.json')

# Pares de volume onde o hardlink já falhou; lembrar evita 300 tentativas em 300 arquivos
_LINK_PROIBIDO = set()


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


def movie_title(base):
    """(título, ano) de um nome de arquivo de filme; (None, None) se não der."""
    y = re.search(r'^(.*?)[ ._(\[-]+((?:19|20)\d{2})(?:[ ._)\]-]|$)', base)
    titulo = clean_name(y.group(1)) if y else clean_name(C.JUNK_RE.sub('', base))
    titulo = tidy_show(titulo)
    return (titulo or None), (y.group(2) if y else None)


def movie_dest(filmes_root, base, ext, titulo=None, ano=None, pasta_propria=None):
    """Destino de um filme.

    `titulo`/`ano` vindos da pesquisa valem mais do que o nome do arquivo. Com
    `pasta_propria` o filme ganha a sua própria pasta — é o que permite guardar
    poster.jpg, fanart.jpg e movie.nfo ao lado dele.
    """
    if titulo is None:
        titulo, ano_do_arquivo = movie_title(base)
        ano = ano or ano_do_arquivo
    if not titulo:
        return None
    if pasta_propria is None:
        pasta_propria = C.setting_bool('movie_folders', True)
    nome = '%s (%s)' % (titulo, ano) if ano else titulo
    if not pasta_propria:
        return os.path.join(filmes_root, nome + ext)
    pasta = existing_show_folder(filmes_root, nome)   # reaproveita a pasta se já existir
    return os.path.join(filmes_root, pasta, pasta + ext)


def unknown_dest(origem):
    """Não identificado: pasta separada, uma subpasta por pasta de origem."""
    pasta = os.path.basename(tidy_path(os.path.dirname(origem))) or 'solto'
    return os.path.join(log_dir(), UNKNOWN_DIR, pasta, os.path.basename(origem))


# ---------------------------------------------------------------- livro-razão
def ledger_chave(src):
    """Identidade do arquivo de origem: nome normalizado + tamanho.

    Não é o caminho: o cliente de torrent move o arquivo de 'incompletos' para
    'completos' e o caminho muda sem o arquivo mudar. O tamanho entra para que um
    arquivo substituído por outro (mesmo nome, release diferente) volte a ser visto.
    """
    try:
        tam = os.path.getsize(src)
    except OSError:
        tam = 0
    return '%s|%d' % (norm(os.path.basename(src)), tam)


def ledger_load():
    """Lê o organizados.json, com a mesma proteção do state.json."""
    dados = {}
    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8-sig') as fh:
            dados = json.load(fh)
        if not isinstance(dados, dict):
            raise ValueError('organizados.json não é um objeto')
    except FileNotFoundError:
        dados = {}
    except Exception as exc:
        dados = {'ilegivel': True}
        try:
            ruim = LEDGER_FILE + '.ruim'
            if os.path.exists(LEDGER_FILE) and not os.path.exists(ruim):
                shutil.copy2(LEDGER_FILE, ruim)
            C.log('organizados.json ilegível (%s); copiei para %s' % (exc, ruim),
                  xbmc.LOGERROR)
        except Exception:
            pass
    dados.setdefault('feitos', {})
    return dados


def ledger_save(dados):
    if dados.pop('ilegivel', False):
        # não sabemos o que havia: gravar agora faria o Ark reorganizar tudo de novo
        C.log('não vou gravar por cima de um organizados.json ilegível', xbmc.LOGWARNING)
        return
    try:
        os.makedirs(C.PROFILE, exist_ok=True)
        tmp = LEDGER_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(dados, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, LEDGER_FILE)
    except Exception as exc:
        C.log('livro-razão: %s' % exc, xbmc.LOGWARNING)


def ledger_add(moves, modo):
    """Registra o que acabou de ser organizado."""
    if not moves:
        return
    dados = ledger_load()
    feitos = dados.setdefault('feitos', {})
    agora = int(time.time())
    for de, para in moves:
        if C.is_video(para):
            feitos[ledger_chave(de)] = {'src': de, 'dst': para,
                                        'modo': modo, 'quando': agora}
    ledger_save(dados)


def ledger_esquecer(chaves):
    """Tira do livro-razão (usado quando o usuário corrige um título)."""
    if not chaves:
        return
    dados = ledger_load()
    feitos = dados.get('feitos', {})
    for ch in chaves:
        feitos.pop(ch, None)
    ledger_save(dados)


def ledger_podar():
    """Remove só o que não existe mais na origem.

    Nunca poda por idade: o livro-razão é justamente o que impede o Ark de religar um
    episódio que o usuário apagou da biblioteca de propósito. Esquecer por tempo
    ressuscitaria esse caso.
    """
    dados = ledger_load()
    feitos = dados.get('feitos', {})
    mortos = [k for k, v in feitos.items() if not os.path.exists(v.get('src', ''))]
    if not mortos:
        return 0
    for k in mortos:
        feitos.pop(k, None)
    ledger_save(dados)
    return len(mortos)


def _aninhado(a, b):
    """True quando um dos caminhos está dentro do outro."""
    if not a or not b:
        return False
    a = os.path.normcase(os.path.abspath(tidy_path(a))) + os.sep
    b = os.path.normcase(os.path.abspath(tidy_path(b))) + os.sep
    return a.startswith(b) or b.startswith(a)


# ---------------------------------------------------------------- o algoritmo
# Quanto se confia em cada pista, do mais firme para o mais chutado. É a mesma ordem
# de sempre; aqui ela virou número para a tela de revisão poder mostrar e ordenar.
PESO_MOTIVO = {
    'nome do arquivo': 1.0,
    'nome do arquivo (anime)': 0.9,
    'maioria da pasta': 0.8,
    'ano no nome': 0.7,
    'nome da pasta': 0.6,
    'pesquisa': 0.85,
    'extra da pasta': 1.0,
    'sem pista': 0.0,
}


class Item:
    """Um vídeo e para onde ele vai."""

    __slots__ = ('origem', 'destino', 'tipo', 'temporada', 'episodio', 'ext',
                 'legendas', 'motivo', 'falhou')

    def __init__(self, origem, tipo, ext, temporada=None, episodio=None, motivo=''):
        self.origem = origem
        self.destino = None      # None = fica onde está
        self.tipo = tipo         # 'episodio' | 'filme' | 'extra' | 'desconhecido'
        self.ext = ext
        self.temporada = temporada
        self.episodio = episodio
        self.motivo = motivo
        self.legendas = []
        self.falhou = ''

    @property
    def nome(self):
        return os.path.basename(self.origem)


class Grupo:
    """Uma série ou franquia: a unidade que o usuário revisa e aprova.

    O organizador antigo trabalhava em pares (origem, destino) soltos, então uma pasta
    de downloads com 20 animes virava uma lista plana de centenas de linhas e não havia
    como perguntar nada ao usuário. O grupo existe para dar nome e dono a cada pedaço.
    """

    __slots__ = ('chave', 'titulo_bruto', 'titulo', 'ano', 'tipo', 'pastas',
                 'itens', 'confianca', 'fonte', 'meta', 'pular')

    def __init__(self, chave, titulo_bruto):
        self.chave = chave
        self.titulo_bruto = titulo_bruto
        self.titulo = titulo_bruto
        self.ano = None
        self.tipo = 'desconhecido'   # 'serie' | 'filme' | 'misto' | 'desconhecido'
        self.pastas = set()
        self.itens = []
        self.confianca = 0.0
        self.fonte = 'arquivo'       # 'arquivo' | 'pasta' | 'anilist' | 'tmdb' | 'llm' | 'manual'
        self.meta = {}
        self.pular = False

    @property
    def desconhecido(self):
        return self.chave.startswith('\x00')

    def contagem(self):
        """(quantos episódios, quantos filmes)."""
        eps = len([i for i in self.itens if i.tipo == 'episodio'])
        filmes = len([i for i in self.itens if i.tipo == 'filme'])
        return eps, filmes

    def a_organizar(self):
        return [i for i in self.itens if i.destino]

    def rotulo(self):
        eps, filmes = self.contagem()
        partes = []
        if eps:
            partes.append('%d ep' % eps)
        if filmes:
            partes.append('%d filme%s' % (filmes, '' if filmes == 1 else 's'))
        sobra = len(self.itens) - eps - filmes
        if sobra:
            partes.append('%d sem destino' % sobra)
        return ' · '.join(partes) or 'vazio'


def _grupo_de(grupos, titulo, rotulo=None):
    """Acha ou cria o grupo de um título. Sem título, o grupo é dos não identificados."""
    chave = norm(titulo) if titulo else '\x00' + norm(rotulo or '?')
    g = grupos.get(chave)
    if g is None:
        g = Grupo(chave, titulo or (rotulo or '?'))
        grupos[chave] = g
    return g


def _grupo_da_pasta(grupos, pasta):
    for g in grupos.values():
        if pasta in g.pastas:
            return g
    return None


def _tipo_e_confianca(g):
    eps, filmes = g.contagem()
    if eps and filmes:
        g.tipo = 'misto'
    elif eps:
        g.tipo = 'serie'
    elif filmes:
        g.tipo = 'filme'
    else:
        g.tipo = 'desconhecido'
    # vale a pista mais fraca que sustentou o grupo: um episódio chutado derruba o resto
    pesos = [PESO_MOTIVO.get(i.motivo, 0.5) for i in g.itens if i.tipo != 'extra']
    g.confianca = round(min(pesos), 2) if pesos else 0.0


def _aplicar_pesquisa(g, resolver):
    """Deixa a pesquisa online melhorar título, ano e tipo do grupo.

    `resolver(grupo)` devolve um dict com titulo/ano/tipo/fonte/confianca, ou None.
    Vive aqui, e não dentro do laço dos vídeos, para a consulta sair uma vez por série:
    20 animes são 20 consultas, não 400.
    """
    try:
        achado = resolver(g)
    except Exception as exc:
        C.log('pesquisa do grupo "%s": %s' % (g.titulo_bruto, exc), xbmc.LOGWARNING)
        return
    if not achado or not achado.get('titulo'):
        return
    g.titulo = achado['titulo']
    g.ano = achado.get('ano') or g.ano
    g.fonte = achado.get('fonte') or 'anilist'
    g.meta = achado
    if achado.get('confianca') is not None:
        g.confianca = max(g.confianca, float(achado['confianca']))
    if achado.get('tipo') == 'filme':
        # a pesquisa reconheceu um filme onde o nome do arquivo não dizia nada
        for it in g.itens:
            if it.tipo == 'desconhecido':
                it.tipo, it.motivo = 'filme', 'pesquisa'
        _tipo_e_confianca(g)


def _destinos(g, series_root, filmes_root, vistos, feitos=None):
    """Calcula o destino de cada item agora que o grupo tem título definitivo."""
    nome = tidy_show(g.titulo) or g.titulo_bruto
    bucket = C.setting_bool('unknown_bucket', True)
    for it in g.itens:
        it.destino = None
        if g.pular:
            continue
        if feitos is not None and ledger_chave(it.origem) in feitos:
            # já organizado antes. É o livro-razão, e não o disco, que manda aqui: no
            # modo hardlink o vídeo nunca sai do Downloads, então olhar só se o destino
            # existe faria o Ark religar o que o usuário apagou da biblioteca.
            continue
        if it.tipo == 'episodio' and series_root:
            it.destino = episode_dest(series_root, nome, it.temporada or 1,
                                      it.episodio, it.ext)
        elif it.tipo == 'filme' and filmes_root:
            it.destino = movie_dest(filmes_root, os.path.splitext(it.nome)[0], it.ext,
                                    titulo=nome, ano=g.ano)
        elif it.tipo == 'desconhecido' and bucket:
            it.destino = unknown_dest(it.origem)
        # 'extra' (NCOP, PV, "extras.mkv") nunca tem destino: fica no Downloads de propósito

        if not it.destino:
            continue
        chave = os.path.normcase(os.path.abspath(it.destino))
        if chave in vistos or os.path.exists(it.destino):
            # já existe no disco, ou dois arquivos brigando pelo mesmo destino.
            # Segunda rede de proteção, depois do livro-razão: nunca sobrescrever
            # um vídeo (ou uma arte) que já estava lá.
            it.destino = None
            continue
        vistos.add(chave)
        it.legendas = sidecars(it.origem)


def plan_groups(root, series_root, filmes_root, resolver=None):
    """Agrupa por série o que está dentro de `root` e calcula os destinos.

    Ordem de confiança: nome do arquivo (S01E02 / 1x02 / "Nome - 02") > maioria da
    pasta > nome das pastas acima > filme pelo ano. `resolver` é opcional e só serve
    para refinar o título com pesquisa online (jk_lookup).
    """
    for raiz in (series_root, filmes_root):
        if _aninhado(root, raiz):
            C.log('a pasta de downloads está dentro da biblioteca (%s): não organizo, '
                  'o Kodi indexaria tudo em dobro' % raiz, xbmc.LOGWARNING)
            return []

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

    # Passada 2 — decide cada vídeo e já o pendura no grupo da série
    grupos = {}
    indecisos = []
    pastas_com_episodio = {}
    for v in videos:
        base, ext = os.path.splitext(os.path.basename(v))
        pasta = os.path.dirname(v)
        info = pelo_nome[v]
        show = season = ep = None
        motivo = ''

        if info and info[0]:                                  # 1 e 2: o arquivo diz tudo
            show, season, ep = info
            motivo = 'nome do arquivo'
            if season is None:
                season = show_from_folders(v, root)[1] or 1
                motivo = 'nome do arquivo (anime)'
        else:
            numero = info[2] if info else parse_only_number(base)
            if numero is not None:
                dono = dono_da_pasta.get(pasta)
                if dono and dono[2] >= 2:                     # 4: a maioria da pasta manda
                    show, season = dono[0], dono[1]
                    motivo = 'maioria da pasta'
                else:                                         # 3: o nome vem da pasta
                    show, season = show_from_folders(v, root)
                    season = season or 1
                    motivo = 'nome da pasta'
                ep = numero

        show = tidy_show(show) if show else None
        if show and ep is not None:
            g = _grupo_de(grupos, show)
            g.pastas.add(pasta)
            g.itens.append(Item(v, 'episodio', ext, season or 1, ep, motivo))
            pastas_com_episodio[pasta] = pastas_com_episodio.get(pasta, 0) + 1
        else:
            indecisos.append((v, base, ext, pasta))

    # Passada 3 — o que sobrou
    for v, base, ext, pasta in indecisos:
        titulo, ano = movie_title(base)
        if pastas_com_episodio.get(pasta) and not ano:
            # numa pasta que já virou série, e sem ano no nome, é extra (NCOP, PV,
            # "extras.mkv"): fica onde está. Com ano, é o filme da franquia e segue adiante.
            dono = _grupo_da_pasta(grupos, pasta)
            if dono is not None:
                dono.itens.append(Item(v, 'extra', ext, motivo='extra da pasta'))
                continue
        if titulo and ano:
            g = _grupo_de(grupos, titulo)
            g.pastas.add(pasta)
            g.ano = g.ano or ano
            g.itens.append(Item(v, 'filme', ext, motivo='ano no nome'))
        else:
            # Sem ano não se chuta filme. O organizador antigo chutava: qualquer sobra
            # com nome não-vazio virava "Filmes\coisa qualquer.mkv". Aqui ou a pesquisa
            # resolve, ou o arquivo vai para a pasta dos não identificados com o nome
            # original intacto — não se renomeia o que não se entendeu.
            g = _grupo_de(grupos, None, titulo or os.path.basename(tidy_path(pasta)))
            g.pastas.add(pasta)
            g.itens.append(Item(v, 'desconhecido', ext, motivo='sem pista'))

    ordenados = sorted(grupos.values(), key=lambda g: C.natural_key(g.titulo_bruto))
    vistos = set()
    feitos = ledger_load().get('feitos', {})
    for g in ordenados:
        _tipo_e_confianca(g)
        if resolver is not None:
            _aplicar_pesquisa(g, resolver)
        _destinos(g, series_root, filmes_root, vistos, feitos)
    return [g for g in ordenados if g.itens]


def aplicar_achado(grupo, achado, series_root=None, filmes_root=None):
    """Encaixa no grupo o que a pesquisa devolveu e refaz os destinos.

    É o que o plugin e a tela usam quando resolvem um grupo por fora do plan_groups
    (para poder mostrar barra de progresso e deixar o usuário cancelar).
    """
    _aplicar_pesquisa(grupo, lambda _g: achado)
    if series_root or filmes_root:
        _tipo_e_confianca(grupo)
        _destinos(grupo, series_root, filmes_root, set())
    return grupo


def recalcular(grupo, series_root, filmes_root):
    """Refaz os destinos de um grupo depois de o usuário corrigir o título.

    Ignora o livro-razão de propósito: corrigir o título é justamente dizer que o
    destino anterior estava errado.
    """
    ledger_esquecer([ledger_chave(i.origem) for i in grupo.itens])
    _tipo_e_confianca(grupo)
    _destinos(grupo, series_root, filmes_root, set())
    return grupo


def plan_folder(root, series_root, filmes_root):
    """Lista de (origem, destino), o formato que o serviço e o botão antigo esperam."""
    return [(it.origem, it.destino)
            for g in plan_groups(root, series_root, filmes_root)
            for it in g.a_organizar()]


def planos(grupos):
    """(origem, destino) de todos os grupos que não foram pulados."""
    return [(it.origem, it.destino)
            for g in grupos if not g.pular
            for it in g.a_organizar()]


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


def _log_moves(moves, modo='movido'):
    """Grava o que o 'Desfazer organizacao.bat' lê.

    De propósito **sobrescreve**: o .bat devolve tudo que estiver no arquivo, então se
    fosse acumulativo um "desfazer" levaria de volta organizações antigas que já estão
    assentadas. Aqui o arquivo guarda só a última organização; o histórico completo fica
    no organizacao-historico.csv, que ninguém desfaz automaticamente.

    A coluna 'Modo' diz ao .bat *como* desfazer: 'movido' devolve com Move-Item, mas
    'link' e 'copia' só podem apagar o arquivo novo — o original nunca saiu do lugar, e
    um Move-Item em cima dele apagaria o download para pôr o link no lugar.
    O histórico fica em 3 colunas como sempre: ninguém o lê por máquina, e mudar o
    cabeçalho de um arquivo que só cresce deixaria as linhas antigas tortas.
    """
    try:
        destino = log_dir()
        os.makedirs(destino, exist_ok=True)
        alvo = os.path.join(destino, LOG_NOME)
        with open(alvo, 'w', newline='', encoding='utf-8-sig') as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            w.writerow(['De', 'Para', 'Modo'])
            for de, para in moves:
                w.writerow([de, para, modo])
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


class VolumeDiferente(OSError):
    """Hardlink pedido entre discos diferentes."""


def modo_atual():
    """O ajuste transfer_mode: 0 hardlink (padrão), 1 copiar, 2 mover."""
    return MODOS[min(max(C.setting_int('transfer_mode', 0), 0), 2)]


def transferir(src, dst, modo):
    """Põe `src` em `dst` do jeito pedido; devolve o modo usado para o log.

    'link' é o padrão: cria um hardlink, então o arquivo continua no Downloads (o
    torrent segue semeando) e a biblioteca não gasta um byte a mais — os dois nomes
    apontam para os mesmos bytes. No Windows isso exige NTFS e o **mesmo volume**, e
    não precisa de administrador (diferente de link simbólico).

    Entre discos diferentes o os.link dá EXDEV, e aí NÃO caímos para cópia por conta
    própria: duplicar centenas de GB sem avisar seria pior do que falhar. Quem chama
    decide — a tela de revisão oferece copiar só aquele grupo.
    """
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        return None                       # já está lá: não é erro, é nada a fazer
    if modo == 'link':
        par = _par_de_volumes(src, dst)
        if par not in _LINK_PROIBIDO:
            try:
                os.link(src, dst)
                return 'link'
            except OSError as exc:
                # 17 = discos diferentes; 1 = o destino não sabe fazer hardlink (FAT32, rede)
                if exc.errno == errno.EXDEV or getattr(exc, 'winerror', None) in (1, 17):
                    _LINK_PROIBIDO.add(par)
                else:
                    raise
        raise VolumeDiferente('não dá para criar atalho de %s para %s' % par)
    if modo == 'copia':
        _copiar(src, dst)
        return 'copia'
    shutil.move(src, dst)
    return 'movido'


def _par_de_volumes(src, dst):
    return (os.path.splitdrive(os.path.abspath(src))[0].lower() or '?',
            os.path.splitdrive(os.path.abspath(dst))[0].lower() or '?')


def _copiar(src, dst):
    """Copia por um arquivo temporário.

    Sem isso, um Kodi fechado no meio da cópia deixa um vídeo pela metade na
    biblioteca — e o scraper o indexa como se estivesse inteiro.
    """
    try:
        livre = shutil.disk_usage(os.path.dirname(dst)).free
    except OSError:
        livre = None
    if livre is not None and livre < os.path.getsize(src) * 1.05:
        raise OSError('falta espaço no destino para %s' % os.path.basename(src))
    tmp = dst + '.ark-parcial'
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def apply_moves(plans, modo=None, progresso=None):
    """Organiza os vídeos (e as legendas). Devolve (quantos, [(de, para)]).

    `modo` None lê o ajuste do usuário. 'move' é o único que muda o caminho de verdade,
    e só nele o state.json precisa ser remapeado: com hardlink ou cópia o caminho antigo
    continua existindo e continua tocando, então mexer no histórico só o estragaria.

    `progresso(i, total, nome)` é opcional e existe para o modo cópia: hardlink é
    instantâneo, mas copiar 200 GB sem nada na tela parece travamento.
    """
    modo = modo or modo_atual()
    # legenda nunca é atalho: é um arquivo pequeno, e quem ajusta a sincronia de um
    # .srt linkado estaria editando o arquivo do torrent e podia derrubar o seed
    modo_legenda = 'copia' if modo == 'link' else modo
    feitos = []
    usado = {'link': 'link', 'copia': 'copia'}.get(modo, 'movido')
    total = len(plans)
    for i, (src, dst) in enumerate(plans):
        if progresso and progresso(i, total, os.path.basename(dst)) is False:
            break                         # quem chama pediu para parar
        try:
            if transferir(src, dst, modo) is None:
                continue
            feitos.append((src, dst))
            novo_base = os.path.splitext(dst)[0]
            for sub_src, sufixo in sidecars(src):
                sub_dst = novo_base + sufixo
                try:
                    if transferir(sub_src, sub_dst, modo_legenda) is not None:
                        feitos.append((sub_src, sub_dst))
                except Exception as exc:
                    C.log('legenda de fora (%s): %s' % (sub_src, exc), xbmc.LOGWARNING)
        except VolumeDiferente as exc:
            C.log('%s' % exc, xbmc.LOGWARNING)
        except Exception as exc:
            C.log('não organizei %s: %s' % (src, exc), xbmc.LOGWARNING)
    if feitos:
        _log_moves(feitos, usado)
        remap_state(feitos, modo)
        ledger_add(feitos, usado)
    return len([1 for _s, d in feitos if C.is_video(d)]), feitos


def remap_state(moves, modo='move'):
    """O state.json é indexado por caminho: sem isso o 'Continuar assistindo' esvazia.

    Mover troca a chave, porque o caminho antigo deixou de existir. Hardlink e cópia
    **acrescentam**: o arquivo continua tocável no Downloads, e substituir a chave
    apagaria o progresso de quem assistia direto de lá.
    """
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
        if modo == 'move':
            st['history'] = {por_arquivo.get(k, k): v
                             for k, v in st.get('history', {}).items()}
            for chave in ('intros', 'credits'):
                if st.get(chave):
                    st[chave] = {por_pasta.get(k, k): v for k, v in st[chave].items()}
        else:
            hist = st.get('history', {})
            for de, para in por_arquivo.items():
                if de in hist and para not in hist:
                    hist[para] = dict(hist[de])
            st['history'] = hist
            for chave in ('intros', 'credits'):
                marcas = st.get(chave) or {}
                for de, para in por_pasta.items():
                    if de in marcas and para not in marcas:
                        marcas[para] = marcas[de]
                if marcas:
                    st[chave] = marcas
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


def folder_signature(root, max_depth=MAX_DEPTH, max_itens=20000):
    """Retrato barato da pasta (quantos, tamanho, mais recente).

    É o que roda a cada poucos segundos: enquanto o retrato não mudar, não há nada novo e
    o organizador nem olha o conteúdo. Também serve para saber se um download terminou —
    enquanto o tamanho cresce, o retrato muda e nada é movido.

    O teto de itens é alto de propósito: no modo hardlink a pasta de downloads nunca
    esvazia, e um teto baixo faria o retrato parar de reagir a arquivo novo — a pilha é
    LIFO sobre os.scandir, então *quais* itens entram no corte não é estável.
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
