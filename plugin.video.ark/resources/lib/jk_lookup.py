# -*- coding: utf-8 -*-
"""Descobre o título de verdade de uma série ou filme a partir do nome bagunçado.

Três fontes, nesta ordem:

1. **AniList** (graphql.anilist.co) — público, sem chave, e é a melhor base que existe
   para anime: tem romaji, inglês, sinônimos, o formato (TV/MOVIE/OVA) e a sinopse.
   O formato é o que separa o filme da franquia dos episódios dela.
2. **TMDB** — só se o usuário colar a chave dele nos ajustes. Cobre o que não é anime e
   dá a sinopse em pt-BR direto. O `tmdb_id` vale mais que o resto: é o mesmo id que o
   scraper do Kodi usa, então achá-lo aqui é entregar o trabalho pronto para ele.
3. **Modelo de linguagem** (jk_llm) — último recurso, para nome que nenhuma busca
   alcança. Devolve só um palpite de título, que volta para o AniList/TMDB confirmar.

Importa jk_organize para reusar norm()/clean_name(). Não há ciclo: jk_organize **nunca**
importa este módulo — recebe `resolver` por parâmetro em plan_groups().
"""
import difflib
import re

import xbmc

from resources.lib import jk_common as C
from resources.lib import jk_net as N
from resources.lib import jk_organize as O

ANILIST = 'https://graphql.anilist.co'
TMDB = 'https://api.themoviedb.org/3'
TMDB_IMG = 'https://image.tmdb.org/t/p/original'

# Acima disto a gente aceita calado; entre os dois aceita mas marca para revisão;
# abaixo do segundo não serve e o arquivo vai para os não identificados.
ACEITA = 0.80
REVISAR = 0.55

CONSULTA = '''
query ($q: String, $n: Int) {
  Page(perPage: $n) {
    media(search: $q, type: ANIME, sort: SEARCH_MATCH) {
      id format seasonYear episodes
      title { romaji english native }
      synonyms
      description(asHtml: false)
      coverImage { extraLarge }
      bannerImage
    }
  }
}
'''

# Sujeira de nome de release que só estraga a busca
SUJEIRA_RE = re.compile(
    r'\[[^\]]*\]|\([^)]*\)|\b(?:'
    r'1080p|720p|2160p|480p|4k|uhd|hdr|x26[45]|h\.?26[45]|hevc|av1|10?bits?|8bits?|'
    r'web-?dl|web-?rip|webrip|bd-?rip|bluray|blu-?ray|br-?rip|dvdrip|hdtv|remux|'
    r'aac|ac3|eac3|dts|flac|opus|dual(?:[ ._-]?audio)?|multi|legendado|dublado|'
    r'raw|uncensored|censored|v\d|repack|proper|complete|batch'
    r')\b', re.I)

# Marcas de temporada/parte: atrapalham a busca pelo nome da obra
PARTE_RE = re.compile(
    r'\b(?:(?:2nd|3rd|\d+(?:st|nd|rd|th))\s+season|season\s*\d+|temporada\s*\d+|'
    r's\d{1,2}|part\s*\d+|parte\s*\d+|cour\s*\d+)\b', re.I)

# Palavras que dizem "isto é um filme" e não fazem parte do título indexado.
# Sem tirar isto o AniList não acha nada para "Gekijouban Kimetsu no Yaiba Mugen Train"
# — conferido contra a API de verdade.
FILME_RE = re.compile(
    r'\b(?:gekijouban|gekijou\s*ban|gekijo?uban|eiga|the\s+movie|movie|filme)\b', re.I)

TIPO_ANILIST = {
    'TV': 'serie', 'TV_SHORT': 'serie', 'ONA': 'serie',
    'MOVIE': 'filme',
    'OVA': 'extra', 'SPECIAL': 'extra', 'MUSIC': 'extra',
}


def limpar_para_busca(nome):
    """Tira grupo, CRC, resolução, codec e marca de temporada do nome."""
    texto = SUJEIRA_RE.sub(' ', nome or '')
    texto = re.sub(r'[._]+', ' ', texto)
    texto = re.sub(r'\b[0-9A-F]{8}\b', ' ', texto)      # CRC solto
    texto = re.sub(r'\s*-\s*\d{1,3}\s*$', '', texto)    # "Nome - 07" no fim
    return re.sub(r'\s{2,}', ' ', texto).strip(' -_.')


def consultas(grupo):
    """Variantes de busca, da mais específica para a mais crua, sem repetir.

    A ordem importa: `resolver` para na primeira que der nota boa. Por isso o termo mais
    completo vem antes, e as versões podadas (sem marca de temporada, sem "Gekijouban")
    depois — elas acham mais, mas acham mais coisa errada também.
    """
    brutos = [grupo.titulo, grupo.titulo_bruto]
    if grupo.itens:
        brutos.append(O.clean_name(grupo.itens[0].nome.rsplit('.', 1)[0]))
    saida = []
    for bruto in brutos:
        limpo = limpar_para_busca(bruto)
        variantes = (limpo,
                     PARTE_RE.sub(' ', limpo),
                     FILME_RE.sub(' ', limpo),
                     FILME_RE.sub(' ', PARTE_RE.sub(' ', limpo)))
        for termo in variantes:
            termo = re.sub(r'\s{2,}', ' ', termo or '').strip(' -_.')
            if len(termo) >= 3 and termo not in saida:
                saida.append(termo)
    return saida


