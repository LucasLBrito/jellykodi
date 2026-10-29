# -*- coding: utf-8 -*-
"""Modelo de linguagem rodando na própria máquina, para nome que nenhuma busca alcança.

Fala o dialeto da API da OpenAI (`POST /chat/completions`), que é o que **Ollama**,
**LM Studio**, **llama.cpp server** e **vLLM** todos servem. Então não há código
específico de nenhum deles: basta o usuário apontar o endereço nos ajustes.

Padrão: `http://localhost:11434/v1` (Ollama). No LM Studio costuma ser
`http://localhost:1234/v1`.

Nada de chave, nada de custo, nada sai da máquina. Em troca, **pesa**: um modelo de 7B
leva de alguns segundos a mais de um minuto por consulta, dependendo da placa. Por isso:
desligado por padrão, teto de consultas por execução, e só é chamado quando o AniList e
o TMDB já falharam — nunca pelo serviço em segundo plano, só com o usuário na frente
olhando a tela de carregamento.

O modelo local não navega na internet. Quem pesquisa de verdade são o AniList e o TMDB
em jk_lookup; aqui o modelo só serve para transformar
"[Grupo] Kmetsu.no.Yaba.S2.RAW.x265" em "Kimetsu no Yaiba", um palpite que volta para a
base confirmar. Palpite sem confirmação nunca entra como certeza.
"""
import json
import re

import xbmc

from resources.lib import jk_common as C
from resources.lib import jk_net as N

PADRAO_URL = 'http://localhost:11434/v1'

# Quantas consultas no máximo por execução; o resto fica para os não identificados
TETO_PADRAO = 12

INSTRUCAO = (
    'Você identifica anime, séries e filmes a partir de nomes de arquivo de download.\n'
    'Responda SÓ com um objeto JSON, sem comentário e sem cercadura de código:\n'
    '{"titulo": "...", "ano": "AAAA" ou null, '
    '"tipo": "serie" ou "filme" ou "desconhecido", "certeza": 0 a 100}\n'
    'Use o título oficial em inglês ou o romaji, nunca em japonês escrito em kanji.\n'
    'Se não reconhecer, devolva tipo "desconhecido" e certeza 0. Não invente.'
)

# quantas chamadas já foram feitas nesta execução do plugin
_gastas = 0


def base_url():
    return (C.setting_string('llm_url', PADRAO_URL) or PADRAO_URL).rstrip('/')


def modelo():
    return C.setting_string('llm_model', '')


def teto():
    return C.setting_int('llm_teto', TETO_PADRAO) or TETO_PADRAO


def disponivel():
    """Ligado nos ajustes, com modelo escolhido, e ainda dentro do teto."""
    if not C.setting_bool('llm_on', False):
        return False
    if not modelo():
        C.log('modelo de linguagem ligado mas sem modelo escolhido nos ajustes',
              xbmc.LOGWARNING)
        return False
    return _gastas < teto()


def zerar():
    """Zera o contador. Chamado uma vez por abertura da tela de organizar."""
    global _gastas
    _gastas = 0


def gastas():
    return _gastas


def modelos():
    """O que o servidor local tem instalado. [] se não houver servidor no ar.

    É o que a ação "Testar modelo local" usa para o usuário escolher de uma lista em
    vez de digitar o nome do modelo na mão e errar.
    """
    try:
        res = N.get_json(base_url() + '/models', timeout=6, tentativas=1)
    except N.SemRede:
        return []
    except (N.Recusado, N.Ocupado) as exc:
        C.log('servidor de modelo local: %s' % exc, xbmc.LOGWARNING)
        return []
    nomes = []
    for m in (res.get('data') or res.get('models') or []):
        nome = m.get('id') or m.get('name') if isinstance(m, dict) else m
        if nome:
            nomes.append(str(nome))
    return sorted(set(nomes))


def _so_json(texto):
    """Arranca o objeto JSON de uma resposta que pode vir com conversa em volta."""
    texto = (texto or '').strip()
    texto = re.sub(r'^```(?:json)?\s*|\s*```$', '', texto, flags=re.I | re.M)
    try:
        return json.loads(texto)
    except Exception:
        pass
    inicio, fim = texto.find('{'), texto.rfind('}')
    if inicio >= 0 and fim > inicio:
        try:
            return json.loads(texto[inicio:fim + 1])
        except Exception:
            pass
    return None


def _perguntar(pergunta, timeout):
    corpo = {
        'model': modelo(),
        'messages': [{'role': 'system', 'content': INSTRUCAO},
                     {'role': 'user', 'content': pergunta}],
        'temperature': 0,                     # identificação não quer criatividade
        'max_tokens': 200,
        'stream': False,
        # Ollama e LM Studio honram isto; quem ignorar cai no _so_json
        'response_format': {'type': 'json_object'},
    }
    res = N.post_json(base_url() + '/chat/completions', corpo,
                      timeout=timeout, tentativas=1)
    escolhas = res.get('choices') or []
    if not escolhas:
        return None
    return _so_json(((escolhas[0].get('message') or {}).get('content')) or '')


def adivinhar(grupo, timeout=None):
    """Palpite de título para um grupo. None quando não dá ou não reconheceu.

    Manda só nomes de arquivo e de pasta — nunca o caminho completo do disco.
    """
    global _gastas
    if not disponivel():
        return None

    chave = C.cache_load('llm').get(grupo.chave)
    if isinstance(chave, dict):                       # resposta já paga em CPU
        return chave.get('v')

    exemplos = [i.nome for i in grupo.itens[:4]]
    pastas = sorted({p.rsplit('\\', 1)[-1].rsplit('/', 1)[-1] for p in grupo.pastas})
    pergunta = ('Nome da pasta: %s\nArquivos:\n%s' %
                (', '.join(pastas) or '(solto)', '\n'.join('- ' + e for e in exemplos)))

    _gastas += 1
    try:
        dados = _perguntar(pergunta, timeout or C.setting_int('llm_timeout', 120) or 120)
    except N.SemRede:
        C.log('não achei o servidor de modelo local em %s' % base_url(), xbmc.LOGWARNING)
        return None
    except (N.Recusado, N.Ocupado) as exc:
        C.log('modelo local: %s' % exc, xbmc.LOGWARNING)
        return None
    except Exception as exc:
        C.log('modelo local falhou: %s' % exc, xbmc.LOGWARNING)
        return None

    palpite = None
    if isinstance(dados, dict):
        titulo = (dados.get('titulo') or '').strip()
        certeza = dados.get('certeza')
        tipo = (dados.get('tipo') or '').strip().lower()
        if titulo and tipo != 'desconhecido' and (certeza is None or float(certeza) >= 40):
            ano = str(dados.get('ano') or '').strip() or None
            palpite = {'titulo': titulo,
                       'ano': ano if ano and re.match(r'^(19|20)\d{2}$', ano) else None,
                       'tipo': tipo if tipo in ('serie', 'filme') else None}

    C.cache_put('llm', grupo.chave, palpite)          # guarda inclusive o "não sei"
    return palpite
