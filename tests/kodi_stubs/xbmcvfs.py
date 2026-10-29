"""Stub minimo do `xbmcvfs`: 'special://profile/' vira uma pasta temporaria."""
import os

PROFILE_ROOT = os.environ.get('ARK_TEST_PROFILE', '')


def translatePath(path):
    if path.startswith('special://profile/'):
        return os.path.join(PROFILE_ROOT, *path[len('special://profile/'):].split('/'))
    return path


def exists(path):
    return os.path.exists(path)


def listdir(path):
    dirs, files = [], []
    for nome in os.listdir(path):
        (dirs if os.path.isdir(os.path.join(path, nome)) else files).append(nome)
    return dirs, files


def mkdirs(path):
    os.makedirs(path, exist_ok=True)
    return True


def rename(src, dst):
    os.rename(src, dst)
    return True