# ---------------------------------------------------------------- AniList
def _sem_html(texto):
    texto = re.sub(r'<br\s*/?>', '\n', texto or '', flags=re.I)
    texto = re.sub(r'<[^>]+>', '', texto)
    return re.sub(r'\n{3,}', '\n\n', texto).strip()


def anilist_buscar(termo, limite=6):
    """Candidatos do AniList para um termo. [] quando não dá (offline, castigo...)."""
    guardado = C.cache_get('anilist', O.norm(termo), dias=30)
    if guardado is not None:
        return guardado
    try:
        res = N.post_json(ANILIST, {'query': CONSULTA,
                                    'variables': {'q': termo, 'n': limite}},
                          timeout=12)
    except N.SemRede as exc:
        C.log('AniList sem rede: %s' % exc, xbmc.LOGDEBUG)
        return []
    except (N.Recusado, N.Ocupado) as exc:
        C.log('AniList: %s' % exc, xbmc.LOGWARNING)
        return []
    saida = []
    for m in ((res.get('data') or {}).get('Page') or {}).get('media') or []:
        t = m.get('title') or {}
        titulos = [t.get('romaji'), t.get('english'), t.get('native')]
        titulos += m.get('synonyms') or []
        # nunca o nativo em japonês como nome de pasta: atrapalha o scraper e o Windows
        nome = t.get('english') or t.get('romaji') or t.get('native')
        if not nome:
            continue
        saida.append({
            'titulo': nome,
            'titulos': [x for x in titulos if x],
            'ano': str(m['seasonYear']) if m.get('seasonYear') else None,
            'tipo': TIPO_ANILIST.get(m.get('format'), 'serie'),
            'fonte': 'anilist',
            'ids': {'anilist': m.get('id')},
            'episodios': m.get('episodes'),
            'sinopse': _sem_html(m.get('description')),
            'poster': (m.get('coverImage') or {}).get('extraLarge'),
            'fanart': m.get('bannerImage'),
        })
    C.cache_put('anilist', O.norm(termo), saida)
    return saida


# ---------------------------------------------------------------- TMDB
def tmdb_buscar(termo, tipo=None, ano=None):
    """Candidatos do TMDB. Lista vazia se o usuário não configurou a chave."""
    chave = C.setting_string('tmdb_key', '')
    if not chave:
        return []
    cache_id = '%s|%s|%s' % (O.norm(termo), tipo or '', ano or '')
    guardado = C.cache_get('tmdb', cache_id, dias=30)
    if guardado is not None:
        return guardado

    alvos = ['tv', 'movie'] if tipo not in ('serie', 'filme') else \
            (['tv'] if tipo == 'serie' else ['movie'])
    saida = []
    for alvo in alvos:
        params = {'api_key': chave, 'query': termo, 'language': 'pt-BR',
                  'include_adult': 'false'}
        if ano:
            params['first_air_date_year' if alvo == 'tv' else 'year'] = ano
        try:
            res = N.get_json('%s/search/%s' % (TMDB, alvo), params=params, timeout=12)
        except N.SemRede:
            return []
        except (N.Recusado, N.Ocupado) as exc:
            C.log('TMDB (%s): %s' % (alvo, exc), xbmc.LOGWARNING)
            continue
        for m in (res.get('results') or [])[:6]:
            nome = m.get('name') or m.get('title')
            if not nome:
                continue
            data = m.get('first_air_date') or m.get('release_date') or ''
            saida.append({
                'titulo': nome,
                'titulos': [x for x in (nome, m.get('original_name'),
                                        m.get('original_title')) if x],
                'ano': data[:4] or None,
                'tipo': 'serie' if alvo == 'tv' else 'filme',
                'fonte': 'tmdb',
                'ids': {'tmdb': m.get('id')},
                'episodios': None,
                'sinopse': (m.get('overview') or '').strip(),
                'poster': TMDB_IMG + m['poster_path'] if m.get('poster_path') else None,
                'fanart': TMDB_IMG + m['backdrop_path'] if m.get('backdrop_path') else None,
            })
    C.cache_put('tmdb', cache_id, saida)
    return saida


