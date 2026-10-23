# JellyKodi

Uma "Netflix" para os seus arquivos de vídeo, em português, feita para usar no **controle**.

É o [Kodi](https://kodi.tv) oficial com uma skin e um add-on por cima. Você aponta uma pasta
com seus MKV/MP4 e ele vira uma tela inicial com capas, sinopses, "Continuar assistindo",
"Pular abertura" e "Próximo episódio" — sem servidor, sem conta, sem mensalidade.

> **Não contém nenhum filme ou série.** Ele organiza e exibe os arquivos que já são seus.

---

## O que ele faz

**Tela inicial estilo Netflix** — destaque grande no topo e fileiras: Continuar assistindo,
Por tema, Adicionados recentemente, Filmes, Séries, Suas pastas.

**Organiza sozinho.** Arraste a pasta baixada para o Downloads e pronto: uns 30 segundos
depois cada episódio está em `Série › Season 01 › Série S01E01.mkv`.
- Entra nas subpastas, por mais fundo que esteja
- Se os arquivos forem só `01.mkv, 02.mkv`, usa o **nome da pasta** como nome da série
- Reconhece `Season 2`, `Temporada 2`, `Livro 2`
- Leva a legenda (`.srt`, `.ass`) junto, renomeada igual ao vídeo
- **Não toca em download pela metade** — espera o arquivo parar de crescer
- **Não mexe em nada enquanto você está assistindo**
- Tudo fica registrado: um `Desfazer organizacao.bat` devolve os arquivos

**Pular abertura e próximo episódio**, estilo Netflix. Usa os capítulos do MKV quando existem;
quando não existem, você marca a abertura uma vez no controle (L3) e vale para a pasta inteira.

**Capas e sinopses em português**, do TMDb, pelos buscadores oficiais do Kodi.

**Feito para controle.** Xbox, 8BitDo, PlayStation e Steam Deck. Menu do player com uma fileira
só de botões grandes, cada um com o nome em português — sem os botões de TV a cabo e teletexto
que vêm no Kodi padrão.

---

## Instalar (Windows)

Baixe o `.zip` da página de [**Releases**](../../releases), extraia e dê dois cliques em
`INSTALAR JellyKodi.bat`.

Ele instala em `C:\Kodi`, cria as pastas `Series` e `Filmes`, põe um atalho na Área de
Trabalho e abre. **Não mexe** em um Kodi que você já tenha instalado.

Para atualizar, é só rodar o instalador da versão nova: suas configurações, histórico e
biblioteca continuam.

O `LEIA-ME.txt` dentro do pacote explica tudo em detalhe, incluindo os botões do controle.

---

## Instalar só os add-ons (se você já usa Kodi)

Se você já tem Kodi 21 "Omega" e não quer o pacote inteiro, copie para a pasta de add-ons:

```
skin.jellykodi/           → addons/skin.jellykodi/
plugin.video.jellykodi/   → addons/plugin.video.jellykodi/
userdata/keymaps/jellykodi-controle.xml → userdata/keymaps/
```

Depois: Configurações → Interface → Skin → **JellyKodi**.

---

## Como fica

![Tela inicial do JellyKodi](instalador/Como%20fica%20(exemplo).png)

---

## O que tem neste repositório

| Pasta | O que é |
|---|---|
| `skin.jellykodi/` | A skin (derivada da Estuary) |
| `plugin.video.jellykodi/` | O add-on: organizador, pular abertura, próximo episódio, fileiras da tela inicial |
| `userdata/keymaps/` | O mapeamento do controle |
| `instalador/` | O instalador para Windows e o LEIA-ME do usuário |
| `docs/` | Notas de desenvolvimento |

O `.zip` pronto **não** fica no repositório — ele vai nas *Releases*, porque carrega o Kodi
inteiro (~90 MB).

---

## Requisitos

- Windows 10 ou 11, 64 bits (o pacote); a skin e o add-on funcionam em qualquer Kodi 21
- Internet só para baixar capas e sinopses
- Um controle ajuda, mas funciona com teclado e mouse também

---

## Licença e créditos

GPL-2.0-or-later. A skin é derivada da **Estuary** (phil65 / Team Kodi) e mantém
CC BY-SA 4.0 na arte e GPL-2.0 no código.

Os detalhes e os créditos completos estão em [NOTICE.md](NOTICE.md). Leia antes de
redistribuir.
