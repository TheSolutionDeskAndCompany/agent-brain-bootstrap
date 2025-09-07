#define AppName "AgentBrain"
#define AppExe "AgentBrain.exe"
#define AppPublisher "The Solution Desk"
#define AppURL "https://github.com/ORG/REPO"
#define AppVersion GetStringDef(ExpandConstant('{#AppVersion}'), '0.1.0')

[Setup]
AppId={{D81D79B4-33D4-4C6D-95D5-2F4B73E3A2C1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename={#AppName}-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Files]
Source: "dist\AgentBrain.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autostartup}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\logs\*.*"

