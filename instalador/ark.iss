; Ark - instalador para Windows 10/11 (64 bits), feito com Inno Setup 6.
;
; Nao compile este arquivo direto: use o instalador\montar.ps1, que monta a pasta
; instalador\build (Kodi oficial + skin + addon) e chama o ISCC com as variaveis abaixo.
;
; Onde instala: C:\Kodi (ou %USERPROFILE%\Kodi se o C:\ nao deixar criar pasta).
;   C:\Kodi\Ark\Kodi   o programa (Kodi portatil + Ark)
;   C:\Kodi\Series     suas series      } nunca sao apagadas pelo desinstalador
;   C:\Kodi\Filmes     seus filmes      }
; Por que nao %LOCALAPPDATA%: e o mesmo lugar das versoes 1.6-1.8 (quem atualiza mantem
; biblioteca e historico), fica fora do OneDrive, o caminho e curto (o Kodi tem pastas
; fundas que estouram o limite de 260 caracteres do Windows) e o organizador grava o log
; de desfazer na pasta que contem a de Series - aqui, a mesma pasta do .bat.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef BuildDir
  #define BuildDir "build"
#endif
#ifndef OutputDir
  #define OutputDir "saida"
#endif

#define AppName "Ark"
#define AppExe "Ark\Kodi\kodi.exe"

