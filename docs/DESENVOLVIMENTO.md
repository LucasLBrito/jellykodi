# Desenvolvimento

## O que precisa

| Para | Ferramenta |
|---|---|
| Testes e lint | [uv](https://docs.astral.sh/uv/) (ele baixa o Python e as dependências sozinho) |
| Montar o Setup | Windows, PowerShell 5.1+, [Inno Setup 6](https://jrsoftware.org/isinfo.php) e [7-Zip](https://www.7-zip.org) |
| Testar de verdade | Kodi 21 "Omega" |

```powershell
winget install astral-sh.uv
winget install JRSoftware.InnoSetup   # só para montar o Setup
winget install 7zip.7zip              # só para montar o Setup baixando o Kodi
```

## Testes

```bash
uv run pytest           # 250+ testes, menos de 2 s
uv run ruff check .     # lint leve: só o que costuma ser bug
uv run --python 3.8 pytest   # o Python que vem dentro do Kodi 21 no Windows
```

Os testes rodam **sem Kodi**. Os módulos do add-on importam `xbmc`, `xbmcaddon` etc. no
topo, então `tests/kodi_stubs/` tem versões mínimas desses módulos e o `tests/conftest.py`
os coloca no caminho antes do primeiro import. Cada teste ganha um perfil próprio numa pasta
temporária (`state.json`, livro-razão, ajustes), então nada vaza entre testes.

| Arquivo | Cobre |
|---|---|
| `tests/test_organize.py` | O planejador: SxxEyy, 1x02, `Nome - 02`, nome e temporada pela pasta, maioria da pasta, filme pelo ano, extras, legendas, nunca sobrescrever, livro-razão, arrumação da biblioteca |
| `tests/test_common.py` | `state.json` (BOM, arquivo ilegível), cache, próximo episódio, capas, pontuação da pesquisa, leitura de JSON da IA |
| `tests/test_xml.py` | Todo XML da skin, do add-on e do keymap abre; as versões batem entre `addon.xml`, `pyproject.toml` e o CHANGELOG |

O planejador é testado com **pastas e arquivos de verdade** (vazios) numa pasta temporária,
porque ele decide olhando o disco. Para testar um nome novo, acrescente um caso em
`test_organize.py`:

```python
def test_meu_caso(biblioteca, criar):
    criar(biblioteca['Downloads'], 'Minha Serie/Temporada 3/07.mkv')
    assert destinos(biblioteca) == {
        '07.mkv': 'Series/Minha Serie/Season 03/Minha Serie S03E07.mkv'}
```

## Montar o Setup

```powershell
.\instalador\montar.ps1                           # baixa o Kodi 21.3 oficial
.\instalador\montar.ps1 -KodiDir C:\caminho\Kodi  # usa um Kodi 21.3 que já está no PC
```

O script:

1. lê a versão do `plugin.video.ark/addon.xml` (e confere que a da skin é igual);
2. baixa o instalador oficial do Kodi de `mirrors.kodi.tv`, confere o **SHA-256** fixado no
   script e extrai com 7-Zip — ou copia a pasta local, **sem** `portable_data`;
3. registra a skin e o add-on no `system/addon-manifest.xml` (veja
   [ARQUITETURA.md](ARQUITETURA.md#decisões));
4. copia `skin.ark` e `plugin.video.ark` deste repositório;
5. baixa o pacote de idioma **pt-BR** do repositório oficial do Kodi (também com SHA-256) —
   ele não vem no instalador do Kodi, e sem ele o Ark abriria em inglês;
6. baixa o Visual C++ da Microsoft e confere a assinatura digital;
7. confere que nada pessoal entrou (`portable_data`, `.db`, `state.json`, `kodi.log`);
8. compila `instalador/ark.iss` → `instalador/saida/Ark-Setup-<versão>.exe` e um `.sha256`.

Os downloads ficam em `instalador/cache/` e são reaproveitados. `build/`, `cache/` e `saida/`
não vão para o git.

Para **atualizar o Kodi**: troque `$KodiUrl` e `$KodiSha256` no começo do `montar.ps1`.
Para o pt-BR: `$PtBrUrl` e `$PtBrSha256`.

O ícone e as imagens do assistente são gerados por código:

```bash
uv run --no-project --with pillow python instalador/arte/gerar_arte.py
```

### Testar o Setup

```powershell
.\instalador\saida\Ark-Setup-1.9.1.exe /VERYSILENT /DIR="C:\ark-teste" /MERGETASKS="!desktopicon"
C:\ark-teste\unins000.exe /VERYSILENT /APAGARDADOS=1
```

`/APAGARDADOS=1` faz a desinstalação silenciosa apagar também configurações e biblioteca
(sem ele, o modo silencioso mantém os dados; o modo normal pergunta).

> **Cuidados ao abrir o Kodi de uma instalação de teste**
> - O organizador automático vigia o `Downloads` **de verdade** do usuário. Antes de abrir,
>   crie `portable_data\userdata\addon_data\plugin.video.ark\settings.xml` com
>   `<setting id="auto_organize">false</setting>`, ou aponte a pasta vigiada para uma pasta
>   vazia em "Escolher pastas".
> - Use uma pasta de **caminho curto**: com caminhos muito longos o Setup trava antes de
>   copiar (limite de 260 caracteres do Windows).

O CI faz o mesmo ciclo a cada push: compila, instala numa pasta temporária, confere os
arquivos e o manifesto, desinstala e confere que `Series` ficou.

## Testar no Kodi

**Deploy rápido** (sem Setup): copie `skin.ark` e `plugin.video.ark` por cima das pastas em
`<Kodi>\addons\`. Mudou só XML da skin? Use `ReloadSkin()` (ou reinicie). Mudou Python?
Reinicie o Kodi — o serviço só recarrega assim. Feche o Kodi antes de mexer no banco
`portable_data\userdata\Database\MyVideos*.db`.

**Testar navegação sem controle na mão**, por JSON-RPC:

1. Com o Kodi **fechado**, ligue no `portable_data\userdata\guisettings.xml`:
   `services.webserver = true`, `services.webserverport = 8089`,
   `services.webserverauthentication = false`.
2. Abra o Kodi e mande teclas de verdade com `Input.ButtonEvent`:

   ```bash
   curl -s -H 'Content-Type: application/json' http://127.0.0.1:8089/jsonrpc \
     -d '{"jsonrpc":"2.0","id":1,"method":"Input.ButtonEvent","params":{"button":"down","keymap":"KB"}}'
   ```

   (`Input.Down` manda "mover", não a tecla, e se comporta diferente.)
3. Confira onde o foco parou com `XBMC.GetInfoLabels` e os rótulos `System.CurrentWindow`,
   `System.CurrentControlId` e `Container(5100).NumItems`.
4. Capture a tela com `Input.ExecuteAction {"action":"screenshot"}` (defina antes
   `debug.screenshotpath`).
5. **Desligue o webserver no fim.**

Em TV com **HDR**, as capturas do Kodi saem escuras e com as cores trocadas (a interface é
desenhada com o brilho SDR reduzido). Para capturas de documentação, use um monitor SDR.

**Ver o que o add-on fez**: `portable_data\kodi.log`, linhas com `[Ark]`.

## Lançar uma versão

1. Suba a versão nos dois `addon.xml` e no `pyproject.toml` e rode `uv lock` (o CI usa
   `--locked` e falha se o lock ficar com a versão velha; o teste `test_versoes_iguais`
   reclama se ficarem diferentes).
2. Escreva a seção no `CHANGELOG.md` (o teste `test_versao_no_changelog` confere).
3. `git tag v1.9.1 && git push origin v1.9.1` — o CI compila o Setup e cria a Release com o
   `.exe` e o `.sha256` anexados.
