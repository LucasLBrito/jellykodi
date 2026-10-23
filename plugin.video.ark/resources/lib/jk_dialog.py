# -*- coding: utf-8 -*-
"""Botão flutuante estilo Netflix ("Pular abertura" / "Próximo episódio")."""
import xbmc
import xbmcgui

from resources.lib.jk_common import ADDON

BTN_MAIN = 100
BTN_SECOND = 101
LBL_INFO = 300

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_PAUSE = 12
ACTION_PLAYER_PLAYPAUSE = 229
ACTION_STOP = 13

# Este botão é uma janela de diálogo: enquanto está na tela, ele recebe TUDO que vem
# do controle. Sem a tabela abaixo, avançar/voltar, legenda, áudio e o menu do player
# simplesmente não funcionavam enquanto aparecia "Pular abertura"/"Próximo episódio".
# Cada ação listada é devolvida para a janela do vídeo, que é quem sabe tratá-la.
PASSTHROUGH = {
    11: 'Info',
    14: 'SkipNext',
    15: 'SkipPrevious',
    16: 'FastForward',
    17: 'Rewind',
    19: 'AspectRatio',
    20: 'StepForward',
    21: 'StepBack',
    22: 'BigStepForward',
    23: 'BigStepBack',
    24: 'OSD',
    25: 'ShowSubtitles',
    26: 'NextSubtitle',
    43: 'AnalogSeekForward',
    44: 'AnalogSeekBack',
    56: 'AudioNextLanguage',
    76: 'SmallStepBack',
    88: 'VolumeUp',
    89: 'VolumeDown',
    91: 'Mute',
    98: 'ChapterOrBigStepForward',
    99: 'ChapterOrBigStepBack',
}


class OverlayButton(xbmcgui.WindowXMLDialog):
    """Janela não-modal. O serviço lê .result a cada meio segundo."""

    def __init__(self, *args, **kwargs):
        self.main_label = kwargs.get('main_label', '')
        self.second_label = kwargs.get('second_label', '')
        self.info_label = kwargs.get('info_label', '')
        self.result = None
        self._ready = False

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
        self.result = 'main' if control_id == BTN_MAIN else 'second'

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.result = 'dismiss'
        elif aid in (ACTION_PAUSE, ACTION_PLAYER_PLAYPAUSE):
            xbmc.Player().pause()
        elif aid == ACTION_STOP:
            self.result = 'dismiss'
            xbmc.Player().stop()
        elif aid in PASSTHROUGH:
            # devolve para a tela do vídeo em vez de engolir
            xbmc.executebuiltin('Action(%s,fullscreenvideo)' % PASSTHROUGH[aid])
