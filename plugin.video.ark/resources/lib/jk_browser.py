# -*- coding: utf-8 -*-
"""A tela de organizar: à esquerda o que achei, à direita como vai ficar.

Um `WindowXMLDialog` com `doModal()`, aberto de dentro de uma ação `RunPlugin`. Duas
regras que não podem ser quebradas:

* **Nunca** acrescentar `endOfDirectory` à rota que abre esta tela, e nunca abri-la de
  dentro de uma listagem de diretório: lá o Kodi espera a listagem terminar e a janela
  travaria a navegação. As ações do Ark que só mostram diálogo já são assim.
* **Nunca** abrir do service.py. O serviço grava o pedido no state e manda um
  `RunPlugin`, que cria a thread de plugin certa.

Nada de `Dialog().multiselect` aqui: a skin não desenha o visto (está registrado nas
NOTAS-DE-DESENVOLVIMENTO) e um episódio já ficou para trás por causa disso. O "pular"
é um estado do próprio item, escrito no texto.
"""
import os

import xbmc
import xbmcgui

from resources.lib import jk_common as C
from resources.lib import jk_lookup as L
from resources.lib import jk_organize as O

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

LBL_TITULO = 400
LST_ORIGEM = 410
LST_DESTINO = 420
IMG_CAPA = 430
TXT_INFO = 440
BTN_ORGANIZAR = 451
BTN_TITULO = 452
BTN_PULAR = 453
BTN_BUSCAR = 454
BTN_FECHAR = 455
LBL_RODAPE = 460

FONTES = {
    'arquivo': 'pelo nome do arquivo',
    'pasta': 'pelo nome da pasta',
    'anilist': 'AniList',
    'tmdb': 'TMDB',
    'llm': 'modelo local',
    'manual': 'você corrigiu',
}


def tamanho_legivel(bytes_):
    for unidade in ('B', 'KB', 'MB', 'GB', 'TB'):
        if bytes_ < 1024 or unidade == 'TB':
            return '%.0f %s' % (bytes_, unidade) if unidade in ('B', 'KB') \
                else '%.1f %s' % (bytes_, unidade)
        bytes_ /= 1024.0
    return '?'


def _bytes_do_grupo(g):
    total = 0
    for it in g.itens:
        try:
            total += os.path.getsize(it.origem)
        except OSError:
            pass
    return total


