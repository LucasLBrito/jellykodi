# Desfaz a ULTIMA organizacao do Ark, lendo o organizacao-log.csv.
#
# O log tem 3 colunas: De, Para, Modo. O modo diz como desfazer:
#   movido       -> devolve o arquivo para a pasta de origem
#   link / copia -> o original nunca saiu do lugar: so apaga o arquivo novo.
#                   Se o original sumiu, devolve a copia em vez de apagar o unico exemplar.
param([string]$Log = (Join-Path (Split-Path -Parent $PSScriptRoot) 'organizacao-log.csv'))
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Log)) { Write-Host '  Nada para desfazer.'; exit 0 }

$feitos = 0; $falhas = 0
foreach ($linha in Import-Csv -LiteralPath $Log -Encoding UTF8) {
    $de = $linha.De; $para = $linha.Para; $modo = $linha.Modo
    if (-not $para -or -not (Test-Path -LiteralPath $para)) { continue }
    try {
        if (($modo -eq 'link' -or $modo -eq 'copia') -and (Test-Path -LiteralPath $de)) {
            Remove-Item -LiteralPath $para -Force
        } else {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $de) | Out-Null
            Move-Item -LiteralPath $para -Destination $de -Force
        }
        $feitos++
    } catch {
        Write-Host "  Nao consegui desfazer: $para ($($_.Exception.Message))"
        $falhas++
    }
}
Write-Host "  Pronto: $feitos arquivo(s) desfeito(s)."
if ($falhas) { Write-Host "  $falhas arquivo(s) ficaram para tras (veja acima)."; exit 1 }
