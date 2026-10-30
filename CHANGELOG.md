# Histórico de versões

## 1.9.1

**Tela inicial**
- O destaque não mostra mais "começar" colado no ano: agora é `Série • 2013 • Gêneros`
- A sinopse do destaque mostra as três linhas inteiras (a última cortava o pé das letras)

## 1.9.0

**Descobre o nome certo sozinho.** Antes de organizar, o Ark pesquisa cada série ou filme
uma vez só (não uma vez por episódio):
- **AniList** — grátis, sem chave, a melhor base para anime
- **TMDb** — opcional, com a sua própria chave nos ajustes; sinopse em português
- **IA local** (Ollama ou LM Studio) — último recurso para nomes muito bagunçados. Roda no seu
  computador: nada sai da máquina e não custa nada. Desligada por padrão.

**Tela "Organizar"**: à esquerda o que ele achou, à direita para onde vai. Dá para corrigir o
título, pular uma série ou aprovar tudo de uma vez, pelo controle.

**Três jeitos de organizar**: atalho (*hardlink* — o download fica onde está e não gasta espaço
a mais), cópia ou mover. O que não foi identificado vai para `_Nao_Identificado` com o nome
original, em vez de virar um "filme" errado.

**Livro-razão** (`organizados.json`): o Ark lembra o que já organizou e não religa um episódio
que você apagou da biblioteca de propósito.

**Capas e .nfo**: grava um `.nfo` ao lado do vídeo e baixa a capa quando o Kodi não acha nenhuma.

**Player**
- Uma barra de progresso só (a do topo aparecia junto e duplicava)
- O menu do player não tem mais animação de fechar: durante ela o Kodi descartava as teclas e
  pausar/avançar "falhavam"
- Botões −10 s / +10 s do menu voltaram a funcionar
- O botão "Pular abertura" não repete mais o que o Kodi já faz sozinho (a pausa ligava e
  desligava na mesma hora)

**Projeto**: instalador `Ark-Setup-1.9.0.exe` (Inno Setup) com desinstalador, testes
automáticos do organizador e CI no GitHub Actions.

## 1.8.0

**Organiza sozinho.** Arraste a pasta para o Downloads e pronto — não precisa apertar nada.
- Entra nas subpastas (até 4 níveis)
- Usa o **nome da pasta** como nome da série quando o arquivo é só `01.mkv`
- Reconhece pasta de temporada (`Season 2`, `Temporada 2`, `Livro 2`)
- Leva legendas junto, renomeadas igual ao vídeo
- Espera o download terminar antes de mexer (arquivo precisa ficar 30 s sem crescer)
- Nunca organiza com vídeo tocando
- Arquivo que ele não consegue ler fica onde está, em vez de virar um "filme" errado
- Desligável pelo ajuste `auto_organize`

**Arrumar a biblioteca existente** (uma vez, perguntando antes): episódio solto na pasta da
série entra na temporada certa, preservando "assistido" e "continuar de onde parou".

**Desfazer**: toda organização grava um `organizacao-log.csv` e o instalador cria um
`Desfazer organizacao.bat`.

**Correção importante:** um `state.json` ilegível apagava todo o histórico em silêncio.
Agora ele tolera BOM e se recusa a gravar por cima de um arquivo que não conseguiu ler.

## 1.7.0

**Navegação da tela inicial.** O foco parou de pular sozinho para o botão "Assistir": as
fileiras não somem mais enquanto estão selecionadas, e elas pararam de recarregar embaixo
do cursor.

**Voltar virou Voltar.** O botão estava mapeado como "ir para a tela inicial" em toda janela,
então sair de qualquer tela te jogava para o começo. Agora segurar é que vai para a Home.

**Controle funciona no player.** Enquanto aparecia "Pular abertura", o controle ficava morto:
só A e B respondiam. Avançar, legenda, áudio e menu voltaram a funcionar.

**Menu do player refeito**: uma fileira de 9 botões com o nome em português, no lugar dos 17
botões de TV a cabo, DVD e teletexto herdados do Kodi padrão.

**Tudo em português.** O buscador de séries do TMDb tinha trocado o nome do ajuste de idioma,
e por isso título e sinopse vinham em inglês mesmo com tudo configurado em pt-BR.

**Carrega mais rápido**: duas consultas no lugar de uma por card, e os limites que deixavam
a tela inicial quase vazia foram removidos.

**Escolher pastas** pelo próprio app: Séries, Filmes e a pasta que ele vigia.

## 1.6.0 e anteriores

Primeiras versões: tela inicial estilo Netflix, "Continuar assistindo", pular abertura por
capítulos do MKV, próximo episódio com contagem, "Por tema", organizar downloads pelo botão,
e o pacote de instalação para Windows.
