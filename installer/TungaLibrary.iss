; ============================================================
;  Inno Setup Script — TungaLibrary Attendance Manager
;  Tested with Inno Setup 6.x  (https://jrsoftware.org/isinfo.php)
;
;  HOW TO BUILD:
;    1. Run PyInstaller first:   pyinstaller TungaLibrary.spec
;    2. Open this file in Inno Setup Compiler and click Build
;    3. Installer lands in:      installer\Output\TungaLibrarySetup.exe
;
;  INSTALL TARGET:
;    No admin rights needed — installs to %LocalAppData%
;    so it works on locked-down college PCs.
; ============================================================

#define AppName        "TungaLibrary Attendance Manager"
#define AppVersion     "1.0.1"
#define AppPublisher   "Tunga Mahavidyalaya"
#define AppExeName     "TungaLibrary.exe"
#define AppId          "{{A3F2C1D4-5E6B-7F8A-9B0C-1D2E3F4A5B6C}"
; Keep this GUID stable for upgrades of the same application.

; Path to PyInstaller output — relative to this .iss file (../dist/TungaLibrary)
#define DistDir        "..\dist\TungaLibrary"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; No admin required — per-user install
PrivilegesRequired=lowest
; Do not offer elevation: persistent data is written beside the executable.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=TungaLibrarySetup
SetupIconFile=..\assets\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Release target: Windows 10 22H2 (x64) and Windows 11 (x64).
MinVersion=10.0.19045
DisableDirPage=yes
UsePreviousAppDir=no
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut";  GroupDescription: "Additional icons:"
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional icons:"

; ── Files ──────────────────────────────────────────────────────────────────

[Files]
; The entire PyInstaller output folder (exe + all Qt DLLs + bundled assets)
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; User data is never an installer payload. main.py creates an empty DB on first
; launch; import students using CSV, then copy approved photos to {app}\photos.
; This prevents upgrades from replacing user data and keeps it out of the
; uninstall file log. Do not add production databases or photos here.

; ── Shortcuts ──────────────────────────────────────────────────────────────

[Icons]
; Desktop shortcut
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

; Start Menu shortcut
Name: "{userprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Tasks: startmenuicon

; Uninstall entry in Start Menu
Name: "{userprograms}\{#AppName}\Uninstall {#AppName}"; Filename: "{uninstallexe}"; Tasks: startmenuicon

; ── Run after install ──────────────────────────────────────────────────────

[Run]
Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

; ── Uninstall ──────────────────────────────────────────────────────────────

; Uninstall removes application files only. Retain attendance, photos and reports.

; ── Code section — create writable dirs if missing ─────────────────────────

[Dirs]
; Ensure reports and photos dirs exist on fresh install
Name: "{app}\reports"; Flags: uninsneveruninstall
Name: "{app}\reports\daily"; Flags: uninsneveruninstall
Name: "{app}\reports\monthly"; Flags: uninsneveruninstall
Name: "{app}\reports\student"; Flags: uninsneveruninstall
Name: "{app}\photos"; Flags: uninsneveruninstall
Name: "{app}\data"; Flags: uninsneveruninstall
