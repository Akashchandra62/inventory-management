; ============================================================
; Inno Setup Script — Jewelry Billing System Installer
; ============================================================

[Setup]
AppName=Jewelry Billing System
AppVersion=1.0.0
AppPublisher=Jewelry Billing System
AppPublisherURL=
DefaultDirName={autopf}\JewelryBillingSystem
DefaultGroupName=Jewelry Billing System
OutputDir=installer_output
OutputBaseFilename=JewelryBillingSystem_Setup_v1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstall info
UninstallDisplayName=Jewelry Billing System
UninstallDisplayIcon={app}\JewelryBillingSystem.exe
; Prevent multiple instances of installer
AppMutex=JewelryBillingSystemInstaller

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\JewelryBillingSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Jewelry Billing System";           Filename: "{app}\JewelryBillingSystem.exe"
Name: "{group}\Uninstall Jewelry Billing System"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Jewelry Billing System";     Filename: "{app}\JewelryBillingSystem.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\JewelryBillingSystem.exe"; Description: "Launch Jewelry Billing System now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up only app folder — never touch C:\JewelryBillingSystem (client data)
Type: filesandordirs; Name: "{app}"
