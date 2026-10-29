"""Planejador do organizador (jk_organize): para onde cada arquivo do Downloads vai.

Nada aqui move arquivo: os testes so chamam o planejamento, que le nomes de pastas e
arquivos de verdade dentro de uma pasta temporaria.
"""
import os

import pytest
import xbmcaddon

from resources.lib import jk_common as C
from resources.lib import jk_organize as O


def destinos(biblioteca):
    """{nome do arquivo de origem: destino relativo a C:\\Kodi (ou None)}."""
    raiz = str(biblioteca['Downloads'].parent)
    grupos = O.plan_groups(str(biblioteca['Downloads']), str(biblioteca['Series']),
                           str(biblioteca['Filmes']))
    saida = {}
    for g in grupos:
        for it in g.itens:
            rel = os.path.relpath(it.destino, raiz).replace(os.sep, '/') if it.destino else None
            saida[it.nome] = rel
    return saida


def itens(biblioteca):
    grupos = O.plan_groups(str(biblioteca['Downloads']), str(biblioteca['Series']),
                           str(biblioteca['Filmes']))
    return {it.nome: it for g in grupos for it in g.itens}


# ---------------------------------------------------------------- leitura do nome
@pytest.mark.parametrize('base, esperado', [
    ('Show.Name.S01E02.1080p.WEB-DL', ('Show Name', 1, 2)),
    ('show_name_s02e10', ('show name', 2, 10)),
    ('A Lenda de Korra S03E13', ('A Lenda de Korra', 3, 13)),
    ('Show Name 1x02', ('Show Name', 1, 2)),
    ('Show Name - 2x105', ('Show Name', 2, 105)),
    ('[SubsPlease] Frieren - 07 [1080p]', ('Frieren', None, 7)),
    ('Frieren - 07', ('Frieren', None, 7)),
    ('Frieren - 07v2', ('Frieren', None, 7)),
])
def test_parse_filename_reconhece_episodio(base, esperado):
    assert O.parse_filename(base) == esperado


@pytest.mark.parametrize('base', ['Filme Qualquer 2019', '01', 'extras', 'Ep 03'])
def test_parse_filename_sem_episodio_no_nome(base):
    assert O.parse_filename(base) is None


@pytest.mark.parametrize('base, numero', [
    ('01', 1), ('Ep 03', 3), ('Episodio 12', 12), ('Episódio 5', 5), ('ep_07', 7),
    ('Capitulo 2', 2), ('05 - O Nome do Episodio', 5),
])
def test_parse_only_number(base, numero):
    assert O.parse_only_number(base) == numero


@pytest.mark.parametrize('base', ['extras', 'Filme Legal 2019', 'making of'])
def test_parse_only_number_sem_numero(base):
    assert O.parse_only_number(base) is None


@pytest.mark.parametrize('nome, temporada', [
    ('Season 2', 2), ('season02', 2), ('S03', 3), ('Temporada 1', 1), ('Livro 2', 2),
    ('Book 3', 3), ('Season_04', 4), ('Naruto', None), ('Specials', None),
])
def test_season_from_dir(nome, temporada):
    assert O.season_from_dir(nome) == temporada


@pytest.mark.parametrize('base, esperado', [
    ('Filme.Legal.2019.1080p.BluRay', ('Filme Legal', '2019')),
    ('Puella Magi Madoka Magica (2013)', ('Puella Magi Madoka Magica', '2013')),
    ('Outro Filme [2001]', ('Outro Filme', '2001')),
])
def test_movie_title(base, esperado):
    assert O.movie_title(base) == esperado


def test_norm_ignora_acento_maiuscula_e_simbolo():
    assert O.norm('Séries: A Lenda!') == O.norm('series a lenda') == 'series a lenda'


