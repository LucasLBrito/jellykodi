# Histórico de versões

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