[Setup]
; AppId fixo: e por ele que o Windows sabe que a versao nova substitui a antiga
AppId={{6C4B8E2A-5F1D-4C3B-9A7E-A2D3F1E0B9C4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Lucas Brito
AppPublisherURL=https://github.com/LucasLBrito/jellykodi
AppSupportURL=https://github.com/LucasLBrito/jellykodi/issues
AppUpdatesURL=https://github.com/LucasLBrito/jellykodi/releases
AppCopyright=Ark: GPL-2.0-or-later. Kodi: Team Kodi, GPL-2.0-or-later.
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Instalador do Ark
DefaultDirName={code:PastaPadrao}
DisableProgramGroupPage=yes
DisableWelcomePage=no
DisableDirPage=no
UsePreviousAppDir=yes
; sem administrador: nada fora da pasta escolhida, desinstalador registrado so para o usuario
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=Ark-Setup-{#AppVersion}
SetupIconFile=arte\ark.ico
UninstallDisplayIcon={app}\Ark\ark.ico
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=arte\assistente-100.bmp,arte\assistente-200.bmp
WizardSmallImageFile=arte\assistente-pequeno-100.bmp,arte\assistente-pequeno-200.bmp
Compression=lzma2/max
SolidCompression=yes
; fecha o Ark aberto antes de trocar os arquivos (e reabre no fim, se o usuario quiser)
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
ptbr.Abrir=Abrir o Ark agora
ptbr.AtalhoArea=Criar atalho na Área de Trabalho
ptbr.PastaVideos=Abrir a pasta dos vídeos
ptbr.AvisoOneDrive=Essa pasta está dentro do OneDrive. Ele fica enviando os vídeos para a nuvem e pode lotar o seu espaço.%n%nUse mesmo assim?
ptbr.ApagarDados=Apagar também as suas configurações, o histórico de "Continuar assistindo" e a biblioteca do Ark?%n%nSeus vídeos (Séries e Filmes) NÃO são apagados em nenhum caso.
ptbr.VCRedist=Instalando componentes do Windows (Visual C++)...

[Tasks]
Name: "desktopicon"; Description: "{cm:AtalhoArea}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; addons do Ark sao substituidos inteiros: arquivo que saiu de uma versao nao fica para tras
Type: filesandordirs; Name: "{app}\Ark\Kodi\addons\skin.ark"
Type: filesandordirs; Name: "{app}\Ark\Kodi\addons\plugin.video.ark"
; nomes antigos (JellyKodi 1.6-1.8)
Type: filesandordirs; Name: "{app}\Ark\Kodi\addons\skin.jellykodi"
Type: filesandordirs; Name: "{app}\Ark\Kodi\addons\plugin.video.jellykodi"
Type: files; Name: "{app}\Ark\Kodi\portable_data\userdata\keymaps\jellykodi-controle.xml"

[Dirs]
Name: "{app}\Series"; Flags: uninsneveruninstall
Name: "{app}\Filmes"; Flags: uninsneveruninstall

[Files]
; o Kodi oficial + skin + addon (montados pelo montar.ps1)
Source: "{#BuildDir}\Kodi\*"; DestDir: "{app}\Ark\Kodi"; Flags: ignoreversion recursesubdirs createallsubdirs
; configuracao inicial: so na primeira instalacao, nunca por cima da do usuario
Source: "modelo\userdata\guisettings.xml"; DestDir: "{app}\Ark\Kodi\portable_data\userdata"; Flags: onlyifdoesntexist uninsneveruninstall
; o mapa do controle e do Ark: sempre a versao nova
Source: "..\userdata\keymaps\ark-controle.xml"; DestDir: "{app}\Ark\Kodi\portable_data\userdata\keymaps"; Flags: ignoreversion
Source: "desfazer-organizacao.ps1"; DestDir: "{app}\Ark"; Flags: ignoreversion
Source: "Desfazer organizacao.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEIA-ME.txt"; DestDir: "{app}\Ark"; Flags: ignoreversion isreadme
Source: "arte\ark.ico"; DestDir: "{app}\Ark"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}\Ark"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\NOTICE.md"; DestDir: "{app}\Ark"; DestName: "CREDITOS.md"; Flags: ignoreversion
#ifexist BuildDir + "\vc_redist.x64.exe"
Source: "{#BuildDir}\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: FaltaVCRedist
#endif

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "-p"; WorkingDir: "{app}\Ark\Kodi"; IconFilename: "{app}\Ark\ark.ico"
Name: "{autoprograms}\{#AppName} - pasta dos vídeos"; Filename: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "-p"; WorkingDir: "{app}\Ark\Kodi"; IconFilename: "{app}\Ark\ark.ico"; Tasks: desktopicon

[Run]
#ifexist BuildDir + "\vc_redist.x64.exe"
; o pacote da Microsoft pede administrador sozinho (shellexec deixa o Windows perguntar)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "{cm:VCRedist}"; Flags: shellexec waituntilterminated; Check: FaltaVCRedist
#endif
Filename: "{app}\{#AppExe}"; Parameters: "-p"; WorkingDir: "{app}\Ark\Kodi"; Description: "{cm:Abrir}"; Flags: postinstall nowait skipifsilent
Filename: "{app}"; Description: "{cm:PastaVideos}"; Flags: postinstall shellexec skipifsilent unchecked

[UninstallDelete]
; o que o Kodi cria sozinho enquanto roda (cache, log). portable_data e tratado no [Code].
Type: filesandordirs; Name: "{app}\Ark\Kodi\portable_data\temp"
Type: files; Name: "{app}\Ark\Kodi\portable_data\kodi.log"
Type: files; Name: "{app}\Ark\Kodi\portable_data\kodi.old.log"
Type: dirifempty; Name: "{app}\Ark\Kodi"
Type: dirifempty; Name: "{app}\Ark"

[Code]
function PodeCriarPasta(const Pasta: String): Boolean;
begin
  Result := DirExists(Pasta) or ForceDirectories(Pasta);
  if Result and not DirExists(Pasta) then
    Result := False;
end;

{ C:\Kodi como nas versoes anteriores; sem permissao no C:\, a pasta do usuario. }
function PastaPadrao(Param: String): String;
begin
  Result := ExpandConstant('{sd}\Kodi');
  if not PodeCriarPasta(Result) then
    Result := ExpandConstant('{%USERPROFILE}\Kodi');
end;

function FaltaVCRedist: Boolean;
var
  Instalado: Cardinal;
begin
  Result := not (RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
                                    'Installed', Instalado) and (Instalado = 1));
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpSelectDir) and (Pos('onedrive', Lowercase(WizardDirValue)) > 0) then
    Result := MsgBox(CustomMessage('AvisoOneDrive'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

function EscaparXml(const Texto: String): String;
begin
  Result := Texto;
  StringChangeEx(Result, '&', '&amp;', True);
  StringChangeEx(Result, '<', '&lt;', True);
  StringChangeEx(Result, '>', '&gt;', True);
  StringChangeEx(Result, '"', '&quot;', True);
end;

{ Cadastra Series e Filmes no Kodi. So na primeira instalacao: depois disso as pastas
  sao do usuario (ele pode ter trocado pelo "Escolher pastas" do app). }
procedure CriarSources;
var
  Arquivo, Xml, Series, Filmes: String;
begin
  Arquivo := ExpandConstant('{app}\Ark\Kodi\portable_data\userdata\sources.xml');
  if FileExists(Arquivo) then
    Exit;
  Series := EscaparXml(ExpandConstant('{app}\Series\'));
  Filmes := EscaparXml(ExpandConstant('{app}\Filmes\'));
  Xml :=
    '<sources>' + #13#10 +
    '    <programs><default pathversion="1"></default></programs>' + #13#10 +
    '    <video>' + #13#10 +
    '        <default pathversion="1"></default>' + #13#10 +
    '        <source>' + #13#10 +
    '            <name>Series</name>' + #13#10 +
    '            <path pathversion="1">' + Series + '</path>' + #13#10 +
    '            <allowsharing>true</allowsharing>' + #13#10 +
    '        </source>' + #13#10 +
    '        <source>' + #13#10 +
    '            <name>Filmes</name>' + #13#10 +
    '            <path pathversion="1">' + Filmes + '</path>' + #13#10 +
    '            <allowsharing>true</allowsharing>' + #13#10 +
    '        </source>' + #13#10 +
    '    </video>' + #13#10 +
    '    <music><default pathversion="1"></default></music>' + #13#10 +
    '    <pictures><default pathversion="1"></default></pictures>' + #13#10 +
    '    <files><default pathversion="1"></default></files>' + #13#10 +
    '    <games><default pathversion="1"></default></games>' + #13#10 +
    '</sources>' + #13#10;
  ForceDirectories(ExtractFileDir(Arquivo));
  SaveStringToFile(Arquivo, Xml, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    CriarSources;
end;

{ Desinstalar: o programa sai sempre; configuracao, historico e biblioteca so se o
  usuario pedir; os videos nunca. Na desinstalacao silenciosa os dados ficam, a nao
  ser com /APAGARDADOS=1 (usado nos testes). }
function ApagarDados: Boolean;
begin
  if UninstallSilent then
    Result := ExpandConstant('{param:APAGARDADOS|0}') = '1'
  else
    Result := MsgBox(CustomMessage('ApagarDados'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Dados: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Dados := ExpandConstant('{app}\Ark\Kodi\portable_data');
    if DirExists(Dados) and ApagarDados then
    begin
      DelTree(Dados, True, True, True);
      RemoveDir(ExpandConstant('{app}\Ark\Kodi'));
      RemoveDir(ExpandConstant('{app}\Ark'));
    end;
  end;
end;
