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

[Files]
; The builder passes MyAppExe path as a preprocessor define.
Source: "{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Manga Library"; Filename: "{app}\MangaLibrary.exe"

[Run]
Filename: "{app}\MangaLibrary.exe"; Description: "Launch Manga Library"; Flags: nowait postinstall skipifsilent
