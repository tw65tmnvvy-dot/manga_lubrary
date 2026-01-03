; Inno Setup script for Manga Library
; The EXE path is provided via /DMyAppExe="<path>" when calling ISCC

[Setup]
AppName=Manga Library
AppVersion=1.0
DefaultDirName={pf}\Manga Library
DefaultGroupName=Manga Library
DisableProgramGroupPage=yes
OutputBaseFilename=MangaLibrary_Installer
Compression=lzma2
SolidCompression=yes
; Require admin so installer can install Chocolatey and system packages
PrivilegesRequired=admin

[Files]
; The builder passes MyAppExe path as a preprocessor define.
Source: "{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Manga Library"; Filename: "{app}\MangaLibrary.exe"

; Optional tasks presented to the user
[Tasks]
Name: installchoco; Description: "Install Chocolatey (Windows package manager)"; GroupDescription: "Optional tools to install:"; Flags: unchecked
Name: choco_git; Description: "Install Git (via Chocolatey)"; Flags: unchecked
Name: choco_python; Description: "Install Python (via Chocolatey)"; Flags: unchecked
Name: choco_7zip; Description: "Install 7zip (via Chocolatey)"; Flags: unchecked
Name: choco_npp; Description: "Install Notepad++ (via Chocolatey)"; Flags: unchecked

[Run]
; If any Chocolatey package task is selected and Chocolatey is not present, install Chocolatey first
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"""; \
	StatusMsg: "Installing Chocolatey (package manager)..."; Flags: runhidden waituntilterminated; \
	Check: (not FileExists(ExpandConstant('{commonappdata}\chocolatey\bin\choco.exe')) ) and \
				 ( IsTaskSelected('choco_git') or IsTaskSelected('choco_python') or IsTaskSelected('choco_7zip') or IsTaskSelected('choco_npp') or IsTaskSelected('installchoco') )

; If user explicitly chose to install Chocolatey (even without selecting packages), install it
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"""; \
	StatusMsg: "Installing Chocolatey (package manager)..."; Flags: runhidden waituntilterminated; Check: IsTaskSelected('installchoco') and (not FileExists(ExpandConstant('{commonappdata}\chocolatey\bin\choco.exe')))

; Install selected Chocolatey packages (use explicit choco path to avoid PATH timing issues)
Filename: "{commonappdata}\chocolatey\bin\choco.exe"; Parameters: "install git -y --no-progress"; StatusMsg: "Installing Git..."; Flags: runhidden waituntilterminated; Check: IsTaskSelected('choco_git') and FileExists(ExpandConstant('{commonappdata}\chocolatey\bin\choco.exe'))
Filename: "{commonappdata}\chocolatey\bin\choco.exe"; Parameters: "install python -y --no-progress"; StatusMsg: "Installing Python..."; Flags: runhidden waituntilterminated; Check: IsTaskSelected('choco_python') and FileExists(ExpandConstant('{commonappdata}\chocolatey\bin\choco.exe'))
Filename: "{commonappdata}\chocolatey\bin\choco.exe"; Parameters: "install 7zip -y --no-progress"; StatusMsg: "Installing 7zip..."; Flags: runhidden waituntilterminated; Check: IsTaskSelected('choco_7zip') and FileExists(ExpandConstant('{commonappdata}\chocolatey\bin\choco.exe'))
Filename: "{commonappdata}\chocolatey\bin\choco.exe"; Parameters: "install notepadplusplus -y --no-progress"; StatusMsg: "Installing Notepad++..."; Flags: runhidden waituntilterminated; Check: IsTaskSelected('choco_npp') and FileExists(ExpandConstant('{commonappdata}\chocolatey\bin\choco.exe'))

; Launch the app after installation
Filename: "{app}\MangaLibrary.exe"; Description: "Launch Manga Library"; Flags: nowait postinstall skipifsilent
