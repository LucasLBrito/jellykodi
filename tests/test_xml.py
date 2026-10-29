"""Todo XML da skin, do addon e do keymap precisa abrir; as versoes precisam bater.

Um XML quebrado na skin nao da erro nenhum na tela: o Kodi so deixa a janela em branco
e escreve uma linha no kodi.log. Por isso a checagem roda aqui, antes de empacotar.
"""
import glob
import os
import re
import xml.etree.ElementTree as ET

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTAS = ('skin.ark', 'plugin.video.ark', 'userdata')
XMLS = sorted(p for pasta in PASTAS
              for p in glob.glob(os.path.join(RAIZ, pasta, '**', '*.xml'), recursive=True))


def test_achou_os_xml():
    assert len(XMLS) > 50


@pytest.mark.parametrize('caminho', XMLS, ids=lambda p: os.path.relpath(p, RAIZ))
def test_xml_bem_formado(caminho):
    ET.parse(caminho)


def _versao_addon(pasta):
    return ET.parse(os.path.join(RAIZ, pasta, 'addon.xml')).getroot().get('version')


def test_versoes_iguais():
    with open(os.path.join(RAIZ, 'pyproject.toml'), encoding='utf-8') as fh:
        projeto = re.search(r'^version = "([^"]+)"', fh.read(), re.M).group(1)
    assert _versao_addon('skin.ark') == _versao_addon('plugin.video.ark') == projeto


def test_versao_no_changelog():
    with open(os.path.join(RAIZ, 'CHANGELOG.md'), encoding='utf-8') as fh:
        assert '## %s' % _versao_addon('plugin.video.ark') in fh.read()
