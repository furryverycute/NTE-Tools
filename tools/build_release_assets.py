from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.version import APP_NAME, APP_VERSION


APP_FOLDER_NAME = APP_NAME
PORTABLE_DIST = ROOT / 'dist' / APP_FOLDER_NAME
RELEASE_DIR = ROOT / 'release'
PORTABLE_ZIP = RELEASE_DIR / f'NTE-Tool-{APP_VERSION}-portable.zip'
INSTALLER_NAME = f'NTE-Tool-{APP_VERSION}-installer'
INSTALLER_EXE = RELEASE_DIR / f'{INSTALLER_NAME}.exe'
INNO_BUILD_DIR = ROOT / 'build' / 'inno'


def run(cmd: list[str]):
    subprocess.check_call(cmd, cwd=str(ROOT))


def remove_path(path: Path):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def zip_portable_folder():
    remove_path(PORTABLE_ZIP)
    with zipfile.ZipFile(PORTABLE_ZIP, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in PORTABLE_DIST.rglob('*'):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(PORTABLE_DIST.parent))


def build_portable():
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'nte_tool.spec'])
    if not (PORTABLE_DIST / f'{APP_NAME}.exe').exists():
        raise FileNotFoundError(f'Portable build output was not found: {PORTABLE_DIST}')
    zip_portable_folder()


def find_inno_compiler() -> Path:
    candidates = [
        os.environ.get('INNO_SETUP_COMPILER', ''),
        shutil.which('ISCC.exe') or '',
        r'C:\Program Files\Inno Setup 6\ISCC.exe',
        r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise FileNotFoundError('Inno Setup 6 compiler(ISCC.exe)을 찾을 수 없습니다.')


def quote_iss_path(path: Path) -> str:
    return str(path.resolve()).replace('\\', '\\\\')


def write_inno_script(vigem_installer: Path) -> Path:
    INNO_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    script_path = INNO_BUILD_DIR / 'nte_tool_setup.generated.iss'
    script = f'''#define MyAppName "{APP_NAME}"
#define MyAppVersion "{APP_VERSION}"
#define MyAppExeName "{APP_NAME}.exe"
#define SourceDir "{quote_iss_path(PORTABLE_DIST)}"
#define OutputDir "{quote_iss_path(RELEASE_DIR)}"
#define IconFile "{quote_iss_path(ROOT / 'app' / 'assets' / 'icon.ico')}"
#define VigEmInstaller "{quote_iss_path(vigem_installer)}"
#define VigEmInstallerName "{vigem_installer.name}"

[Setup]
AppId={{{{1B69B5D6-0B08-4F4D-9C2E-07E142000001}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher=furryverycute
AppPublisherURL=https://github.com/furryverycute/NTE-Tools
AppSupportURL=https://github.com/furryverycute/NTE-Tools/issues
AppUpdatesURL=https://github.com/furryverycute/NTE-Tools/releases
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir={{#OutputDir}}
OutputBaseFilename=NTE-Tool-{{#MyAppVersion}}-installer
SetupIconFile={{#IconFile}}
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면 바로 가기 만들기"; GroupDescription: "추가 작업:"; Flags: unchecked

[Files]
Source: "{{#SourceDir}}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{{#VigEmInstaller}}"; DestDir: "{{tmp}}"; DestName: "{{#VigEmInstallerName}}"; Flags: deleteafterinstall

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{tmp}}\\{{#VigEmInstallerName}}"; Parameters: "/quiet /norestart"; StatusMsg: "가상 컨트롤러 드라이버를 설치하는 중입니다..."; Flags: waituntilterminated runhidden
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{#MyAppName}} 실행"; Flags: nowait postinstall skipifsilent

[Code]
var
  DependencyPage: TWizardPage;
  AgreeCheck: TNewCheckBox;
  ForceExit: Boolean;

procedure InitializeWizard;
var
  Body: TNewStaticText;
begin
  DependencyPage := CreateCustomPage(wpWelcome, '필수 런타임 설치 동의', 'NTE Tool 가방 자동 스캔에 필요한 구성 요소입니다.');

  Body := TNewStaticText.Create(DependencyPage);
  Body.Parent := DependencyPage.Surface;
  Body.Left := 0;
  Body.Top := 0;
  Body.Width := DependencyPage.SurfaceWidth;
  Body.Height := ScaleY(170);
  Body.WordWrap := True;
  Body.Caption :=
    'NTE Tool 설치에는 다음 구성 요소가 포함됩니다:' + #13#10#13#10 +
    '1. ViGEmBus 가상 컨트롤러 드라이버' + #13#10 +
    '   - 가방 자동 스캔 중 게임 UI를 이동하기 위해 필요합니다.' + #13#10#13#10 +
    '2. Tesseract OCR 런타임' + #13#10 +
    '   - 스캔한 장비 옵션을 읽기 위해 필요하며, 앱 폴더에 함께 설치됩니다.' + #13#10#13#10 +
    '동의하지 않으면 NTE Tool 설치를 진행할 수 없습니다.';

  AgreeCheck := TNewCheckBox.Create(DependencyPage);
  AgreeCheck.Parent := DependencyPage.Surface;
  AgreeCheck.Left := 0;
  AgreeCheck.Top := Body.Top + Body.Height + ScaleY(8);
  AgreeCheck.Width := DependencyPage.SurfaceWidth;
  AgreeCheck.Height := ScaleY(36);
  AgreeCheck.Caption := '위 필수 구성 요소 설치에 동의합니다.';
  AgreeCheck.Checked := False;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DependencyPage.ID then
  begin
    if not AgreeCheck.Checked then
    begin
      MsgBox('필수 구성 요소 설치에 동의하지 않아 설치를 종료합니다.', mbInformation, MB_OK);
      ForceExit := True;
      WizardForm.Close;
      Result := False;
    end;
  end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if ForceExit then
    Confirm := False;
end;
'''
    script_path.write_text(script, encoding='utf-8-sig')
    return script_path


def build_installer():
    remove_path(INSTALLER_EXE)
    from app.scanner.runtime_setup import ensure_controller_installer

    vigem_installer = ensure_controller_installer(download=True)
    if not vigem_installer:
        raise FileNotFoundError('ViGEmBus installer was not prepared.')
    script_path = write_inno_script(Path(vigem_installer))
    inno = find_inno_compiler()
    run([str(inno), str(script_path)])
    if not INSTALLER_EXE.exists():
        raise FileNotFoundError(f'Installer build output was not found: {INSTALLER_EXE}')


def main() -> int:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    build_portable()
    build_installer()
    print('Release assets ready:')
    print(f'  {PORTABLE_ZIP}')
    print(f'  {INSTALLER_EXE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
