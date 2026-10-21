; Instalador do Stonks AI Desktop (Inno Setup 6).
;
; Pré-requisito: gerar o executável com
;     pyinstaller desktop/stonks-desktop.spec --noconfirm
; Depois, a partir da raiz do projeto:
;     "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" desktop\installer\stonks-ai.iss
; Saída: dist\installer\StonksAI-Setup-<versão>.exe
;
; Instala só para o usuário atual (sem pedir administrador) em %LOCALAPPDATA%\Programs\StonksAI.
; Os dados financeiros ficam em %APPDATA%\StonksAI e só são apagados se o usuário pedir na desinstalação.

#define AppName "Stonks AI"
; Mantenha igual à versão do pyproject.toml
#define AppVersion "0.2.0"
#define AppExe "StonksAI.exe"

[Setup]
AppId={{004A9BF7-D173-45DB-AE6E-43E6C7F4EEB1}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Stonks AI
DefaultDirName={localappdata}\Programs\StonksAI
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist\installer
OutputBaseFilename=StonksAI-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\assets\stonks.ico
UninstallDisplayName={#AppName}
; Fecha o app aberto antes de atualizar
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\..\dist\StonksAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o {#AppName} agora"; Flags: nowait postinstall skipifsilent

[Code]
// Na desinstalação, pergunta se os dados financeiros também devem ser apagados.
// O padrão é manter, para não perder nada numa reinstalação.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\StonksAI');
    if DirExists(DataDir) and (not UninstallSilent) then
      if MsgBox('Deseja apagar também seus dados (transações, metas, configurações) em ' + DataDir + '?'
                + #13#10#13#10 + 'Escolha Não para manter os dados caso vá reinstalar.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
