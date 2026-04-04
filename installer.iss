[Setup]
AppName=Jewelry Billing System
AppVersion=1.0.0
DefaultDirName={autopf}\JewelryBillingSystem
DefaultGroupName=Jewelry Billing System
OutputDir=C:\Users\Dell\Desktop\JBS_Installer
OutputBaseFilename=JewelryBillingSystem_Setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "C:\Users\Dell\OneDrive\Desktop\code\JewelryBillingSystem\jewelry_billing_system\dist\JewelryBillingSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Jewelry Billing System"; Filename: "{app}\JewelryBillingSystem.exe"
Name: "{commondesktop}\Jewelry Billing System"; Filename: "{app}\JewelryBillingSystem.exe"

[Run]
Filename: "{app}\JewelryBillingSystem.exe"; Flags: nowait postinstall
