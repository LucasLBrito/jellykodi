# -*- coding: utf-8 -*-
"""A única porta de saída do Ark para a rede.

Tudo aqui é stdlib: o addon depende só de `xbmc.python` e não vai ganhar um
`script.module.requests` por causa de três consultas de título.

Regra desta casa: nada levanta exceção crua para cima. São três, e cada uma quer um
tratamento diferente de quem chama — offline é silêncio, recusado é tentar outra fonte,
ocupado é deixar para depois.
"""
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

import xbmc

from resources.lib import jk_common as C

UA = 'Ark/%s (addon de Kodi; +https://github.com/LucasLBrito/ark)' % (
    C.ADDON.getAddonInfo('version') or '1.9.0')

PADRAO = {
    'User-Agent': UA,
    'Accept': 'application/json',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.5',
}


class SemRede(Exception):
    """Sem internet. Não é culpa do servidor e não melhora repetindo agora."""


class Recusado(Exception):
    """4xx: o pedido está errado ou o conteúdo não existe. Tente outra fonte."""


class Ocupado(Exception):
    """429/5xx: o servidor pediu calma."""


# host -> instante a partir do qual vale tentar de novo
_CASTIGO = {}


def _host(url):
    try:
        return urllib.parse.urlsplit(url).netloc.lower()
    except Exception:
        return url


def de_castigo(url):
    """Quanto falta para este host sair do castigo (0 = pode tentar)."""
    falta = _CASTIGO.get(_host(url), 0) - time.time()
    return int(falta) if falta > 0 else 0


def _castigar(url, segundos):
    """Guarda o host de lado por um tempo.

    É isto que impede o serviço, que acorda a cada 15 s, de metralhar um servidor que
    já respondeu 429: a chamada seguinte nem abre socket.
    """
    _CASTIGO[_host(url)] = time.time() + max(segundos, 30)


def _abrir(req, timeout):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        corpo = b''
        try:
            corpo = exc.read()
        except Exception:
            pass
        return exc.code, corpo, exc
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise SemRede(str(exc))


def _pedir(url, dados=None, headers=None, timeout=12, tentativas=2):
    """Devolve bytes. `dados` não-nulo vira POST."""
    if de_castigo(url):
        raise Ocupado('%s está de castigo por %ds' % (_host(url), de_castigo(url)))

    cab = dict(PADRAO)
    cab.update(headers or {})
    req = urllib.request.Request(url, data=dados, headers=cab,
                                 method='POST' if dados is not None else 'GET')

    ultimo = None
    for volta in range(max(tentativas, 1)):
        resposta = _abrir(req, timeout)
        if len(resposta) == 2:
            return resposta[1]
        codigo, corpo, exc = resposta
        if codigo in (429, 500, 502, 503, 504):
            espera = 0
            try:
                espera = int(exc.headers.get('Retry-After') or 0)
            except Exception:
                espera = 0
            if volta + 1 < tentativas and codigo != 429:
                xbmc.sleep(800 * (volta + 1))
                ultimo = exc
                continue
            _castigar(url, espera or 120)
            raise Ocupado('%s respondeu %d' % (_host(url), codigo))
        raise Recusado('%s respondeu %d: %s' % (_host(url), codigo,
                                                (corpo or b'')[:200].decode('utf-8', 'replace')))
    raise Ocupado('%s não respondeu (%s)' % (_host(url), ultimo))


def get_json(url, params=None, headers=None, timeout=12, tentativas=2):
    if params:
        url = '%s%s%s' % (url, '&' if '?' in url else '?',
                          urllib.parse.urlencode(params))
    bruto = _pedir(url, None, headers, timeout, tentativas)
    try:
        return json.loads(bruto.decode('utf-8', 'replace'))
    except Exception as exc:
        raise Recusado('resposta não é JSON: %s' % exc)


def post_json(url, corpo, headers=None, timeout=30, tentativas=1):
    cab = {'Content-Type': 'application/json'}
    cab.update(headers or {})
    dados = json.dumps(corpo, ensure_ascii=False).encode('utf-8')
    bruto = _pedir(url, dados, cab, timeout, tentativas)
    try:
        return json.loads(bruto.decode('utf-8', 'replace'))
    except Exception as exc:
        raise Recusado('resposta não é JSON: %s' % exc)


def baixar(url, destino, timeout=30, max_bytes=16 * 1024 * 1024):
    """Baixa um arquivo (pôster, fanart) para `destino`. True se deu certo.

    Lê em pedaços e desiste se passar do teto: um pôster de 200 MB não existe, mas um
    redirecionamento para o lugar errado sim. Grava num .parcial e só então renomeia,
    para nunca deixar um JPG pela metade onde o Kodi vai procurar arte.
    """
    if de_castigo(url):
        return False
    tmp = destino + '.parcial'
    try:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'image/*'})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, 'wb') as fh:
            lido = 0
            while True:
                pedaco = resp.read(64 * 1024)
                if not pedaco:
                    break
                lido += len(pedaco)
                if lido > max_bytes:
                    raise OSError('arquivo grande demais (%d bytes)' % lido)
                fh.write(pedaco)
        if not lido:
            raise OSError('veio vazio')
        os.replace(tmp, destino)
        return True
    except Exception as exc:
        C.log('não baixei %s: %s' % (url, exc), xbmc.LOGWARNING)
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False
