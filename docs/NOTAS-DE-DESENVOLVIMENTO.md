# JellyKodi — contexto para Claude Code

Kodi 21.3 "Omega" **portátil** (Windows) personalizado estilo Netflix/Jellyfin, em pt-BR, feito para controle (Xbox/8BitDo/Steam). Dono: Lucas (fala português; responder em PT-BR, linguagem simples). Sempre **testar todas as navegações** depois de mudar algo.

## Onde está cada coisa
- Fonte (este zip): `skin.jellykodi/` (v1.6.0), `plugin.video.jellykodi/` (v1.6.0), `userdata/keymaps/jellykodi-controle.xml`.
- PC do Lucas (instalado):
  - Programa: `C:\Kodi\JellyKodi-Portatil\Kodi\kodi.exe -p` (dados em `...\Kodi\portable_data\`; log em `portable_data\kodi.log`)
  - Addons instalados: `...\Kodi\addons\skin.jellykodi` e `...\Kodi\addons\plugin.video.jellykodi` (verificar; podem estar em `portable_data\addons`)
  - Vídeos: `C:\Kodi\Series` (Madoka 12 eps; A Lenda de Korra S01E01-06), `C:\Kodi\Filmes\Puella Magi Madoka Magica\` (Rebellion + Concept Movie; `.nfo` com https://www.themoviedb.org/movie/212162)
  - Downloads ainda com Korra S01E07-12 e S02E01-07 (usar "Organizar Downloads")
  - Pasta Documentos é do OneDrive → manter tudo FORA dele.
- Pacote para amigos: `JellyKodi-v1.6-para-amigos.zip` (~95 MB) = `INSTALAR JellyKodi.bat` + `app/instalar.ps1` (instala em C:\Kodi, robocopy sem sobrescrever portable_data, cria Series/Filmes, escreve sources.xml se não existir, atalho na Área de Trabalho) + `app/Kodi` + `app/Extras/vc_redist_x64.exe` + `LEIA-ME.txt`.

## Deploy de mudanças
Copiar as pastas do addon/skin por cima das instaladas e reiniciar o Kodi (ou `ReloadSkin()` para XML). Fechar o Kodi antes de mexer no banco `portable_data/userdata/Database/MyVideos*.db`.

## Skin (derivada da Estuary)
- `colors/defaults.xml`: paleta Netflix (foco FFE50914, fundo FF141414).
- `xml/Home.xml`: menu topo 9000 (Início, Séries, Filmes, Pastas, Pesquisar); menu direita 9100 (Atualizar, Monitor, Otimizar, Config, Desligar); hero 301 Assistir / 302 Mais informações; grouplist 500 de fileiras:
  5100 Continuar assistindo · 5150 Por tema · 5050 "Adicionar e organizar" (itens estáticos → `RunPlugin(plugin://plugin.video.jellykodi/?action=organize|open_folder&which=series|filmes|update|help)`) · 5200 Recentes · 5300 Filmes · 5400 Séries · 5500 Suas pastas.
- `xml/Includes_JellyKodi.xml`: variáveis JKHero* (por `Window(home).Property(jk_hero)`), includes JKCard, JKToolCard, JKRow.
- Monitor ultrawide 21:9 (2560 de largura): usar âncoras `left/right/bottom`, nunca largura fixa 1920.
- Ícones em `media/jk/` (PNG 256x256 RGBA: ic_organize, ic_series, ic_filmes, ic_refresh, ic_help).

## Addon `plugin.video.jellykodi` (pluginsource + service)
- `service.py`: pular abertura/recap (capítulos do MKV ou marcação L3/F9 por pasta), créditos/próximo episódio com contagem, histórico; a cada 120 s `auto_metadata` (selectaction=2 = retomar sem perguntar; TMDb pt-BR; auto_configure; refresh se precisar).
- `plugin.py` actions: continue, recent, play, forget, monitor, optimize, update, themes/theme (Por tema), rescrape, organize (`_plan_move`: SxxEyy, NxNN, "Nome - 01", ano), open_folder, help. `_roots()` acha pastas Séries/Filmes pelo **rótulo** da fonte (contém "serie"/"filme").
- `resources/lib/jk_meta.py`: grava direto na tabela `path` do banco (strContent, strScraper, scanRecursive, useFolderNames, **strSettings com pt-BR**, senão vem em inglês); `ensure_ptbr` para todas as fontes; `refresh_all_ptbr`; scrapers `metadata.themoviedb.org.python` / `metadata.tvshows.themoviedb.org.python`.
- `resources/lib/jk_common.py`: estado em `special://profile/addon_data/plugin.video.jellykodi/state.json` (load_state/save_state), helpers de vídeo/caminho.
- Keymap: View → capítulos; L3/R3/F9/F10 → NotifyAll(jellykodi, mark_intro/mark_credits/clear_marks); F8 capítulos.

## Armadilhas conhecidas
- Kodi recusa VideoLibrary.Clean durante um scan → esperar o scan acabar.
- Miniaturas `image://video@` travam → deixar desligado.
- Não existe JSON-RPC para adicionar fonte; sources.xml só é lido na inicialização.
- Scan completo (`VideoLibrary.Scan` sem diretório) usa os caminhos com conteúdo no banco, não o sources.xml.

## Pendências
1. **(EM ANDAMENTO) Escolher pastas de Séries/Filmes/Downloads pelo app.** Plano:
   - Nova action `folders` + item "Escolher pastas" na fileira 5050 (ícone novo `ic_folder.png`).
   - Diálogo: "Pasta de Séries: X", "Pasta de Filmes: Y", "Pasta de onde organizar (Downloads): Z"; `xbmcgui.Dialog().browse(0, ...)` para escolher (permite criar pasta nova).
   - Guardar em state.json (`folders: {series, filmes, downloads}`); `_roots()`, `organize_downloads`, `open_folder`, `show_help` e `auto_configure` passam a usar isso primeiro (fallback: rótulos das fontes).
   - Ao trocar: `M.set_content(nova, 'tvshows'|'movies')` + `VideoLibrary.Scan(directory=nova)`; perguntar se move os vídeos da pasta antiga (DialogProgress; mesmo disco = instantâneo) e depois `VideoLibrary.Clean`.
   - Atualizar `portable_data/userdata/sources.xml` (trocar o caminho da fonte Séries/Filmes) para a aba "Pastas" refletir após reiniciar.
   - Avisar se a pasta escolhida estiver dentro do OneDrive; impedir Séries = Filmes.
   - Atualizar LEIA-ME e o zip dos amigos (v1.7).
2. Conferir no banco se as sinopses ficaram em pt-BR e se Rebellion foi identificado certo (TMDb 212162).
3. Organizar os episódios novos de Korra que estão em Downloads.
4. Amigo: mandar o zip por link (OneDrive/Google Drive) ou WhatsApp como Documento — e-mail bloqueia zip com programa.

## Ponto de situação — v1.7 (22/10/2026, em andamento)

Plano completo em `C:\Users\LUCAS\.claude\plans\ola-estou-app-de-purrfect-whale.md` (aprovado).
Backup do `portable_data/userdata` e da fonte antes das mudanças: pasta `scratchpad` da sessão.

### Diagnóstico confirmado nesta máquina
- Código instalado em `C:\Kodi\JellyKodi-Portatil\Kodi\addons\` é **idêntico** ao da fonte; só o número de versão (diz 1.5.0) e os 5 PNGs de `media/jk/` estão velhos.
- Da Estuary, só 5 arquivos são realmente nossos: `Home.xml`, `Includes_JellyKodi.xml`, `Includes.xml` (1 linha), `Startup.xml`, `View_54_InfoWall.xml`. **Todo XML de player/OSD é Estuary puro** — é de lá que vem o OSD cheio de botões de TV/PVR.
- **Foco pula sozinho na Home:** `JKRow` esconde a fileira quando ela fica vazia (`NumItems>0 | IsUpdating`), e o Kodi joga o foco no `defaultcontrol always="true" 301`. Piora porque `service.py` muda `jk_refresh` a cada `VideoLibrary.OnUpdate` (um por item num scan) e as 3 fileiras de plugin recarregam embaixo do cursor.
- **Voltar vira "ir pra Home" em tudo:** `<back>ActivateWindow(Home)</back>` está no `<global>` do keymap e só `FullscreenVideo` sobrescreve.
- **Controle morre no player:** `OverlayButton` (`jk_dialog.py`) é `WindowXMLDialog` com `.show()`, rouba o foco e o `onAction` só trata Back/Pause/Stop — seek, OSD, legenda e áudio são engolidos. O log confirma: `ignoring action ... closing animation is running`.
- **Home parece vazia:** `scan_recent` corta em `found[:40]`, `max_depth=3`, `count>=20` por fileira, 1 card por pasta, cache de 15 min, e "Por tema" esconde grupo com menos de 2 títulos. Cada card custa um `Files.GetFileDetails` (N+1).
- `videoplayer.seekdelay=750` (←/→ demora); `extractthumb`/`extractchapterthumbs` ligados; sem `advancedsettings.xml`.

### Como testar navegação sem controle na mão
Com o Kodi fechado, ligar `services.webserver` no `guisettings.xml`; abrir o Kodi e usar JSON-RPC por `curl`:
`Input.Down/Up/Left/Right/Select/Back` para andar e `XBMC.GetInfoLabels` com `System.CurrentWindow`,
`System.CurrentControlId` e `Container(5100..5500).NumItems` para provar onde o foco parou e quantos
cards cada fileira trouxe. `TakeScreenshot` para conferir o visual. **Desligar o webserver no fim.**

### O que já foi feito (v1.7.0, testado nesta máquina em 23/10/2026)

**Navegação da Home**
- `JKRow` (`Includes_JellyKodi.xml`): a fileira não some mais enquanto está com o foco
  (`| Control.HasFocus(...)` na condição), ganhou `<onback>301</onback>`, `<onleft>9000</onleft>`
  e `limit` 25 → 40.
- `Home.xml`: `defaultcontrol` sem `always="true"`; fileiras começam em `top 600` (cabe mais de uma
  na tela); menu de cima dá a volta (9000 ⇄ 9100); as 15 linhas de `onclick` dos botões 301/302
  viraram 3, usando a variável nova `JKHeroRow` + expressão `jk_any_row`.
- `service.py`: `onNotification` só anota `pending_bump`; o laço recarrega as fileiras **uma vez**,
  5 s depois do último `OnUpdate` e fora de scan. As fileiras pararam de piscar durante a navegação.
- `plugin.py`: `endOfDirectory(cacheToDisc=True)` nas fileiras.

**Keymap** — `back` global virou `Back` de verdade; segurar 800 ms é que vai pra Home. Seção `<Home>`
com `back` inerte, LT/RT = início/fim da lista, Start = volta pro vídeo. No vídeo: ↑ = info/barra,
↓ = OSD (capítulos saíram do direcional; continuam no View/F8).

**Player**
- `jk_dialog.py`: tabela `PASSTHROUGH` devolve 22 ações (seek, OSD, legenda, áudio, volume…) para a
  janela do vídeo com `Action(<nome>,fullscreenvideo)`. Antes o overlay engolia tudo menos A e B.
- Overlay sem animação de fechamento (era ela que gerava `ignoring action`; agora o log zera).
- `VideoOSD.xml` reescrito: uma fileira centralizada de 9 botões (anterior, −10s, play/pause, +10s,
  próximo, legendas, áudio, capítulos, parar) com o nome em pt-BR por cima (`JKOSDHelp`).
  Saiu tudo de PVR/DVD/teletexto. ↑ foca a barra de progresso, ↓ fecha.
- `videoplayer.seekdelay` 750 → 0, aplicado sozinho pelo serviço (`player_defaults_v17` no state).

**Carregamento**
- `jk_meta.library_index()`: 2 consultas no lugar de 1 `Files.GetFileDetails` por card.
  **Atenção:** episódio não aceita `year` nem `genre` (usa `firstaired`) — pedir isso faz o Kodi
  recusar a consulta inteira e os cards ficam sem capa/sinopse. Por isso há `EPISODE_FIELDS` e
  `MOVIE_FIELDS` separados.
- `addDirectoryItems` em lote; `kodi_major()` em cache.
- Limites: `found[:40]`→400, `max_depth` 3→5, `count>=20`→40, cache de recentes 15→5 min.
- `list_continue`: o `seen_folders.add` saiu de antes dos testes — era isso que sumia com a série
  inteira quando o item mais novo era arquivo apagado ou último episódio. "Continuar assistindo"
  foi de 1 para 3 cards.
- `next_video` emenda na temporada seguinte (`_first_of_next_season`).
- `_finish_wall` só chama `Container.SetViewMode(500)` se a janela Vídeos estiver aberta.
- `ensure_ptbr` só roda uma vez por pasta (`ptbr_sources` no state); "Atualizar" reaplica.
  `refresh_all_ptbr` com `xbmc.sleep(250)` entre os pedidos.

**Escolher pastas** (fecha a pendência 1) — action `folders`, card novo na fileira 5050 com
`media/jk/ic_folder.png`. Diálogo "Onde ficam seus vídeos" com Séries/Filmes/Downloads, `browse`,
aviso de OneDrive, impede Séries = Filmes, grava em `state['folders']`. Ao trocar: `set_content` +
`_write_source` (reescreve `sources.xml` com ElementTree) + pergunta se move os vídeos
(`_move_videos`, `xbmcvfs.rename` com cópia como reserva) + `scan` + `Clean`.
`_roots()`/`_downloads_root()` leem o state primeiro e caem no rótulo da fonte como reserva.

**Não testado de ponta a ponta:** a troca de pasta de verdade (`_write_source` + `set_content` +
mover) — exigiria repontar as fontes reais do Lucas. O diálogo, o salvar e a leitura das pastas
atuais foram testados.

**Ainda aberto:** sinopses e títulos continuam em inglês/japonês (pendência 2) — o `strSettings`
pt-BR está gravado, mas a biblioteca precisa de um `refresh_all_ptbr` que funcione; conferir.

### Revisão do algoritmo das capas (23/10/2026)

Ordem que decide a imagem do card: `add_video` monta a arte a partir do índice da biblioteca →
`JKCardArt` escolhe o que desenhar → `C.art_for()` só entra quando não veio nada da internet.

Defeitos encontrados e corrigidos:
1. **Pôster entrava como `landscape`.** `art_for` fazia `thumb = landscape = fanart or poster`.
   O card é deitado (340x191) com `aspectratio=scale`, então um pôster em pé era cortado numa
   faixa do meio. Agora só `fanart` vira landscape; o pôster fica na chave `poster`.
2. **Imagem solta na pasta era ignorada em série.** O episódio está em `Série/Season 01/` e o
   `poster.jpg`/`fanart.jpg` quase sempre em `Série/`. `folder_art` agora olha a pasta de cima
   quando a atual é uma temporada (`SEASON_RE`), com a pasta do episódio tendo prioridade.
3. **`poster_folder`** era uma chave inventada que nenhuma parte da skin lia — virou `poster`.
4. **`JKCardArt` não tinha pôster como reserva:** item só com pôster virava card cinza.
   Agora a ordem é landscape → fanart → thumb (ignorando `Default*`) → poster, e
   `jk_card_has_art` inclui pôster.
5. **`art_for` batia no disco por card** (até 8 `xbmcvfs.exists` por pasta) mesmo quando a
   biblioteca já tinha a arte. Agora só roda se não veio landscape/fanart/thumb.
6. `myvideos.extractthumb` e `extractchapterthumbs` estavam **ligados** e geravam miniaturas
   `image://video@...mkv` (o filme Concept Movie tinha uma). O serviço desliga as duas nos
   padrões (`player_defaults_v17b`). Entradas antigas no banco só somem num refresh.

Auditoria das fileiras depois: 5100/5150/5200/5300/5400 com landscape+fanart+poster do TMDb;
5500 ("Suas pastas") não tem arte nenhuma — são fontes, mostram `DefaultHardDisk.png` no card.

Também corrigido: os ícones ▶ e ℹ do destaque ficaram 40 px abaixo dos botões quando a fileira
301/302 subiu de `top 306` para `266`; foram de `top 324` para `284`.

### pt-BR RESOLVIDO (23/10/2026) — causa raiz

O buscador **metadata.tvshows.themoviedb.org.python 1.7+** (o ativo está em
`portable_data/addons/`, não o antigo de `Kodi/addons/`) **renomeou o ajuste de idioma**:
quem decide título e sinopse agora é `languageDetails` (e `languageImages`); o `language`
antigo nem existe mais nesse scraper. O JellyKodi só gravava `language`, então o Kodi pedia
`language=en-US` ao TMDb e tudo vinha em inglês. O de **filmes** ainda usa `language`.

Como foi provado: `debug.showloginfo=true` + `VideoLibrary.RefreshEpisode` e depois
`grep "api.themoviedb.org"` no log — a URL saía com `language=en-US` mesmo com `pt-BR` no
`pathSettings`. Depois da correção saem 7 chamadas `language=pt-BR`.

Corrigido em três lugares de `jk_meta.py`:
- `PTBR_SETTINGS` agora grava `language`, `languageDetails`, `languageImages` e `tmdbcertcountry`.
- `scrapers_to_portuguese` escreve as quatro chaves (pula a que o buscador não tiver, porque
  `getSetting` devolve '' nesse caso), marca `scrapers_ptbr_v2` e liga `needs_ptbr_refresh`.
- `ensure_ptbr` compara `strSettings<>?` com o texto inteiro em vez de procurar `%pt-BR%`,
  senão uma mudança futura nos ajustes passa batido. Estado versionado: `ptbr_sources_v2`.

Resultado: 18 episódios com título e sinopse em pt-BR ("Bem-Vindo a Cidade da República",
"Uma Folha no Vento"...), sinopse do Rebellion em pt-BR. O que **continua** em japonês/inglês é
limitação do TMDb: `movie/418189` (Concept Movie) tem `overview` vazio e título japonês mesmo
pedindo pt-BR, e o nome da série Korra é "The Legend of Korra" no próprio catálogo pt-BR.

### Mais telas e fluxos (23/10/2026)

- **Séries / Filmes / Pastas** são as telas padrão da Estuary (parede de pôsteres, lista larga).
  Funcionam, mas não têm a cara da Home.
- **O item `..` roubava o foco** em toda lista: ao abrir Séries o foco caía em "voltar", e apertar
  A saía da tela. Como o Voltar do controle já funciona, o serviço agora desliga
  `filelists.showparentdiritems` e liga `videolibrary.tvshowsselectfirstunwatcheditem=2`
  (`player_defaults_v17c`). Agora Séries abre no primeiro título e a série abre no próximo
  episódio não assistido.
- **"Suas pastas" mostra pendrives** (ESD-USB, KINGSTON) porque `sources://video/` inclui as
  unidades removíveis — por isso a fileira 5500 tem 4 itens e nenhuma arte. Não resolvido.
- **"Organizar Downloads"** testado até a confirmação: lê os 26 episódios de Korra e planeja
  `A Lenda de Korra › Season 01/02/03 › A Lenda de Korra SxxEyy.mkv`. **Cancelado** — os
  arquivos do Lucas não foram movidos.
- **"Atualizar"** roda Clean + scan mas não dá nenhum retorno visual durante os minutos que leva.
- Caixa da sinopse do destaque voltou para `height 117` (3 linhas inteiras); com 100 cortava a
  terceira linha no meio.

### Korra organizado + biblioteca grande (23/10/2026)

Os 26 episódios saíram do Downloads: `C:\Kodi\Series\A Lenda de Korra\Season 01/02/03`
(12 + 7 + 13), nomes `A Lenda de Korra SxxEyy.mkv`. **Downloads vazio, 44 episódios na
biblioteca.** Todos os novos entraram **direto em pt-BR** ("2x01. Espírito Rebelde",
"3x01. Um Sopro de Ar Puro", "1x07. A Consequência") — a correção do `languageDetails` vale
também para o scan de arquivos novos, não só para refresh.

**Armadilha achada no caminho:** o `multiselect` do Kodi **não desenha visto nenhum** nesta skin
(nem na Estuary — não existe `ListItem.IsSelected` em lugar nenhum do XML delas). Dava para
desmarcar um item sem perceber e o arquivo ficava para trás sem explicação — foi o que aconteceu
com o S01E07 num teste. **Trocado por `Dialog().yesno` com resumo agrupado por série/temporada**
("A Lenda de Korra › Temporada 2: 7 vídeo(s)"), botões "Organizar" / "Agora não" (padrão no não).
Nunca mais usar `multiselect` aqui.

Depois de organizar, as fileiras continuaram certas (5200 foi de 4 para 6 cards) e a navegação
pelas 7 fileiras seguiu sem o foco escapar. Entrar em Séries → Korra agora mostra a tela de
temporadas (Book One/Two/Three) com o foco já na primeira, não em "Todas as temporadas".

**Observação:** uma série com 3 pastas de temporada vira **3 cards** em "Adicionados
recentemente" (o agrupamento de `list_recent` é por pasta, e `Season 01/02/03` são pastas
diferentes). Talvez devesse agrupar pela pasta da série.

## v1.8.0 — Organizador automático (23/10/2026)

Arrastou uma pasta para o Downloads? O JellyKodi organiza **sozinho**, sem apertar nada.

### `resources/lib/jk_organize.py` (novo)
O algoritmo saiu do `plugin.py` para cá porque o **serviço também precisa dele**.
`plugin.py` virou casca: `_roots()`/`_downloads_root()` só chamam `O.roots()`/`O.watch_root()`,
para serviço e plugin nunca discordarem sobre onde as coisas ficam.

**Ordem de confiança do algoritmo** (`plan_folder`, busca recursiva até 4 níveis):
1. `S01E02` / `1x02` no nome do arquivo;
2. `Nome - 02` no arquivo;
3. **nome vem da pasta** — arquivo só com número (`01.mkv`, `Ep 03.mkv`): se a pasta é de
   temporada (`Season 2`, `S02`, `Temporada 2`, `Livro 2`) usa a pasta **de cima** e aquele
   número de temporada; senão usa a pasta imediata, temporada 1;
4. **maioria da pasta** — 2+ arquivos já identificados como a mesma série puxam os ambíguos;
5. filme pelo ano.

Trava: arquivo numa pasta que já virou série **nunca** vira filme — fica onde está (é extra).
É o que impede `01.mkv` de virar um filme chamado "01", e foi testado com `extras.mkv`.

Legendas (`.srt/.ass/...`, inclusive `.pt-BR.srt`) vão junto e são renomeadas igual ao vídeo.

### Organizador automático (`service.py`)
`auto_organize()` roda a cada 15 s, **nunca** com vídeo tocando nem durante scan.
Tira um retrato barato da pasta (`folder_signature`: quantos, tamanho, mtime mais novo);
enquanto o retrato não muda não olha o conteúdo. Mudou → espera o retrato ficar **parado por
`ESPERA_ESTAVEL` (30 s)** antes de mexer. É assim que não se toca em download pela metade.
Desliga pelo ajuste `auto_organize` (padrão ligado).

### Arrumar a biblioteca existente
`plan_tidy` + `tidy_library()`: episódio solto na raiz da série entra na `Season NN`.
Roda **uma vez** (`tidy_v1` no state), pelo botão, com `yesno` antes — são arquivos que já
funcionam. `watched_snapshot()`/`restore_watched()` guardam e devolvem `playcount`,
`lastplayed` e `resume`, porque **o Kodi marca assistido por caminho**: sem isso o Madoka
voltaria para 0/12. `remap_state()` refaz as chaves do `state.json` (history por arquivo,
intros/credits por pasta).

### Desfazer
`C:\Kodi\organizacao-log.csv` é **sobrescrito** a cada organização, de propósito: o
`Desfazer organizacao.bat` devolve tudo que estiver no arquivo, então um log acumulativo
faria um "desfazer" levar organizações antigas junto. O histórico completo fica em
`organizacao-historico.csv`, que ninguém desfaz sozinho.

### Armadilhas descobertas (não repetir)
- **`Dialog().yesno` do Kodi só mostra 4 linhas** e corta as de cima **em silêncio**. Por isso
  o resumo manda no máximo 3 grupos + "... e mais N pasta(s)".
- **Nunca editar o `state.json` com `Set-Content -Encoding UTF8` do PowerShell 5.1**: ele grava
  BOM, o `json.load` falhava e o `save_state` seguinte gravava um estado vazio por cima —
  apagou o histórico uma vez. Use `[System.IO.File]::WriteAllText` com `UTF8Encoding $false`.
  O `load_state` agora lê com `utf-8-sig` e, se o arquivo estiver ilegível, copia para
  `state.json.ruim` e **recusa gravar por cima**.

### Testado nesta máquina (tudo em caixa de areia, biblioteca real intacta)
- Nome pela pasta: `Naruto/01.mkv` → `Naruto/Season 01/Naruto S01E01.mkv`.
- Temporada pela pasta: `One Piece/Season 2/05.mkv` → `One Piece/Season 02/One Piece S02E05.mkv`.
- Legenda junto; `sample.mkv`, `extras.mkv` e `.crdownload` ignorados; filme pelo ano.
- **Automático:** pasta copiada às 11:03:32, organizada às 11:04:06 sem tocar em nada.
- **Download pela metade:** arquivo crescendo por 75 s — nunca movido; parou, organizou em 32 s.
- **Durante o vídeo:** 2 min com episódio tocando — não organizou; parou, organizou em 33 s.
- **Arrumação:** 2 episódios soltos entraram na `Season 01`; os que já estavam certos não
  foram tocados; nome impossível de ler (`bagunca ep 05.mkv`) foi **deixado quieto** de propósito.

### Pacote para amigos v1.8 (23/10/2026)

`C:\Users\LUCAS\Downloads\JellyKodi-v1.8-para-amigos.zip` (~90 MB, 4222 arquivos).
Montado a partir do v1.6, trocando por dentro: addons 1.6.0 → **1.8.0**, keymap novo,
`guisettings.xml` com os 5 ajustes novos (seekdelay 0, as duas miniaturas de vídeo
desligadas, sem item `..`, abre no próximo episódio), `LEIA-ME.txt` e `instalar.ps1`.

O `instalar.ps1` agora também cria **`Desfazer organizacao.bat`** em `C:\Kodi` (apontando
para o `organizacao-log.csv` da instalação), porque agora a organização é automática e o
amigo precisa de um jeito de voltar atrás.

**`LOG_CSV` deixou de ser `C:\Kodi` fixo:** `jk_organize.log_dir()` usa a pasta que contém a
de Séries, senão o perfil do addon. O instalador cai em `%USERPROFILE%\Kodi` quando o `C:\`
não deixa escrever, e aí o caminho fixo botaria o log no lugar errado.

**Ao gerar o zip:** `ZipFile.CreateFromDirectory` grava as entradas com **barra invertida**,
que o Explorer do Windows pode extrair como um arquivo só de nome esquisito. Monte entrada
por entrada trocando `\` por `/` (foi o que o v1.6 fazia). Também montar numa pasta de
caminho **curto** (`C:\_jk-build`): a pasta do scratchpad estoura o MAX_PATH do Windows e a
extração morre no meio, nos caminhos fundos do `webinterface.default`.

Conferido no zip: sem `state.json`, sem `MyVideos*.db`, sem `kodi.log`, sem `Thumbnails`,
sem `addon_data` — nenhum dado pessoal do Lucas.
