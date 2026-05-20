; ============================================================
; Inno Setup Script — Jewelry Billing System Installer
; Requires Inno Setup 6: https://jrsoftware.org/isinfo.php
; ============================================================

[Setup]
; AppId MUST stay the same across all versions so upgrades work correctly
AppId={{F3A8C2D1-7B4E-4F2A-9C0E-1D5E8A3F6B2C}
AppName=Jewelry Billing System
AppVersion=1.0.0
AppVerName=Jewelry Billing System 1.0.0
AppPublisher=Jewelry Billing System
DefaultDirName={autopf}\JewelryBillingSystem
DefaultGroupName=Jewelry Billing System
OutputDir=installer_output
OutputBaseFilename=JewelryBillingSystem_Setup_v1.0.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Windows 7 SP1 and later (covers Win 7, 8, 8.1, 10, 11)
MinVersion=6.1.7601
; Admin rights required to write to Program Files
PrivilegesRequired=admin
; Uninstall info shown in Add/Remove Programs
UninstallDisplayName=Jewelry Billing System
UninstallDisplayIcon={app}\JewelryBillingSystem.exe
; Prevent multiple instances of installer running at once
AppMutex=JewelryBillingSystemInstaller

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\JewelryBillingSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\Jewelry Billing System";           Filename: "{app}\JewelryBillingSystem.exe"
Name: "{group}\Uninstall Jewelry Billing System"; Filename: "{uninstallexe}"
; Desktop shortcut — ALWAYS created for all users, no opt-out checkbox
Name: "{commondesktop}\Jewelry Billing System";   Filename: "{app}\JewelryBillingSystem.exe"

[Run]
Filename: "{app}\JewelryBillingSystem.exe"; Description: "Launch Jewelry Billing System now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove only the app install folder.
; NEVER touches C:\JewelryBillingSystem\ — that is the client's data folder.
Type: filesandordirs; Name: "{app}"
