"""Utilitarios de jk_common, jk_lookup e jk_llm que nao dependem do Kodi."""
import json
import os

import pytest

from resources.lib import jk_common as C
from resources.lib import jk_llm as L
from resources.lib import jk_lookup as K


# ---------------------------------------------------------------- jk_common
@pytest.mark.parametrize('nome, eh', [
    ('ep.mkv', True), ('EP.MP4', True), ('a.m2ts', True), ('a.srt', False), ('a', False),
])
def test_is_video(nome, eh):
    assert C.is_video(nome) is eh


def test_natural_key_ordena_numeros_como_gente():
    nomes = ['ep10.mkv', 'ep2.mkv', 'Ep1.mkv']
    assert sorted(nomes, key=C.natural_key) == ['Ep1.mkv', 'ep2.mkv', 'ep10.mkv']


@pytest.mark.parametrize('caminho, esperado', [
    ('C:\\Kodi\\Series\\a.mkv', ('C:\\Kodi\\Series\\', 'a.mkv')),
    ('smb://nas/videos/a.mkv', ('smb://nas/videos/', 'a.mkv')),
    ('a.mkv', ('', 'a.mkv')),
])
def test_split_path(caminho, esperado):
    assert C.split_path(caminho) == esperado


@pytest.mark.parametrize('nome, eh', [
    ('Show S01E02.mkv', True), ('show 1x02.mkv', True), ('Ep 5.mkv', True),
    ('Episódio 5.mkv', True), ('Frieren - 07.mkv', True),
    ('Filme Legal 2019.mkv', False), ('Rebellion.mkv', False),
])
def test_looks_like_episode(nome, eh):
    assert C.looks_like_episode('C:\\x\\' + nome) is eh


@pytest.mark.parametrize('caminho, titulo', [
    ('C:\\x\\Filme.Legal.2019.1080p.WEB-DL.mkv', 'Filme Legal 2019'),
    ('C:\\x\\[Grupo] Frieren - 07 [1080p].mkv', 'Frieren - 07'),
    ('C:\\x\\Rebellion.mkv', 'Rebellion'),
])
def test_nice_title(caminho, titulo):
    assert C.nice_title(caminho) == titulo


@pytest.mark.parametrize('caminho, nome', [
    ('C:\\Series\\Korra\\Season 01\\ep.mkv', 'Korra'),
    ('C:\\Series\\Korra\\Temporada 2\\ep.mkv', 'Korra'),
    ('C:\\Series\\Madoka\\ep.mkv', 'Madoka'),
    ('smb://nas/Series/Korra/S01/ep.mkv', 'Korra'),
])
def test_folder_name_pula_pasta_de_temporada(caminho, nome):
    assert C.folder_name(caminho) == nome


@pytest.mark.parametrize('seg, texto', [(0, '0:00'), (65, '1:05'), (3661, '1:01:01'), (-5, '0:00')])
def test_fmt_time(seg, texto):
    assert C.fmt_time(seg) == texto


@pytest.mark.parametrize('capitulo, intro, outro', [
    ('Opening', True, False), ('Abertura', True, False), ('OP', True, False),
    ('Ending', False, True), ('Créditos', False, True), ('Preview', False, True),
    ('Parte A', False, False),
])
def test_capitulos_pulaveis(capitulo, intro, outro):
    assert bool(C.INTRO_RE.search(capitulo)) is intro
    assert bool(C.OUTRO_RE.search(capitulo)) is outro


def test_next_video_na_mesma_pasta_e_na_proxima_temporada(tmp_path):
    serie = tmp_path / 'Korra'
    for rel in ('Season 01/ep1.mkv', 'Season 01/ep2.mkv', 'Season 02/ep1.mkv',
                'Season 02/notas.txt'):
        p = serie.joinpath(*rel.split('/'))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'x')
    s1 = str(serie / 'Season 01') + os.sep
    s2 = str(serie / 'Season 02') + os.sep
    assert C.next_video(s1 + 'ep1.mkv') == s1 + 'ep2.mkv'
    assert C.next_video(s1 + 'ep2.mkv') == s2 + 'ep1.mkv'
    assert C.next_video(s2 + 'ep1.mkv') is None


