# Segurança

## Como avisar sobre uma falha

Achou algo que pode prejudicar quem usa o Ark — por exemplo, um nome de arquivo que faz o
organizador mover ou apagar algo fora das pastas dele, ou um jeito de executar código pela
pesquisa de títulos? **Não abra uma issue pública.**

Use o [aviso privado de vulnerabilidade do GitHub](https://github.com/LucasLBrito/jellykodi/security/advisories/new)
(aba *Security → Report a vulnerability*). Inclua, se puder, os passos para reproduzir e a
versão do Ark.

Você recebe uma resposta em até 7 dias.

## O que o Ark faz por conta própria

Para avaliar o risco, vale saber:

- O **organizador automático** só lê e grava nas pastas escolhidas (Downloads, Séries,
  Filmes) e numa pasta `_Nao_Identificado`. Ele nunca apaga vídeo; o padrão é criar um
  *hardlink*.
- O **serviço em segundo plano não pesquisa títulos na internet**. A pesquisa (AniList, TMDb,
  IA local) só acontece na tela Organizar, aberta pela pessoa. Capas e sinopses da biblioteca
  vêm dos buscadores oficiais do Kodi, durante a varredura.
- A **IA local** é opcional, desligada por padrão e fala só com o endereço configurado
  (padrão `http://localhost:11434`).
- A **chave do TMDb** fica nos ajustes do add-on, na máquina da pessoa; nunca no repositório
  nem no Setup.

## Versões cobertas

Só a versão mais recente recebe correções.
