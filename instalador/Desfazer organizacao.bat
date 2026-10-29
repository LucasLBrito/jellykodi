@echo off
chcp 65001 >nul
title Desfazer a ultima organizacao do Ark
echo.
echo  Isto desfaz a ULTIMA organizacao de arquivos do Ark:
echo  devolve os videos para a pasta de origem ou apaga os atalhos criados.
echo.
pause
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Ark\desfazer-organizacao.ps1" -Log "%~dp0organizacao-log.csv"
echo.
pause