# ---------------------------------------------------------------- o plano completo
def test_sxxeyy_vai_para_a_temporada(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Show.Name.S01E02.1080p.WEB-DL.mkv')
    assert destinos(biblioteca) == {
        'Show.Name.S01E02.1080p.WEB-DL.mkv': 'Series/Show Name/Season 01/Show Name S01E02.mkv'}


def test_formato_1x02(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Show Name 2x05.mp4')
    assert destinos(biblioteca) == {
        'Show Name 2x05.mp4': 'Series/Show Name/Season 02/Show Name S02E05.mp4'}


def test_anime_nome_traco_numero_vira_temporada_1(biblioteca, criar):
    criar(biblioteca['Downloads'], '[SubsPlease] Frieren - 07 [1080p].mkv')
    it = itens(biblioteca)['[SubsPlease] Frieren - 07 [1080p].mkv']
    assert it.motivo == 'nome do arquivo (anime)'
    assert destinos(biblioteca)[it.nome] == 'Series/Frieren/Season 01/Frieren S01E07.mkv'


def test_anime_pega_temporada_da_pasta(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Frieren/Season 2/Frieren - 03.mkv')
    assert destinos(biblioteca) == {
        'Frieren - 03.mkv': 'Series/Frieren/Season 02/Frieren S02E03.mkv'}


def test_nome_vem_da_pasta(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Naruto/01.mkv', 'Naruto/Ep 02.mkv')
    assert destinos(biblioteca) == {
        '01.mkv': 'Series/Naruto/Season 01/Naruto S01E01.mkv',
        'Ep 02.mkv': 'Series/Naruto/Season 01/Naruto S01E02.mkv',
    }
    assert itens(biblioteca)['01.mkv'].motivo == 'nome da pasta'


def test_temporada_vem_da_pasta(biblioteca, criar):
    criar(biblioteca['Downloads'], 'One Piece/Season 2/05.mkv')
    assert destinos(biblioteca) == {
        '05.mkv': 'Series/One Piece/Season 02/One Piece S02E05.mkv'}


def test_numero_solto_na_raiz_nao_vira_serie(biblioteca, criar):
    # a pasta vigiada nao e nome de serie: '01.mkv' solto no Downloads nao tem dono
    criar(biblioteca['Downloads'], '01.mkv')
    it = itens(biblioteca)['01.mkv']
    assert it.tipo == 'desconhecido'
    assert '_Nao_Identificado' in destinos(biblioteca)['01.mkv']


def test_maioria_da_pasta_puxa_os_ambiguos(biblioteca, criar):
    criar(biblioteca['Downloads'],
          'baixados/Frieren - 01.mkv', 'baixados/Frieren - 02.mkv', 'baixados/03.mkv')
    it = itens(biblioteca)['03.mkv']
    assert it.motivo == 'maioria da pasta'
    assert destinos(biblioteca)['03.mkv'] == 'Series/Frieren/Season 01/Frieren S01E03.mkv'


def test_um_so_arquivo_nao_e_maioria(biblioteca, criar):
    criar(biblioteca['Downloads'], 'baixados/Frieren - 01.mkv', 'baixados/03.mkv')
    assert itens(biblioteca)['03.mkv'].motivo == 'nome da pasta'


def test_filme_pelo_ano_ganha_pasta_propria(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Filme.Legal.2019.1080p.mkv')
    assert destinos(biblioteca) == {
        'Filme.Legal.2019.1080p.mkv': 'Filmes/Filme Legal (2019)/Filme Legal (2019).mkv'}


def test_filme_sem_pasta_propria(biblioteca, criar):
    xbmcaddon.SETTINGS['movie_folders'] = False
    criar(biblioteca['Downloads'], 'Filme.Legal.2019.mkv')
    assert destinos(biblioteca) == {'Filme.Legal.2019.mkv': 'Filmes/Filme Legal (2019).mkv'}


def test_extra_na_pasta_de_serie_nao_vira_filme(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Naruto/01.mkv', 'Naruto/02.mkv', 'Naruto/extras.mkv')
    it = itens(biblioteca)['extras.mkv']
    assert it.tipo == 'extra'
    assert it.destino is None            # fica no Downloads de proposito


def test_filme_da_franquia_na_pasta_da_serie_segue_adiante(biblioteca, criar):
    # com ano no nome, e o filme da franquia: nao e tratado como extra
    criar(biblioteca['Downloads'], 'Naruto/01.mkv', 'Naruto/Naruto The Movie 2004.mkv')
    assert itens(biblioteca)['Naruto The Movie 2004.mkv'].tipo == 'filme'


def test_sem_pista_nao_e_renomeado(biblioteca, criar):
    # com as pastas escolhidas no app, os nao identificados ficam ao lado de Series/Filmes
    C.save_state({'folders': {'series': str(biblioteca['Series'])}})
    criar(biblioteca['Downloads'], 'coisa/bagunca total.mkv')
    rel = destinos(biblioteca)['bagunca total.mkv']
    assert rel == '_Nao_Identificado/coisa/bagunca total.mkv'


def test_sem_pista_e_sem_balde_fica_onde_esta(biblioteca, criar):
    xbmcaddon.SETTINGS['unknown_bucket'] = False
    criar(biblioteca['Downloads'], 'coisa/bagunca total.mkv')
    assert destinos(biblioteca) == {'bagunca total.mkv': None}


def test_legendas_vao_junto(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Show.S01E01.mkv', 'Show.S01E01.srt',
          'Show.S01E01.pt-BR.srt', 'Show.S01E01.nfo', 'Outro.S01E01.srt')
    it = itens(biblioteca)['Show.S01E01.mkv']
    assert sorted(sufixo for _origem, sufixo in it.legendas) == ['.pt-BR.srt', '.srt']


@pytest.mark.parametrize('nome', ['Show.S01E01.mkv.crdownload', 'Show.S01E01.mkv.part',
                                  'Show.S01E01.sample.mkv', 'Show.S01E01.txt'])
def test_ignora_download_pela_metade_sample_e_nao_video(biblioteca, criar, nome):
    criar(biblioteca['Downloads'], nome)
    assert O.plan_groups(str(biblioteca['Downloads']), str(biblioteca['Series']),
                         str(biblioteca['Filmes'])) == []


def test_profundidade_maxima(biblioteca, criar):
    criar(biblioteca['Downloads'], 'a/b/c/d/Show S01E01.mkv', 'a/b/c/d/e/f/Show S01E02.mkv')
    assert list(destinos(biblioteca)) == ['Show S01E01.mkv']


def test_reaproveita_pasta_existente_da_serie(biblioteca, criar):
    (biblioteca['Series'] / 'A Lenda de Korra').mkdir()
    criar(biblioteca['Downloads'], 'a lenda de korra S02E01.mkv')
    assert destinos(biblioteca) == {
        'a lenda de korra S02E01.mkv':
            'Series/A Lenda de Korra/Season 02/A Lenda de Korra S02E01.mkv'}


def test_nunca_sobrescreve_o_que_ja_existe(biblioteca, criar):
    criar(biblioteca['Series'], 'Show/Season 01/Show S01E01.mkv')
    criar(biblioteca['Downloads'], 'Show S01E01.mkv')
    assert destinos(biblioteca) == {'Show S01E01.mkv': None}


def test_dois_arquivos_para_o_mesmo_destino(biblioteca, criar):
    criar(biblioteca['Downloads'], 'a/Show S01E01.mkv', 'b/Show S01E01.mkv')
    grupos = O.plan_groups(str(biblioteca['Downloads']), str(biblioteca['Series']),
                           str(biblioteca['Filmes']))
    destinos_validos = [it.destino for g in grupos for it in g.itens if it.destino]
    assert len(destinos_validos) == 1


def test_livro_razao_nao_reorganiza(biblioteca, criar):
    (video,) = criar(biblioteca['Downloads'], 'Show S01E01.mkv')
    O.ledger_add([(str(video), str(biblioteca['Series'] / 'x.mkv'))], 'link')
    assert destinos(biblioteca) == {'Show S01E01.mkv': None}


def test_downloads_dentro_da_biblioteca_e_recusado(biblioteca, criar):
    dentro = biblioteca['Series'] / 'Downloads'
    criar(dentro, 'Show S01E01.mkv')
    assert O.plan_groups(str(dentro), str(biblioteca['Series']), str(biblioteca['Filmes'])) == []


def test_grupos_e_confianca(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Show S01E01.mkv', 'Show/02.mkv', 'Filme 2019.mkv')
    grupos = {g.titulo: g for g in O.plan_groups(
        str(biblioteca['Downloads']), str(biblioteca['Series']), str(biblioteca['Filmes']))}
    assert grupos['Show'].tipo == 'serie'
    # vale a pista mais fraca: 'nome da pasta' (0.6) derruba 'nome do arquivo' (1.0)
    assert grupos['Show'].confianca == 0.6
    assert grupos['Filme'].tipo == 'filme'
    assert grupos['Show'].rotulo() == '2 ep'


def test_plan_folder_formato_antigo(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Show S01E01.mkv')
    ((origem, destino),) = O.plan_folder(str(biblioteca['Downloads']),
                                         str(biblioteca['Series']), str(biblioteca['Filmes']))
    assert origem.endswith('Show S01E01.mkv')
    assert destino.endswith(os.path.join('Show', 'Season 01', 'Show S01E01.mkv'))


def test_recalcular_apos_corrigir_titulo(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Shw S01E01.mkv')
    (g,) = O.plan_groups(str(biblioteca['Downloads']), str(biblioteca['Series']),
                         str(biblioteca['Filmes']))
    g.titulo = 'Show Certo'
    O.recalcular(g, str(biblioteca['Series']), str(biblioteca['Filmes']))
    assert g.itens[0].destino.endswith(
        os.path.join('Show Certo', 'Season 01', 'Show Certo S01E01.mkv'))


def test_pesquisa_melhora_o_titulo(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Shingeki no Kyojin S01E01.mkv')
    grupos = O.plan_groups(
        str(biblioteca['Downloads']), str(biblioteca['Series']), str(biblioteca['Filmes']),
        resolver=lambda g: {'titulo': 'Attack on Titan', 'ano': '2013', 'fonte': 'anilist',
                            'confianca': 0.95})
    (g,) = grupos
    assert g.fonte == 'anilist' and g.confianca == 1.0
    assert 'Attack on Titan S01E01.mkv' in g.itens[0].destino


def test_pesquisa_que_falha_nao_derruba_o_plano(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Show S01E01.mkv')

    def quebra(_g):
        raise RuntimeError('sem rede')

    (g,) = O.plan_groups(str(biblioteca['Downloads']), str(biblioteca['Series']),
                         str(biblioteca['Filmes']), resolver=quebra)
    assert g.titulo == 'Show' and g.itens[0].destino


# ---------------------------------------------------------------- arrumar a biblioteca
def test_plan_tidy_poe_episodio_solto_na_temporada(biblioteca, criar):
    serie = biblioteca['Series']
    criar(serie, 'Madoka/Madoka S01E01.mkv', 'Madoka/Season 01/Madoka S01E02.mkv',
          'Madoka/bagunca ep x.mkv')
    planos = O.plan_tidy(str(serie))
    rel = [(os.path.relpath(a, serie), os.path.relpath(b, serie)) for a, b in planos]
    assert rel == [(os.path.join('Madoka', 'Madoka S01E01.mkv'),
                    os.path.join('Madoka', 'Season 01', 'Madoka S01E01.mkv'))]


def test_plan_tidy_numero_dentro_da_temporada(biblioteca, criar):
    serie = biblioteca['Series']
    criar(serie, 'Korra/Season 02/03.mkv')
    ((_, dst),) = O.plan_tidy(str(serie))
    assert dst.endswith(os.path.join('Korra', 'Season 02', 'Korra S02E03.mkv'))


# ---------------------------------------------------------------- vigia e resumo
def test_folder_signature_muda_quando_o_download_cresce(biblioteca, criar):
    (arq,) = criar(biblioteca['Downloads'], 'Show S01E01.mkv', conteudo=b'a')
    antes = O.folder_signature(str(biblioteca['Downloads']))
    arq.write_bytes(b'a' * 10)
    depois = O.folder_signature(str(biblioteca['Downloads']))
    assert antes[0] == depois[0] == 1
    assert depois[1] > antes[1]


def test_folder_signature_pasta_inexistente():
    assert O.folder_signature(os.path.join('nao', 'existe', 'mesmo')) is None


def test_resumo_agrupa_por_serie_e_temporada(biblioteca):
    s, f = str(biblioteca['Series']), str(biblioteca['Filmes'])
    planos = [('a', os.path.join(s, 'Korra', 'Season 01', 'x.mkv')),
              ('b', os.path.join(s, 'Korra', 'Season 01', 'y.mkv')),
              ('c', os.path.join(s, 'Korra', 'Season 02', 'z.mkv')),
              ('d', os.path.join(f, 'Filme (2019)', 'Filme (2019).mkv'))]
    assert O.resumo(planos, s, f) == [
        '[B]Filme (2019)[/B]:  1 vídeo(s)',
        '[B]Korra  ›  Temporada 1[/B]:  2 vídeo(s)',
        '[B]Korra  ›  Temporada 2[/B]:  1 vídeo(s)',
    ]
