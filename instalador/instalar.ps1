# Ark - instalador para qualquer PC com Windows 10/11 (64 bits).
# Instala em C:\Kodi (fora do OneDrive), cria as pastas Series e Filmes, atalho e abre.
$ErrorActionPreference = 'Stop'
$app  = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $app 'Kodi'
function Say($m) { Write-Host "  $m" }

# 1. onde instalar: C:\Kodi (ou a pasta do usuario se C:\ nao deixar)
$base = if ($env:JK_BASE) { $env:JK_BASE } else { 'C:\Kodi' }
try { New-Item -ItemType Directory -Force -Path $base | Out-Null }
catch { $base = Join-Path $env:USERPROFILE 'Kodi'; New-Item -ItemType Directory -Force -Path $base | Out-Null }
$kodiDir  = Join-Path $base 'Ark\Kodi'
$userdata = Join-Path $kodiDir 'portable_data\userdata'
$series   = Join-Path $base 'Series'
$filmes   = Join-Path $base 'Filmes'

# 2. fechar o Ark se estiver aberto
Get-Process -Name kodi -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$kodiDir*" } | ForEach-Object {
    Say 'Fechando o Ark aberto...'; $null = $_.CloseMainWindow(); Start-Sleep 5
    if (-not $_.HasExited) { $_ | Stop-Process -Force }
}

# 3. copiar (atualizacao preserva configuracoes, historico e biblioteca)
$atualizando = Test-Path -LiteralPath (Join-Path $kodiDir 'kodi.exe')
Say ($(if ($atualizando) { "Atualizando o Ark em $base ..." } else { "Instalando o Ark em $base (1-2 minutos)..." }))
$rc = @($src, $kodiDir, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:2', '/W:2')
if ($atualizando) { $rc += @('/XD', (Join-Path $src 'portable_data')) }
& robocopy @rc | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Falha ao copiar arquivos (robocopy $LASTEXITCODE)" }
try { Get-ChildItem -LiteralPath $kodiDir -Recurse -File | Unblock-File } catch {}

# 4. pastas de videos + cadastradas no Kodi
New-Item -ItemType Directory -Force -Path $series, $filmes | Out-Null
$srcFile = Join-Path $userdata 'sources.xml'
if (-not (Test-Path -LiteralPath $srcFile)) {
    function Esc($s) { [Security.SecurityElement]::Escape($s) }
    $xml = @"
<sources>
    <programs><default pathversion="1"></default></programs>
    <video>
        <default pathversion="1"></default>
        <source>
            <name>Series</name>
            <path pathversion="1">$(Esc ($series + '\'))</path>
            <allowsharing>true</allowsharing>
        </source>
        <source>
            <name>Filmes</name>
            <path pathversion="1">$(Esc ($filmes + '\'))</path>
            <allowsharing>true</allowsharing>
        </source>
    </video>
    <music><default pathversion="1"></default></music>
    <pictures><default pathversion="1"></default></pictures>
    <files><default pathversion="1"></default></files>
    <games><default pathversion="1"></default></games>
</sources>
"@
    New-Item -ItemType Directory -Force -Path $userdata | Out-Null
    [IO.File]::WriteAllText($srcFile, $xml, (New-Object Text.UTF8Encoding($false)))
}


# 4b. atalho para desfazer a ultima organizacao de arquivos
$undo = Join-Path $base 'Desfazer organizacao.bat'
$log  = Join-Path $base 'organizacao-log.csv'
$bat  = @"
@echo off
title Desfazer a ultima organizacao do Ark
echo Isto devolve para a pasta de origem os videos da ULTIMA organizacao.
echo.
pause
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Test-Path -LiteralPath '$log')) { Write-Host 'Nada para desfazer.'; exit }; Import-Csv -LiteralPath '$log' | ForEach-Object { if (Test-Path -LiteralPath `$_.Para) { New-Item -ItemType Directory -Force -Path (Split-Path -Parent `$_.De) | Out-Null; Move-Item -LiteralPath `$_.Para -Destination `$_.De -Force } }; Write-Host 'Pronto: arquivos devolvidos.'"
echo.
pause
"@
[IO.File]::WriteAllText($undo, $bat, (New-Object Text.UTF8Encoding($false)))


# 5. atalho na Area de Trabalho
$kodi = Join-Path $kodiDir 'kodi.exe'
try {
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Ark.lnk')
    $s.TargetPath = $kodi; $s.Arguments = '-p'; $s.WorkingDirectory = $kodiDir; $s.IconLocation = "$kodi,0"; $s.Save()
    Say 'Atalho "Ark" criado na Area de Trabalho.'
} catch { Say 'Nao consegui criar o atalho. Abra pelo arquivo kodi.exe com -p.' }

Write-Host ''
Say "Pronto! Ark instalado em $base"
Say "Coloque series em:  $series"
Say "Coloque filmes em:  $filmes"
Say 'Ou so baixe na pasta Downloads: ele organiza sozinho em ~30 segundos.'
if (-not $env:JK_NO_LAUNCH) { Start-Process -FilePath $kodi -ArgumentList '-p' -WorkingDirectory $kodiDir }
