"""Stub minimo do modulo `xbmc` do Kodi, so para rodar os testes fora do Kodi."""
LOGDEBUG, LOGINFO, LOGWARNING, LOGERROR, LOGFATAL = 0, 1, 2, 3, 4

LOGS = []


def log(msg, level=LOGDEBUG):
    LOGS.append((level, msg))


def getInfoLabel(_label):
    return '21.3 (21.3.0) Git:stub'


def getCondVisibility(_cond):
    return False


def executebuiltin(_cmd, _wait=False):
    pass


def executeJSONRPC(_req):
    return '{"jsonrpc": "2.0", "id": 1, "result": {}}'


def sleep(_ms):
    pass


class Monitor:
    def abortRequested(self):
        return False

    def waitForAbort(self, _timeout=0):
        return False


class Player:
    def isPlaying(self):
        return False

    def isPlayingVideo(self):
        return False