def test_folder_art_olha_a_pasta_da_serie(tmp_path):
    temporada = tmp_path / 'Korra' / 'Season 01'
    temporada.mkdir(parents=True)
    (tmp_path / 'Korra' / 'poster.jpg').write_bytes(b'x')
    (temporada / 'fanart.jpg').write_bytes(b'x')
    art = C.art_for(str(temporada) + os.sep + 'ep1.mkv')
    assert art['poster'].endswith('poster.jpg')
    # o poster em pe nunca vira 'landscape' (o card e deitado e cortaria a imagem)
    assert art['landscape'].endswith('fanart.jpg')


# ---------------------------------------------------------------- state.json
def test_state_roundtrip():
    st = C.load_state()
    assert st == {'history': {}, 'intros': {}, 'credits': {}}
    st['folders'] = {'series': 'C:\\Kodi\\Series'}
    C.save_state(st)
    assert C.load_state()['folders'] == {'series': 'C:\\Kodi\\Series'}


def test_state_com_bom_e_lido():
    with open(C.STATE_FILE, 'w', encoding='utf-8-sig') as fh:
        json.dump({'folders': {'series': 'x'}}, fh)
    assert C.load_state()['folders'] == {'series': 'x'}


def test_state_ilegivel_nunca_e_sobrescrito():
    with open(C.STATE_FILE, 'w', encoding='utf-8') as fh:
        fh.write('{ isto nao e json')
    st = C.load_state()
    assert os.path.exists(C.STATE_FILE + '.ruim')
    C.save_state(st)                                   # tem que recusar
    with open(C.STATE_FILE, encoding='utf-8') as fh:
        assert fh.read() == '{ isto nao e json'


def test_historico_fica_nos_300_mais_recentes():
    st = C.load_state()
    st['history'] = {'v%d' % i: {'ts': i} for i in range(350)}
    C.save_state(st)
    hist = C.load_state()['history']
    assert len(hist) == 300 and 'v349' in hist and 'v0' not in hist


def test_cache_expira():
    C.cache_put('teste', 'k', 42)
    assert C.cache_get('teste', 'k') == 42
    dados = C.cache_load('teste')
    dados['k']['ts'] = 0
    C.cache_save('teste', dados)
    assert C.cache_get('teste', 'k', dias=30) is None
    assert C.cache_get('teste', 'k', dias=0) == 42


# ---------------------------------------------------------------- jk_lookup
@pytest.mark.parametrize('nome, limpo', [
    ('[SubsPlease] Frieren (1080p) [A1B2C3D4]', 'Frieren'),
    ('Frieren.S01.1080p.WEB-DL.x265.10bit', 'Frieren S01'),
    ('Frieren - 07', 'Frieren'),
    ('Kimetsu no Yaiba BluRay Dual Audio', 'Kimetsu no Yaiba'),
])
def test_limpar_para_busca(nome, limpo):
    assert K.limpar_para_busca(nome) == limpo


def test_pontuar_prefere_titulo_exato_e_ano_certo():
    termo = 'Madoka Magica'
    certo = {'titulos': ['Puella Magi Madoka Magica', 'Madoka Magica'], 'ano': 2011,
             'tipo': 'serie'}
    errado = {'titulos': ['Magical Girl Site'], 'ano': 2018, 'tipo': 'serie'}
    assert K.pontuar(termo, certo, 'serie', 2011) == 1.0
    assert K.pontuar(termo, errado, 'serie', 2011) < K.REVISAR
    assert K.melhor(termo, [errado, certo], 'serie')[0] is certo


def test_pontuar_tipo_errado_pesa_contra():
    c = {'titulos': ['Frieren'], 'tipo': 'filme'}
    assert K.pontuar('Frieren', c, 'serie') < K.pontuar('Frieren', c, 'filme')


def test_melhor_sem_candidatos():
    assert K.melhor('x', []) == (None, 0.0)


# ---------------------------------------------------------------- jk_llm
@pytest.mark.parametrize('texto, esperado', [
    ('{"titulo": "Frieren"}', {'titulo': 'Frieren'}),
    ('```json\n{"titulo": "Frieren"}\n```', {'titulo': 'Frieren'}),
    ('Claro! Aqui esta: {"titulo": "Frieren", "ano": 2023} Espero ter ajudado.',
     {'titulo': 'Frieren', 'ano': 2023}),
    ('nao sei', None),
    ('', None),
])
def test_llm_extrai_json_da_resposta(texto, esperado):
    assert L._so_json(texto) == esperado
