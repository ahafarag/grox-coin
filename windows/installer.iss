; Inno Setup script for the Grox Wallet installer (GroxWallet-Setup-<version>-win-x64.exe).
; Built by windows\build.ps1:  iscc /DAppVersion=1.0.0 /DSourceDir=<GroxWallet folder> /DOutputDir=dist installer.iss
;
; Installs for the current user only (no administrator rights needed) into
; %LOCALAPPDATA%\Programs\Grox Wallet. It writes nothing outside that folder and the
; Start menu: the app creates the wallet folder (C:\Users\<you>\Grox) itself. Never
; use Documents here: ransomware protection / OneDrive can block it ("Error 2").
; Wallets and the blockchain (C:\ProgramData\grox) are never deleted by the uninstaller.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\build\windows\dist\GroxWallet"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

[Setup]
AppId={{8F3D5C2A-6B1E-4E7A-9C41-2B7F0D5A9E13}
AppName=Grox Wallet
AppVersion={#AppVersion}
AppVerName=Grox Wallet {#AppVersion}
AppPublisher=Grox
AppPublisherURL=https://github.com/ahafarag/grox-coin
AppSupportURL=https://github.com/ahafarag/grox-coin/blob/main/docs/WINDOWS.md
AppUpdatesURL=https://github.com/ahafarag/grox-coin/releases
DefaultDirName={autopf}\Grox Wallet
DefaultGroupName=Grox
DisableProgramGroupPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
AppMutex=GroxWalletRunning
OutputDir={#OutputDir}
OutputBaseFilename=GroxWallet-Setup-{#AppVersion}-win-x64
SetupIconFile=grox.ico
UninstallDisplayIcon={app}\GroxWallet.exe
UninstallDisplayName=Grox Wallet
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion={#AppVersion}
VersionInfoProductName=Grox Wallet

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupAppRunningError=Grox Wallet is running. Close its window first (mining stops), then press OK.
UninstallAppRunningError=Grox Wallet is running. Close its window first (mining stops), then press OK.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Grox Wallet"; Filename: "{app}\GroxWallet.exe"; Comment: "Grox wallet and solo mining"
Name: "{autoprograms}\Grox wallet files"; Filename: "{%USERPROFILE}\Grox"; Comment: "Your Grox wallet files (back them up)"
Name: "{autodesktop}\Grox Wallet"; Filename: "{app}\GroxWallet.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GroxWallet.exe"; Description: "{cm:LaunchProgram,Grox Wallet}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    MsgBox('Grox Wallet was removed.' + #13#10#13#10 +
      'Your wallet files were kept in:' + #13#10 + ExpandConstant('{%USERPROFILE}\Grox') + #13#10#13#10 +
      'The blockchain copy was kept in C:\ProgramData\grox (you can delete that folder to free space).',
      mbInformation, MB_OK);
end;