# ---------------------------------------------------------------- pontuação
def pontuar(termo, candidato, dica_tipo=None, ano=None):
    """0.0 a 1.0. Compara com TODOS os títulos do candidato e usa o melhor."""
    alvo = O.norm(termo)
    if not alvo:
        return 0.0
    nota = 0.0
    for titulo in candidato.get('titulos') or [candidato.get('titulo')]:
        outro = O.norm(titulo or '')
        if not outro:
            continue
        parecido = difflib.SequenceMatcher(None, alvo, outro).ratio()
        if alvo == outro:
            parecido = 1.0
        elif alvo in outro or outro in alvo:
            parecido = max(parecido, 0.88)
        nota = max(nota, parecido)

    if ano and candidato.get('ano'):
        nota += 0.08 if str(ano) == str(candidato['ano']) else -0.10
    if dica_tipo in ('serie', 'filme') and candidato.get('tipo') in ('serie', 'filme'):
        nota += 0.06 if candidato['tipo'] == dica_tipo else -0.18
    return max(0.0, min(1.0, round(nota, 3)))


def melhor(termo, candidatos, dica_tipo=None, ano=None):
    """(candidato, nota) do melhor da lista, ou (None, 0.0)."""
    escolhido, melhor_nota = None, 0.0
    for c in candidatos or []:
        nota = pontuar(termo, c, dica_tipo, ano)
        if nota > melhor_nota:
            escolhido, melhor_nota = c, nota
    return escolhido, melhor_nota


# ---------------------------------------------------------------- o resolvedor
def _dica(grupo):
    return grupo.tipo if grupo.tipo in ('serie', 'filme') else None


def resolver(grupo, usar_llm=True):
    """O que plan_groups() chama. Devolve um dict de achado, ou None.

    Sai na primeira consulta que der nota boa. O cache é por grupo, então reabrir a
    tela de organizar não gasta uma única requisição.
    """
    if not C.setting_bool('lookup_online', True):
        return None

    cache_id = O.norm(grupo.titulo_bruto)
    guardado = C.cache_get('resolve', cache_id, dias=30)
    if guardado is not None:
        return guardado or None

    dica, ano = _dica(grupo), grupo.ano
    achado, nota = None, 0.0
    for termo in consultas(grupo):
        c, n = melhor(termo, anilist_buscar(termo), dica, ano)
        if n > nota:
            achado, nota = c, n
        if nota >= ACEITA:
            break

    # TMDB entra quando o AniList não resolveu, ou para achar o id que o Kodi usa
    if nota < ACEITA or (achado and 'tmdb' not in (achado.get('ids') or {})):
        termo = (achado or {}).get('titulo') or (consultas(grupo) or [''])[0]
        if termo:
            c, n = melhor(termo, tmdb_buscar(termo, dica, ano), dica, ano)
            if achado and c and n >= REVISAR:
                # o AniList deu o nome; o TMDB dá o id que o scraper do Kodi precisa
                achado.setdefault('ids', {}).update(c.get('ids') or {})
                if not achado.get('sinopse'):
                    achado['sinopse'] = c.get('sinopse')
                nota = max(nota, n)
            elif n > nota:
                achado, nota = c, n

    # último recurso: o modelo de linguagem só chuta o nome; quem confirma é a base
    if nota < REVISAR and usar_llm:
        from resources.lib import jk_llm as LLM
        if LLM.disponivel():
            palpite = LLM.adivinhar(grupo)
            if palpite and palpite.get('titulo'):
                c, n = melhor(palpite['titulo'],
                              anilist_buscar(palpite['titulo'])
                              or tmdb_buscar(palpite['titulo'], dica, palpite.get('ano')),
                              palpite.get('tipo') or dica, palpite.get('ano'))
                if c and n >= REVISAR:
                    achado, nota = c, min(n, ACEITA - 0.05)   # palpite não vira certeza
                    achado['fonte'] = 'llm'
                elif palpite.get('tipo'):
                    achado = {'titulo': palpite['titulo'], 'ano': palpite.get('ano'),
                              'tipo': palpite['tipo'], 'fonte': 'llm', 'ids': {},
                              'sinopse': '', 'poster': None, 'fanart': None}
                    nota = REVISAR

    if not achado or nota < REVISAR:
        C.cache_put('resolve', cache_id, None)
        return None

    achado = dict(achado)
    achado['confianca'] = nota
    achado['revisar'] = nota < ACEITA
    C.cache_put('resolve', cache_id, achado)
    return achado


def esquecer(grupo):
    """Tira o grupo do cache de resolução (o usuário corrigiu o título à mão)."""
    for ns in ('resolve',):
        dados = C.cache_load(ns)
        if dados.pop(O.norm(grupo.titulo_bruto), None) is not None:
            C.cache_save(ns, dados)


def candidatos(termo, dica_tipo=None):
    """Lista para o usuário escolher na tela ('Buscar na web')."""
    vistos, saida = set(), []
    for c in (anilist_buscar(termo) or []) + (tmdb_buscar(termo, dica_tipo) or []):
        marca = (O.norm(c['titulo']), c.get('ano'))
        if marca in vistos:
            continue
        vistos.add(marca)
        c = dict(c)
        c['confianca'] = pontuar(termo, c, dica_tipo)
        saida.append(c)
    return sorted(saida, key=lambda c: c['confianca'], reverse=True)
