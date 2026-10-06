; Installeur Windows d'IUC (Inno Setup 6). Installe l'application compilée par
; PyInstaller (build\dist\IUC) pour l'utilisateur courant, sans droits administrateur,
; avec un raccourci dans le menu Démarrer. Les données (%LOCALAPPDATA%\IUC) sont gardées à
; la désinstallation : on les supprime depuis IUC (« Supprimer mes données locales »).
; Mise à jour depuis IUC : installation silencieuse avec /UPDATE=1, qui attend la fermeture
; d'IUC puis le relance (voir backend/app/services/update.py).
;   set IUC_VERSION=1.0.0 && iscc packaging\iuc.iss

#define AppVersion GetEnv("IUC_VERSION")
#if AppVersion == ""
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{99136391-9BBF-4869-A7FE-D7D354E47CEA}
AppName=IUC – Instagram Unlike Cleaner
AppVersion={#AppVersion}
AppVerName=IUC {#AppVersion}
AppPublisher=Cédric Kouadio
AppPublisherURL=https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner
AppSupportURL=https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner/issues
DefaultDirName={localappdata}\Programs\IUC
DefaultGroupName=IUC
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\build\installer
; Nom stable : le README pointe vers releases/latest/download/IUC-Setup.exe.
OutputBaseFilename=IUC-Setup
SetupIconFile=iuc.ico
UninstallDisplayIcon={app}\IUC.exe
LicenseFile=..\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\build\dist\IUC\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\IUC"; Filename: "{app}\IUC.exe"
Name: "{group}\Désinstaller IUC"; Filename: "{uninstallexe}"
Name: "{autodesktop}\IUC"; Filename: "{app}\IUC.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\IUC.exe"; Description: "{cm:LaunchProgram,IUC}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\IUC.exe"; Flags: nowait; Check: IsUpdate

[Code]
const
  // Verrou tenu par IUC.exe tant qu'il tourne (backend/app/desktop.py).
  InstanceLock = 'Local\IUC-Instagram-Unlike-Cleaner';
  MaxWaitMs = 60000;

function IsUpdate: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE|0}') = '1';
end;

function InitializeSetup: Boolean;
var
  Waited: Integer;
begin
  // Mise à jour lancée par IUC : ses fichiers ne sont remplaçables qu'une fois IUC fermé.
  if IsUpdate then
  begin
    Waited := 0;
    while CheckForMutexes(InstanceLock) and (Waited < MaxWaitMs) do
    begin
      Sleep(250);
      Waited := Waited + 250;
    end;
  end;
  Result := True;
end;
