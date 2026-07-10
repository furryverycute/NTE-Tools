param(
    [string]$SourceDir = '',
    [string]$TargetDir = '',
    [switch]$Force,
    [switch]$NoDownload
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptDir
if ([string]::IsNullOrWhiteSpace($TargetDir)) {
    $TargetDir = Join-Path $ProjectRoot 'tools\tesseract'
}

$TessdataFastBase = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main'
$RequiredLangs = @('eng', 'kor')

function Write-Step([string]$Text) {
    Write-Host "[Portable Tesseract] $Text"
}

function Find-InstalledTesseractDir {
    $candidates = New-Object System.Collections.Generic.List[string]

    if ($SourceDir -and (Test-Path (Join-Path $SourceDir 'tesseract.exe'))) {
        $candidates.Add($SourceDir)
    }

    $cmd = Get-Command tesseract.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        $candidates.Add((Split-Path -Parent $cmd.Source))
    }

    $paths = @(
        "$env:ProgramFiles\Tesseract-OCR",
        "${env:ProgramFiles(x86)}\Tesseract-OCR",
        "$env:LOCALAPPDATA\Programs\Tesseract-OCR",
        "$env:ProgramData\scoop\apps\tesseract\current",
        "$env:ProgramData\chocolatey\lib\tesseract\tools"
    ) | Where-Object { $_ -and ($_ -notmatch '^\\Tesseract-OCR') }

    foreach ($p in $paths) { $candidates.Add($p) }

    foreach ($p in $candidates) {
        if ($p -and (Test-Path (Join-Path $p 'tesseract.exe'))) {
            return (Resolve-Path $p).Path
        }
    }
    return $null
}

function Copy-TesseractTree([string]$Source, [string]$Target) {
    if (!(Test-Path (Join-Path $Source 'tesseract.exe'))) {
        throw "Source does not contain tesseract.exe: $Source"
    }
    if (!(Test-Path $Target)) {
        New-Item -ItemType Directory -Force -Path $Target | Out-Null
    }

    Write-Step "Copying runtime files from: $Source"
    Write-Step "Target: $Target"

    Get-ChildItem -Path $Source -File | Where-Object {
        $_.Name -ieq 'tesseract.exe' -or $_.Extension -ieq '.dll'
    } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination (Join-Path $Target $_.Name) -Force
    }

    $sourceTessdata = Join-Path $Source 'tessdata'
    $targetTessdata = Join-Path $Target 'tessdata'
    if (Test-Path $sourceTessdata) {
        if (!(Test-Path $targetTessdata)) {
            New-Item -ItemType Directory -Force -Path $targetTessdata | Out-Null
        }
        foreach ($lang in $RequiredLangs) {
            $sourceFile = Join-Path $sourceTessdata "$lang.traineddata"
            if (Test-Path $sourceFile) {
                Copy-Item -Path $sourceFile -Destination (Join-Path $targetTessdata "$lang.traineddata") -Force
            }
        }
    }
}

function Download-File([string]$Url, [string]$OutFile) {
    if ($NoDownload) { throw "Download disabled: $Url" }
    $parent = Split-Path -Parent $OutFile
    if ($parent -and !(Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Write-Step "Downloading: $Url"
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
    } catch {
        if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
            Start-BitsTransfer -Source $Url -Destination $OutFile
        } else {
            throw
        }
    }
}

function Ensure-LanguageData([string]$Target) {
    $tessdata = Join-Path $Target 'tessdata'
    if (!(Test-Path $tessdata)) { New-Item -ItemType Directory -Force -Path $tessdata | Out-Null }
    foreach ($lang in $RequiredLangs) {
        $file = Join-Path $tessdata "$lang.traineddata"
        $needsDownload = $Force -or !(Test-Path $file) -or ((Get-Item $file -ErrorAction SilentlyContinue).Length -lt 1024)
        if ($needsDownload) {
            Download-File "$TessdataFastBase/$lang.traineddata" $file
        } else {
            Write-Step "Language data exists: $lang.traineddata"
        }
    }
}

function Test-Portable([string]$Target) {
    $exe = Join-Path $Target 'tesseract.exe'
    $tessdata = Join-Path $Target 'tessdata'
    $eng = Join-Path $tessdata 'eng.traineddata'
    $kor = Join-Path $tessdata 'kor.traineddata'
    $hangul = Join-Path $tessdata 'Hangul.traineddata'

    if (!(Test-Path $exe)) { throw "Missing: $exe" }
    if (!(Test-Path $eng)) { throw 'Missing: eng.traineddata' }
    if (!(Test-Path $kor) -and !(Test-Path $hangul)) { throw 'Missing: kor.traineddata or Hangul.traineddata' }

    Write-Step 'Verifying portable Tesseract...'

    # Tesseract 5.5 Windows builds can crash with std::filesystem_error when
    # --list-langs receives a tessdata path containing non-ASCII characters
    # such as Korean folder names.  The engine itself was already copied, so
    # setup verification should not fail only because the project path is
    # non-ASCII.  Verify the executable with --version, then verify language
    # data by file existence.  Only run --list-langs on ASCII paths.
    $versionOutput = (& $exe --version 2>&1 | Select-Object -First 1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($versionOutput)) {
        throw "Tesseract executable verification failed: $exe"
    }
    Write-Host $versionOutput

    $pathForTesseract = "$exe`t$tessdata"
    $containsNonAscii = $pathForTesseract -cmatch '[^\u0000-\u007F]'

    if ($containsNonAscii) {
        Write-Step 'Project path contains non-ASCII characters. Skipping --list-langs to avoid Tesseract filesystem crash.'
        Write-Step 'Language verification uses traineddata file check instead.'
        return
    }

    try {
        $langs = (& $exe --tessdata-dir $tessdata --list-langs 2>&1 | Out-String)
        if ($LASTEXITCODE -ne 0) {
            throw "--list-langs exited with code $LASTEXITCODE"
        }
        foreach ($lang in $RequiredLangs) {
            if ($lang -eq 'kor') {
                if (($langs -notmatch '(?m)^kor$') -and ($langs -notmatch '(?m)^Hangul$')) {
                    throw 'Language verification failed: kor or Hangul'
                }
            } elseif ($langs -notmatch "(?m)^$lang$") {
                throw "Language verification failed: $lang"
            }
        }
    } catch {
        Write-Step "Warning: --list-langs verification failed, but required traineddata files exist. Continuing. ($($_.Exception.Message))"
    }
}

try {
    Write-Step 'This script does not run the Tesseract installer and does not require admin rights.'
    Write-Step "Project portable target: $TargetDir"

    $already = Test-Path (Join-Path $TargetDir 'tesseract.exe')
    if ($already -and -not $Force) {
        Write-Step 'Existing portable engine found. Skipping engine copy.'
    } else {
        $source = Find-InstalledTesseractDir
        if (-not $source) {
            throw @"
No existing Tesseract folder was found.

Use one of these methods:
1. Copy a complete Tesseract folder into:
   $TargetDir
   Required files:
   - tesseract.exe
   - DLL files beside tesseract.exe
   - tessdata\eng.traineddata
   - tessdata\kor.traineddata

2. If Tesseract is already installed elsewhere, run:
   setup.bat "C:\path\to\Tesseract-OCR"
"@
        }
        Copy-TesseractTree $source $TargetDir
    }

    Ensure-LanguageData $TargetDir
    Test-Portable $TargetDir

    Write-Step "OK: portable Tesseract is ready."
    exit 0
} catch {
    Write-Host ''
    Write-Host '[ERROR] Portable Tesseract setup failed.' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
