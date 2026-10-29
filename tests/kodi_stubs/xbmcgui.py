"""Stub minimo do `xbmcgui`."""


class Window:
    def __init__(self, _id=10000):
        self._props = {}

    def setProperty(self, key, value):
        self._props[key] = value

    def getProperty(self, key):
        return self._props.get(key, '')

    def clearProperty(self, key):
        self._props.pop(key, None)


class WindowXMLDialog(Window):
    def __init__(self, *args, **kwargs):
        super().__init__()


class Dialog:
    def notification(self, *args, **kwargs):
        pass

    def yesno(self, *args, **kwargs):
        return False

    def ok(self, *args, **kwargs):
        return True


class DialogProgress:
    def create(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def iscanceled(self):
        return False

    def close(self):
        pass


class ListItem:
    def __init__(self, label='', label2='', path='', offscreen=False):
        self.label, self.path = label, path
