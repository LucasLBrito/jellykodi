# Créditos e licenças

O Ark é software livre e **só existe por cima do trabalho de outras pessoas**.

## Kodi
O programa em si é o [Kodi](https://kodi.tv) (Team Kodi), GPL-2.0-or-later.
Código-fonte: <https://github.com/xbmc/xbmc>.

O Setup distribui o **Kodi 21.3 "Omega" oficial**, baixado de `mirrors.kodi.tv` com o
SHA-256 conferido (veja `instalador/montar.ps1`). A única alteração é uma lista: o arquivo
`system/addon-manifest.xml` ganha as linhas `skin.ark`, `plugin.video.ark` e
`resource.language.pt_br`, para o Kodi tratar esses addons como parte do sistema e não os
deixar desativados. Nenhum binário do Kodi é modificado. O código-fonte correspondente é o
da tag `21.3-Omega` em <https://github.com/xbmc/xbmc>.

O Setup também inclui o pacote de idioma **`resource.language.pt_br`** (Team Kodi e
tradutores do Kodi), baixado sem modificação do repositório oficial de addons.

## Estuary
A skin `skin.ark` é **derivada da Estuary**, de phil65 e Ichabod Fletchman (Team Kodi).
- Código: GNU GPL, versão 2.0
- Arte: Creative Commons Attribution-ShareAlike 4.0
- Original: <https://github.com/xbmc/skin.estuary>

Por ser derivada, a `skin.ark` continua sob as mesmas licenças. As fontes da skin mantêm as
próprias licenças (veja `skin.ark/fonts/*license*`).

## Ark
- `plugin.video.ark` (código próprio): GPL-2.0-or-later
- `skin.ark`: CC BY-SA 4.0 (arte) + GPL-2.0 (código), herdadas da Estuary
- Instalador, testes, scripts e o ícone do Ark (gerado por `instalador/arte/gerar_arte.py`):
  GPL-2.0-or-later

## Microsoft Visual C++
O Setup leva o instalador oficial do **Microsoft Visual C++ Redistributable** (x64), sem
modificação e com a assinatura digital da Microsoft conferida, e só o executa quando o
Windows não o tem. É distribuído sob a licença da Microsoft para esse pacote redistribuível.

## Fontes de dados
- **[The Movie Database (TMDb)](https://www.themoviedb.org)**: capas, fundos e sinopses,
  pelos buscadores oficiais do Kodi e, opcionalmente, pela chave do próprio usuário.
  Este produto usa a API do TMDb, mas não é endossado nem certificado pelo TMDb.
- **[AniList](https://anilist.co)**: pesquisa de títulos de anime, pela API pública.

## Capturas de tela
As imagens em `docs/img/` mostram os filmes abertos da [Blender Foundation](https://studio.blender.org/films/)
(Big Buck Bunny, Sintel, Tears of Steel, Sprite Fright e outros), sob CC BY, com arte vinda
do TMDb.

## O que este projeto NÃO contém
Nenhum filme, série, episódio ou legenda. Ele organiza e exibe **os seus arquivos**.
