[Setup]
AppName=Jewelry Billing System
AppVersion=1.0.0
AppPublisher=Your Company
DefaultDirName={autopf}\JewelryBillingSystem
DefaultGroupName=Jewelry Billing System
OutputDir=C:\Users\Dell\Desktop\JBS_Installer
OutputBaseFilename=JewelryBillingSystem_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "C:\Users\Dell\OneDrive\Desktop\code\JewelryBillingSystem\jewelry_billing_system\dist\JewelryBillingSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Jewelry Billing System"; Filename: "{app}\JewelryBillingSystem.exe"
Name: "{commondesktop}\Jewelry Billing System"; Filename: "{app}\JewelryBillingSystem.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\JewelryBillingSystem.exe"; Description: "Launch Jewelry Billing System"; Flags: nowait postinstall
