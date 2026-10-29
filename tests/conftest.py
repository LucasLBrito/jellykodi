"""Prepara um "Kodi de mentira" antes de importar o addon.

O addon importa `xbmc`, `xbmcaddon` etc. no topo dos modulos, entao os stubs e a pasta
de perfil temporaria precisam existir ANTES do primeiro import.
"""
import os
import sys
import tempfile

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

os.environ.setdefault('ARK_TEST_PROFILE', tempfile.mkdtemp(prefix='ark-perfil-'))
sys.path.insert(0, os.path.join(AQUI, 'kodi_stubs'))
sys.path.insert(0, os.path.join(RAIZ, 'plugin.video.ark'))

import xbmcaddon  # noqa: E402

from resources.lib import jk_common as C  # noqa: E402
from resources.lib import jk_organize as O  # noqa: E402


@pytest.fixture(autouse=True)
def perfil_isolado(tmp_path, monkeypatch):
    """Cada teste ganha state.json, livro-razao e ajustes proprios."""
    perfil = tmp_path / 'perfil'
    perfil.mkdir()
    monkeypatch.setattr(C, 'PROFILE', str(perfil))
    monkeypatch.setattr(C, 'STATE_FILE', str(perfil / 'state.json'))
    monkeypatch.setattr(C, 'CACHE_DIR', str(perfil / 'cache'))
    monkeypatch.setattr(O, 'LEDGER_FILE', str(perfil / 'organizados.json'))
    monkeypatch.setattr(xbmcaddon, 'SETTINGS', {'movie_folders': True, 'unknown_bucket': True})
    C.ADDON = xbmcaddon.Addon()
    C._FOLDER_ART.clear()
    yield perfil


@pytest.fixture
def biblioteca(tmp_path):
    """Pastas Downloads, Series e Filmes vazias, lado a lado (como em C:/Kodi)."""
    raiz = tmp_path / 'Kodi'
    pastas = {nome: raiz / nome for nome in ('Downloads', 'Series', 'Filmes')}
    for p in pastas.values():
        p.mkdir(parents=True)
    return pastas


@pytest.fixture
def criar():
    """Cria arquivos de mentira. O organizador so olha nomes e tamanhos."""
    def _criar(base, *rels, conteudo=b'x'):
        caminhos = []
        for rel in rels:
            p = base.joinpath(*rel.split('/'))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(conteudo)
            caminhos.append(p)
        return caminhos
    return _criar
