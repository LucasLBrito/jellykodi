# -*- coding: utf-8 -*-
"""Botão flutuante estilo Netflix ("Pular abertura" / "Próximo episódio")."""
import xbmc
import xbmcgui

from resources.lib.jk_common import ADDON

BTN_MAIN = 100
BTN_SECOND = 101
LBL_INFO = 300

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_PREVIOUS_MENU = 10
ACTION_STOP = 13
ACTION_SHOW_OSD = 24
ACTION_NAV_BACK = 92
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_MOUSE_RIGHT_CLICK = 101
ACTION_MOUSE_WHEEL_UP = 104
ACTION_MOUSE_WHEEL_DOWN = 105

# Como o Kodi trata as teclas enquanto este botão está na tela (testado no Kodi 21):
# - Pausa, avançar/voltar, legenda, áudio, volume, capítulo, Info e Parar o Kodi JÁ
#   entrega sozinho ao vídeo. NÃO repetir aqui: antes o código pausava de novo, e a
#   pausa ligava e desligava na hora ("pausar falha às vezes").
# - O que não chega ao vídeo e precisa ser repassado: setas (o botão usa para navegar),
#   o menu do player (OSD) e o mouse.
# - Para o vídeo tratar, use Action(X) SEM janela; Action(X,fullscreenvideo) não faz
#   nada para avançar/voltar. Só o OSD precisa ir direto para a janela do vídeo.


class OverlayButton(xbmcgui.WindowXMLDialog):
    """Janela não-modal. O serviço lê .result a cada meio segundo."""

    def __init__(self, *args, **kwargs):
        self.main_label = kwargs.get('main_label', '')
        self.second_label = kwargs.get('second_label', '')
        self.info_label = kwargs.get('info_label', '')
        self.result = None
        self._ready = False
        self._clicked = False

    @classmethod
    def create(cls, **kwargs):
        return cls('script-ark-overlay.xml', ADDON.getAddonInfo('path'), 'default', '1080i', **kwargs)

    def onInit(self):
        self._ready = True
        self.getControl(BTN_MAIN).setLabel(self.main_label)
        second = self.getControl(BTN_SECOND)
        second.setLabel(self.second_label)
        second.setVisible(bool(self.second_label))
        self.getControl(LBL_INFO).setLabel(self.info_label)
        self.setFocusId(BTN_MAIN)

    def set_main_label(self, text):
        self.main_label = text
        if self._ready:
            try:
                self.getControl(BTN_MAIN).setLabel(text)
            except RuntimeError:
                pass

    def onClick(self, control_id):
        # o Kodi avisa o clique (onClick) antes de mandar a mesma ação para onAction
        self._clicked = True
        self.result = 'main' if control_id == BTN_MAIN else 'second'

    def onAction(self, action):
        aid = action.getId()
        clicked, self._clicked = self._clicked, False
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.result = 'dismiss'
        elif aid == ACTION_STOP:
            self.result = 'dismiss'     # o Kodi para o vídeo sozinho
        elif aid in (ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT):
            # Com dois botões ("Assistir créditos" | "Próximo episódio"), esquerda/direita
            # trocam de botão. Com um botão só, viram voltar/avançar, igual no vídeo.
            if not self.second_label:
                xbmc.executebuiltin('Action(StepBack)' if aid == ACTION_MOVE_LEFT else 'Action(StepForward)')
        elif aid == ACTION_SHOW_OSD:
            xbmc.executebuiltin('Action(OSD,fullscreenvideo)')
        elif aid == ACTION_MOUSE_LEFT_CLICK:
            # clique fora do botão: o mesmo que no vídeo (abre o menu do player)
            if not clicked:
                xbmc.executebuiltin('Action(OSD,fullscreenvideo)')
        elif aid == ACTION_MOUSE_RIGHT_CLICK:
            xbmc.executebuiltin('Action(Info)')
        elif aid == ACTION_MOUSE_WHEEL_UP:
            xbmc.executebuiltin('Action(StepForward)')
        elif aid == ACTION_MOUSE_WHEEL_DOWN:
            xbmc.executebuiltin('Action(StepBack)')
