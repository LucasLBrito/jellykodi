<#
.SYNOPSIS
    Monta o pacote do Ark e compila o instalador Ark-Setup-<versao>.exe.

.DESCRIPTION
    O Kodi (~160 MB) nao fica no git. Este script junta, em instalador\build:
      - o Kodi 21.3 "Omega" OFICIAL, sem modificacao: baixado de mirrors.kodi.tv
        (com SHA-256 conferido) e extraido com 7-Zip, ou copiado de uma pasta local;
      - skin.ark e plugin.video.ark deste repositorio;
      - o Visual C++ da Microsoft (opcional; o Setup so instala se faltar).
    Depois chama o ISCC (Inno Setup 6) com o instalador\ark.iss.

    Nada de portable_data da pasta de origem entra: e ali que ficam biblioteca,
    historico e configuracoes pessoais.

.EXAMPLE
    .\instalador\montar.ps1
    Baixa o Kodi oficial e compila.

.EXAMPLE
    .\instalador\montar.ps1 -KodiDir C:\Kodi\Ark\Kodi
    Usa um Kodi 21.3 que ja esta no PC (so os arquivos do programa).
#>
[CmdletBinding()]
param(
    # Pasta de um Kodi 21.3 para Windows x64 ja instalado/extraido. Sem ela, baixa o oficial.
    [string]$KodiDir,
    # So monta a pasta build, sem compilar o Setup.
    [switch]$SemCompilar,
    # Nao inclui o instalador do Visual C++ no Setup.
    [switch]$SemVCRedist,
    # Caminho do ISCC.exe, se nao estiver nos lugares de sempre.
    [string]$Iscc
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # o Invoke-WebRequest fica 10x mais lento com a barra

$KodiVersao = '21.3'
$KodiUrl    = 'https://mirrors.kodi.tv/releases/windows/win64/kodi-21.3-Omega-x64.exe'
$KodiSha256 = '2C46C2BD60B38BB60EB0A5E3468BFD43E9235521EAE2910B8C81455E46335C5C'
$VCUrl      = 'https://aka.ms/vs/17/release/vc_redist.x64.exe'
# O portugues NAO vem no instalador do Kodi: e um addon do repositorio oficial.
# Sem ele o Kodi ignora o locale.language do guisettings e abre em ingles.
$PtBrUrl    = 'https://mirrors.kodi.tv/addons/omega/resource.language.pt_br/resource.language.pt_br-11.0.109.zip'
$PtBrSha256 = '992E6FEC0DC8148131EFE9D4CD4E006192682E89C4D94B294F70EC40247498F4'

$Aqui   = $PSScriptRoot
$Raiz   = Split-Path -Parent $Aqui
$Build  = Join-Path $Aqui 'build'
$Cache  = Join-Path $Aqui 'cache'
$Saida  = Join-Path $Aqui 'saida'
$Destino = Join-Path $Build 'Kodi'

function Passo($m) { Write-Host "==> $m" -ForegroundColor Cyan }

function Copiar($de, $para, [string[]]$semPastas = @(), [string[]]$semArquivos = @()) {
    $rc = @($de, $para, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:2', '/W:2')
    if ($semPastas)   { $rc += '/XD'; $rc += $semPastas }
    if ($semArquivos) { $rc += '/XF'; $rc += $semArquivos }
    & robocopy @rc | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy falhou ($LASTEXITCODE): $de -> $para" }
}

# ---------------------------------------------------------------- versao
[xml]$addon = Get-Content -LiteralPath (Join-Path $Raiz 'plugin.video.ark\addon.xml') -Encoding UTF8
$Versao = $addon.addon.version
[xml]$skin = Get-Content -LiteralPath (Join-Path $Raiz 'skin.ark\addon.xml') -Encoding UTF8
if ($skin.addon.version -ne $Versao) {
    throw "Versoes diferentes: plugin $Versao, skin $($skin.addon.version)"
}
Passo "Ark $Versao"

if (Test-Path -LiteralPath $Build) { Remove-Item -LiteralPath $Build -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Build, $Cache | Out-Null

# ---------------------------------------------------------------- Kodi oficial
if ($KodiDir) {
    $KodiDir = (Resolve-Path -LiteralPath $KodiDir).Path
    if (-not (Test-Path -LiteralPath (Join-Path $KodiDir 'kodi.exe'))) { throw "Nao achei kodi.exe em $KodiDir" }
    Passo "Copiando o Kodi de $KodiDir (sem portable_data)"
    $fora = @('portable_data', '__pycache__') + @('skin.ark', 'plugin.video.ark', 'skin.jellykodi',
              'plugin.video.jellykodi' | ForEach-Object { Join-Path $KodiDir "addons\$_" })
    Copiar $KodiDir $Destino $fora @('*.pyc', '*.log', 'state.json', '*.db')
} else {
    $exe = Join-Path $Cache (Split-Path -Leaf $KodiUrl)
    if (-not (Test-Path -LiteralPath $exe) -or (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $KodiSha256) {
        Passo "Baixando o Kodi $KodiVersao oficial"
        Invoke-WebRequest -Uri $KodiUrl -OutFile $exe -UseBasicParsing
    }
    $hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    if ($hash -ne $KodiSha256) { Remove-Item -LiteralPath $exe -Force; throw "SHA-256 do Kodi nao confere: $hash" }

    $7z = @("$env:ProgramFiles\7-Zip\7z.exe", "${env:ProgramFiles(x86)}\7-Zip\7z.exe") |
          Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $7z) { throw 'Precisa do 7-Zip para extrair o instalador do Kodi (winget install 7zip.7zip).' }
    Passo 'Extraindo o Kodi com 7-Zip'
    $bruto = Join-Path $Build 'kodi-extraido'
    & $7z x $exe "-o$bruto" -y -bso0 -bsp0
    if ($LASTEXITCODE -ne 0) { throw "7-Zip falhou ($LASTEXITCODE)" }
    $raizKodi = Get-ChildItem -LiteralPath $bruto -Recurse -Filter 'kodi.exe' | Select-Object -First 1
    if (-not $raizKodi) { throw 'kodi.exe nao apareceu no instalador extraido' }
    # sobras do instalador NSIS ($PLUGINSDIR, desinstalador) nao fazem parte do programa
    Copiar $raizKodi.DirectoryName $Destino @('$PLUGINSDIR', '$TEMP', '$_OUTDIR') @('Uninstall.exe', 'uninstall.exe')
    Remove-Item -LiteralPath $bruto -Recurse -Force
}

# ---------------------------------------------------------------- Ark
Passo 'Copiando skin.ark e plugin.video.ark'
foreach ($a in 'skin.ark', 'plugin.video.ark') {
    Copiar (Join-Path $Raiz $a) (Join-Path $Destino "addons\$a") @('__pycache__') @('*.pyc')
}

# O Kodi DESATIVA todo addon que aparece na pasta sem passar pelo gerenciador de addons
# (protecao contra addon "plantado"). Sem isto o Ark abria com a Estuary padrao e sem o
# servico. Os addons listados no addon-manifest.xml sao tratados como parte do sistema
# e ficam ativos (sem "optional": skin e servico SAO o Ark, nao podem ficar desligados;
# isso tambem reativa quem atualizou de uma versao em que eles ficaram desativados). E o mesmo mecanismo que
# distribuicoes como o LibreELEC usam. E o UNICO arquivo do Kodi que o pacote altera.
Passo 'Registrando os addons do Ark no addon-manifest.xml'
$manifesto = Join-Path $Destino 'system\addon-manifest.xml'
$texto = [IO.File]::ReadAllText($manifesto)
foreach ($id in 'skin.ark', 'plugin.video.ark', 'resource.language.pt_br') {
    if ($texto -notmatch ">$([regex]::Escape($id))<") {
        $texto = $texto.Replace('</addons>', "  <addon>$id</addon>`n</addons>")
    }
}
[IO.File]::WriteAllText($manifesto, $texto, (New-Object Text.UTF8Encoding($false)))

Passo 'Pacote de idioma portugues (repositorio oficial do Kodi)'
$ptbrZip = Join-Path $Cache (Split-Path -Leaf $PtBrUrl)
if (-not (Test-Path -LiteralPath $ptbrZip) -or (Get-FileHash -LiteralPath $ptbrZip -Algorithm SHA256).Hash -ne $PtBrSha256) {
    Invoke-WebRequest -Uri $PtBrUrl -OutFile $ptbrZip -UseBasicParsing
}
$hash = (Get-FileHash -LiteralPath $ptbrZip -Algorithm SHA256).Hash
if ($hash -ne $PtBrSha256) { Remove-Item -LiteralPath $ptbrZip -Force; throw "SHA-256 do pt_br nao confere: $hash" }
$ptbrDir = Join-Path $Destino 'addons\resource.language.pt_br'
if (Test-Path -LiteralPath $ptbrDir) { Remove-Item -LiteralPath $ptbrDir -Recurse -Force }
Expand-Archive -LiteralPath $ptbrZip -DestinationPath (Join-Path $Destino 'addons') -Force

if (-not $SemVCRedist) {
    $vc = Join-Path $Cache 'vc_redist.x64.exe'
    if (-not (Test-Path -LiteralPath $vc)) {
        Passo 'Baixando o Visual C++ da Microsoft'
        Invoke-WebRequest -Uri $VCUrl -OutFile $vc -UseBasicParsing
    }
    $assinatura = Get-AuthenticodeSignature -LiteralPath $vc
    if ($assinatura.Status -ne 'Valid' -or $assinatura.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
        Remove-Item -LiteralPath $vc -Force
        throw "vc_redist.x64.exe sem assinatura valida da Microsoft ($($assinatura.Status))"
    }
    Copy-Item -LiteralPath $vc -Destination (Join-Path $Build 'vc_redist.x64.exe')
}

# ---------------------------------------------------------------- conferencia
Passo 'Conferindo que nao entrou nada pessoal'
$proibido = Get-ChildItem -LiteralPath $Build -Recurse -Force |
    Where-Object { $_.Name -in @('portable_data', 'state.json', 'kodi.log', 'organizados.json', 'addon_data') -or
                   $_.Extension -eq '.db' -or $_.Name -eq '__pycache__' }
if ($proibido) { throw "Arquivos que nao deveriam estar no pacote:`n$($proibido.FullName -join "`n")" }
foreach ($obrigatorio in 'kodi.exe', 'addons\skin.ark\addon.xml', 'addons\plugin.video.ark\addon.xml',
                         'addons\metadata.themoviedb.org.python\addon.xml', 'addons\skin.estuary\addon.xml',
                         'addons\resource.language.pt_br\addon.xml') {
    if (-not (Test-Path -LiteralPath (Join-Path $Destino $obrigatorio))) { throw "Faltou $obrigatorio no pacote" }
}
$mb = [math]::Round(((Get-ChildItem -LiteralPath $Build -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host "    pacote: $mb MB em $Build"

if ($SemCompilar) { return }

# ---------------------------------------------------------------- Setup
if (-not $Iscc) {
    $Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
              "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") |
            Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Iscc) { throw 'Precisa do Inno Setup 6 (winget install JRSoftware.InnoSetup).' }
Passo 'Compilando o Setup'
New-Item -ItemType Directory -Force -Path $Saida | Out-Null
& $Iscc /Q "/DAppVersion=$Versao" "/DBuildDir=$Build" "/DOutputDir=$Saida" (Join-Path $Aqui 'ark.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC falhou ($LASTEXITCODE)" }
$setup = Join-Path $Saida "Ark-Setup-$Versao.exe"
$sha = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash
"$sha  Ark-Setup-$Versao.exe" | Set-Content -LiteralPath "$setup.sha256" -Encoding ascii
Passo ("Pronto: {0} ({1:N1} MB)" -f $setup, ((Get-Item -LiteralPath $setup).Length / 1MB))
Write-Host "    SHA-256: $sha"
