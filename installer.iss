[Setup]
AppName=Jewelry Billing System
AppVersion=1.0.0
AppPublisher=Jewelry Billing System
DefaultDirName={autopf}\JewelryBillingSystem
DefaultGroupName=Jewelry Billing System
OutputBaseFilename=JewelryBillingSystem_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop Shortcut"

[Files]
Source: "dist\JewelryBillingSystem.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\Jewelry Billing System"; Filename: "{app}\JewelryBillingSystem.exe"
Name: "{autodesktop}\Jewelry Billing System"; Filename: "{app}\JewelryBillingSystem.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\JewelryBillingSystem.exe"; Description: "Launch Jewelry Billing System"; Flags: nowait postinstall skipifsilent