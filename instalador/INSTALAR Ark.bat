@echo off
chcp 65001 >nul
title Instalar JellyKodi
cd /d "%~dp0"
echo.
echo  ==============================================
echo    JellyKodi - Kodi estilo Netflix com controle
echo  ==============================================
echo.
if not exist "%~dp0app\Kodi\kodi.exe" (
  echo  [X] Nao achei os arquivos. Extraia o ZIP inteiro antes de rodar este instalador
  echo      ^(botao direito no ZIP ^> Extrair tudo^). Nao rode de dentro do ZIP.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\instalar.ps1"
if errorlevel 1 (
  echo.
  echo  [X] Deu erro. Tire um print desta janela e mande para quem te passou o JellyKodi.
  pause
  exit /b 1
)
echo.
echo  Abrindo o JellyKodi... ^(esta janela fecha sozinha^)
timeout /t 8 >nul
