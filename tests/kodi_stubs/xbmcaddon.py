"""Stub minimo do `xbmcaddon`. Os testes mudam SETTINGS para simular os ajustes."""
SETTINGS = {}


class Addon:
    def __init__(self, addon_id='plugin.video.ark'):
        self._id = addon_id

    def getAddonInfo(self, key):
        return {'id': self._id, 'profile': 'special://profile/addon_data/%s/' % self._id,
                'path': '', 'version': '0.0.0-test', 'name': 'Ark'}.get(key, '')

    def getSetting(self, key):
        return str(SETTINGS.get(key, ''))

    # Os getSetting* tipados do Kodi levantam excecao para ajuste desconhecido;
    # o jk_common conta com isso para cair no valor padrao.
    def getSettingBool(self, key):
        return bool(SETTINGS[key])

    def getSettingInt(self, key):
        return int(SETTINGS[key])

    def getSettingString(self, key):
        return str(SETTINGS[key])

    def setSetting(self, key, value):
        SETTINGS[key] = value

    def getLocalizedString(self, _id):
        return ''