class Organizador(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        # sem super().__init__(): o Kodi recebe os argumentos no __new__ da
        # WindowXMLDialog, e é assim que o jk_dialog.py já faz
        self.grupos = kwargs.get('grupos') or []
        self.series_root = kwargs.get('series_root')
        self.filmes_root = kwargs.get('filmes_root')
        self.resultado = None          # None = fechou sem fazer nada | 'organizar'
        self.foco = -1

    @classmethod
    def abrir(cls, grupos, series_root, filmes_root):
        """Devolve ('organizar'|None, grupos já com as correções do usuário)."""
        janela = cls('script-ark-organizar.xml', C.ADDON.getAddonInfo('path'),
                     'default', '1080i', grupos=grupos,
                     series_root=series_root, filmes_root=filmes_root)
        janela.doModal()
        resultado, grupos = janela.resultado, janela.grupos
        del janela                     # solta a janela; sem isto o XML fica preso
        return resultado, grupos

    # ------------------------------------------------------------------ montagem
    def onInit(self):
        self._rotular_botoes()
        self._pintar()

    def _rotular_botoes(self):
        for cid, texto in ((BTN_ORGANIZAR, 'Organizar'),
                           (BTN_TITULO, 'Corrigir título'),
                           (BTN_PULAR, 'Pular / incluir'),
                           (BTN_BUSCAR, 'Buscar na web'),
                           (BTN_FECHAR, 'Fechar')):
            try:
                self.getControl(cid).setLabel(texto)
            except Exception:
                pass

    def _item_origem(self, g):
        pastas = sorted(g.pastas)
        nome = os.path.basename(O.tidy_path(pastas[0])) if pastas else ''
        rotulo = nome or '(solto na raiz)'
        if g.pular:
            rotulo = '[COLOR 55FFFFFF]%s[/COLOR]' % rotulo
        item = xbmcgui.ListItem(rotulo, '%d vídeo(s) · %s'
                                % (len(g.itens), tamanho_legivel(_bytes_do_grupo(g))))
        capa = C.art_for(g.itens[0].origem) if g.itens else {}
        item.setArt({'thumb': (capa or {}).get('thumb') or 'DefaultFolder.png'})
        return item

    def _item_destino(self, g):
        vai = g.a_organizar()
        if g.pular:
            titulo = '[COLOR 55FFFFFF]%s — pulado[/COLOR]' % g.titulo
            detalhe = 'nada será feito com este'
        elif not vai:
            titulo = g.titulo
            detalhe = 'nada a fazer: já está na biblioteca'
        elif g.tipo == 'desconhecido':
            titulo = 'Não identifiquei: %s' % g.titulo
            detalhe = '%d arquivo(s) vão para %s' % (len(vai), O.UNKNOWN_DIR)
        else:
            raiz = self.series_root if g.tipo in ('serie', 'misto') else self.filmes_root
            # só o nome da raiz e a temporada: o caminho inteiro não cabe na coluna e
            # repetiria o nome da série, que já está no título logo acima
            onde = os.path.basename(O.tidy_path(raiz or '')) or 'Biblioteca'
            temporada = os.path.basename(os.path.dirname(vai[0].destino))
            if temporada and temporada.lower().startswith('season'):
                onde = '%s › %s' % (onde, temporada)
            titulo = '%s%s' % (g.titulo, ' (%s)' % g.ano if g.ano else '')
            detalhe = '%s · %d arquivo(s)' % (onde, len(vai))
        item = xbmcgui.ListItem(titulo, detalhe)
        item.setArt({'thumb': (g.meta or {}).get('poster') or ''})
        return item

    def _pintar(self):
        try:
            esquerda = self.getControl(LST_ORIGEM)
            direita = self.getControl(LST_DESTINO)
        except Exception as exc:
            C.log('tela de organizar sem controles: %s' % exc, xbmc.LOGERROR)
            return
        pos = 0
        try:
            pos = esquerda.getSelectedPosition()
        except Exception:
            pass
        esquerda.reset()
        direita.reset()
        esquerda.addItems([self._item_origem(g) for g in self.grupos])
        direita.addItems([self._item_destino(g) for g in self.grupos])
        if self.grupos:
            pos = min(max(pos, 0), len(self.grupos) - 1)
            esquerda.selectItem(pos)
            direita.selectItem(pos)
        self.foco = -1
        self._pintar_detalhe(pos)
        self._pintar_cabecalho()

    def _pintar_cabecalho(self):
        series = len([g for g in self.grupos if g.tipo in ('serie', 'misto')])
        filmes = len([g for g in self.grupos if g.tipo == 'filme'])
        duvidas = len([g for g in self.grupos if g.tipo == 'desconhecido'])
        partes = []
        if series:
            partes.append('%d série(s)' % series)
        if filmes:
            partes.append('%d filme(s)' % filmes)
        if duvidas:
            partes.append('%d sem identificar' % duvidas)
        arquivos = sum(len(g.a_organizar()) for g in self.grupos if not g.pular)
        self._texto(LBL_TITULO, 'Achei %s' % (', '.join(partes) or 'nada'))
        self._texto(LBL_RODAPE,
                    'Vou organizar %d arquivo(s). Os downloads ficam onde estão — a '
                    'biblioteca usa atalho e não gasta espaço a mais.' % arquivos)

    def _pintar_detalhe(self, pos):
        g = self.grupos[pos] if 0 <= pos < len(self.grupos) else None
        if g is None:
            return
        capa = (g.meta or {}).get('poster') or ''
        # a moldura da capa só aparece quando há capa; vazia parecia defeito na tela
        self.setProperty('ark_capa', capa)
        try:
            self.getControl(IMG_CAPA).setImage(capa)
        except Exception:
            pass
        linhas = ['[B]%s[/B]' % g.titulo]
        if g.titulo != g.titulo_bruto:
            linhas.append('no arquivo: %s' % g.titulo_bruto)
        linhas.append('identificado %s' % FONTES.get(g.fonte, g.fonte))
        linhas.append('certeza: %d%%' % round(g.confianca * 100))
        linhas.append(g.rotulo())
        sinopse = (g.meta or {}).get('sinopse')
        if sinopse:
            linhas += ['', sinopse[:600]]
        self._texto(TXT_INFO, '\n'.join(linhas))

    def _texto(self, cid, texto):
        try:
            controle = self.getControl(cid)
            if hasattr(controle, 'setText'):
                controle.setText(texto)
            else:
                controle.setLabel(texto)
        except Exception:
            pass

    # ------------------------------------------------------------------ interação
    def _grupo(self):
        for cid in (LST_ORIGEM, LST_DESTINO):
            try:
                if self.getFocusId() == cid:
                    pos = self.getControl(cid).getSelectedPosition()
                    if 0 <= pos < len(self.grupos):
                        return self.grupos[pos]
            except Exception:
                pass
        try:
            pos = self.getControl(LST_ORIGEM).getSelectedPosition()
            return self.grupos[pos] if 0 <= pos < len(self.grupos) else None
        except Exception:
            return None

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.resultado = None
            self.close()
            return
        self._espelhar()

    def _espelhar(self):
        """Mantém as duas colunas na mesma linha: elas são o mesmo grupo."""
        try:
            cid = self.getFocusId()
        except Exception:
            return
        if cid not in (LST_ORIGEM, LST_DESTINO):
            return
        outro = LST_DESTINO if cid == LST_ORIGEM else LST_ORIGEM
        try:
            pos = self.getControl(cid).getSelectedPosition()
            self.getControl(outro).selectItem(pos)
        except Exception:
            return
        if pos != self.foco:
            self.foco = pos
            self._pintar_detalhe(pos)

    def onClick(self, cid):
        if cid == BTN_ORGANIZAR:
            self.resultado = 'organizar'
            self.close()
        elif cid == BTN_FECHAR:
            self.resultado = None
            self.close()
        elif cid == BTN_TITULO:
            self._corrigir()
        elif cid == BTN_PULAR:
            self._pular()
        elif cid == BTN_BUSCAR:
            self._buscar()
        elif cid in (LST_ORIGEM, LST_DESTINO):
            self._menu_do_grupo()

    def _menu_do_grupo(self):
        g = self._grupo()
        if g is None:
            return
        opcoes = ['Corrigir o título', 'Buscar na web',
                  'Incluir este' if g.pular else 'Pular este',
                  'Ver os arquivos deste grupo']
        escolha = xbmcgui.Dialog().select(g.titulo, opcoes)
        if escolha == 0:
            self._corrigir()
        elif escolha == 1:
            self._buscar()
        elif escolha == 2:
            self._pular()
        elif escolha == 3:
            self._ver_arquivos(g)

    def _ver_arquivos(self, g):
        linhas = []
        for it in g.itens:
            if it.destino:
                linhas.append('%s\n   vai virar  %s' % (it.nome,
                                                        os.path.basename(it.destino)))
            elif it.tipo == 'extra':
                linhas.append('%s\n   fica no Downloads (extra)' % it.nome)
            else:
                linhas.append('%s\n   nada a fazer' % it.nome)
        xbmcgui.Dialog().textviewer(g.titulo, '\n\n'.join(linhas))

    def _pular(self):
        g = self._grupo()
        if g is None:
            return
        g.pular = not g.pular
        O.recalcular(g, self.series_root, self.filmes_root)
        self._pintar()

    def _corrigir(self):
        g = self._grupo()
        if g is None:
            return
        novo = xbmcgui.Dialog().input('Qual é o título certo?', g.titulo,
                                      type=xbmcgui.INPUT_ALPHANUM)
        novo = (novo or '').strip()
        if not novo:
            return
        self._aplicar_titulo(g, novo, self._escolher(novo, g))

    def _buscar(self):
        g = self._grupo()
        if g is None:
            return
        achado = self._escolher(g.titulo, g)
        if achado:
            self._aplicar_titulo(g, g.titulo, achado)

    def _escolher(self, termo, g):
        """Pergunta ao AniList/TMDB e deixa o usuário escolher. None = usa o que digitou."""
        if not C.setting_bool('lookup_online', True):
            return None
        barra = xbmcgui.DialogProgressBG()
        try:
            barra.create('Ark', 'Procurando "%s"...' % termo)
            achados = L.candidatos(termo, g.tipo if g.tipo in ('serie', 'filme') else None)
        except Exception as exc:
            C.log('busca manual falhou: %s' % exc, xbmc.LOGWARNING)
            achados = []
        finally:
            try:
                barra.close()
            except Exception:
                pass
        if not achados:
            xbmcgui.Dialog().notification('Ark', 'Não achei nada para "%s"' % termo)
            return None
        tipos = {'serie': 'série', 'filme': 'filme', 'extra': 'especial'}
        opcoes = ['%s%s — %s (%d%%)' % (c['titulo'],
                                        ' (%s)' % c['ano'] if c.get('ano') else '',
                                        tipos.get(c.get('tipo'), '?'),
                                        round(c.get('confianca', 0) * 100))
                  for c in achados[:10]]
        opcoes.append('Usar exatamente o que eu digitei')
        escolha = xbmcgui.Dialog().select('Qual destes?', opcoes)
        if escolha < 0 or escolha >= len(achados[:10]):
            return None
        return achados[escolha]

    def _aplicar_titulo(self, g, digitado, achado):
        g.titulo = (achado or {}).get('titulo') or digitado
        g.ano = (achado or {}).get('ano') or g.ano
        g.fonte = 'manual' if not achado else achado.get('fonte', 'manual')
        g.confianca = 1.0
        if achado:
            g.meta = achado
            tipo = achado.get('tipo')
            if tipo in ('serie', 'filme'):
                for it in g.itens:
                    if it.tipo == 'desconhecido':
                        it.tipo, it.motivo = tipo, 'pesquisa'
        L.esquecer(g)
        O.recalcular(g, self.series_root, self.filmes_root)
        self._pintar()
