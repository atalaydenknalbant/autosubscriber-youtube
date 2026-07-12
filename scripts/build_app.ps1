$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,

        [Parameter(Mandatory = $false)]
        [string]$Description = "Native command"
    )

    & $Command

    $ExitCode = $LASTEXITCODE

    if ($ExitCode -ne 0) {
        throw "$Description failed with exit code $ExitCode"
    }
}

$BuildPython = Join-Path `
    $RepoRoot `
    ".build_venv\Scripts\python.exe"

$RequirementsFile = Join-Path `
    $RepoRoot `
    "requirements.txt"

$AppRequirementsFile = Join-Path `
    $RepoRoot `
    "requirements-app.txt"

$SpecFile = Join-Path `
    $RepoRoot `
    "autosubscriber_app.spec"

$RuntimeHook = Join-Path `
    $RepoRoot `
    "scripts\pyinstaller_transformers_runtime.py"

$BuildDirectory = Join-Path `
    $RepoRoot `
    "build"

$DistDirectory = Join-Path `
    $RepoRoot `
    "dist"

$DistExecutable = Join-Path `
    $DistDirectory `
    "AutosubscriberApp.exe"

$LegacyDistConfig = Join-Path `
    $RepoRoot `
    "dist\AutosubscriberApp\config.ini"

$DistConfig = Join-Path `
    $DistDirectory `
    "config.ini"

$UserDataDirectory = Join-Path `
    $env:LOCALAPPDATA `
    "AutosubscriberApp"

$PreviousUserConfig = Join-Path `
    $UserDataDirectory `
    "config.ini"

Write-Host ""
Write-Host "Autosubscriber application build"
Write-Host "Repository: $RepoRoot"
Write-Host ""

if (-not (Test-Path -LiteralPath $BuildPython)) {
    Write-Host "Creating the build virtual environment..."

    Invoke-NativeCommand `
        -Description "Virtual environment creation" `
        -Command {
            python -m venv .build_venv
        }
}

if (-not (Test-Path -LiteralPath $BuildPython)) {
    throw "Build Python was not created: $BuildPython"
}

if (-not (Test-Path -LiteralPath $RequirementsFile)) {
    throw "Requirements file was not found: $RequirementsFile"
}

if (-not (Test-Path -LiteralPath $AppRequirementsFile)) {
    throw "Application requirements file was not found: $AppRequirementsFile"
}

if (-not (Test-Path -LiteralPath $SpecFile)) {
    throw "PyInstaller spec file was not found: $SpecFile"
}

if (-not (Test-Path -LiteralPath $RuntimeHook)) {
    throw "PyInstaller runtime hook was not found: $RuntimeHook"
}

$ConfigSource = $null

if (Test-Path -LiteralPath $DistConfig) {
    $ConfigSource = $DistConfig
}
elseif (Test-Path -LiteralPath $LegacyDistConfig) {
    $ConfigSource = $LegacyDistConfig
}
elseif (Test-Path -LiteralPath $PreviousUserConfig) {
    $ConfigSource = $PreviousUserConfig
}

if ($ConfigSource -and $ConfigSource -ne $DistConfig) {
    Write-Host "Migrating the existing configuration beside the executable..."

    New-Item `
        -ItemType Directory `
        -Path $DistDirectory `
        -Force | Out-Null

    Copy-Item `
        -LiteralPath $ConfigSource `
        -Destination $DistConfig `
        -Force
}

Write-Host "Updating pip..."

Invoke-NativeCommand `
    -Description "pip update" `
    -Command {
        & $BuildPython -m pip install --upgrade pip
    }

Write-Host "Installing main requirements..."

Invoke-NativeCommand `
    -Description "Main requirements installation" `
    -Command {
        & $BuildPython -m pip install `
            -r $RequirementsFile
    }

Write-Host "Installing application requirements..."

Invoke-NativeCommand `
    -Description "Application requirements installation" `
    -Command {
        & $BuildPython -m pip install `
            -r $AppRequirementsFile
    }

Write-Host "Installing packaging and tokenizer dependencies..."

Invoke-NativeCommand `
    -Description "Packaging dependencies installation" `
    -Command {
        & $BuildPython -m pip install --upgrade `
            "protobuf>=4.25.0,<7" `
            sentencepiece `
            pyinstaller `
            pyinstaller-hooks-contrib
    }

Write-Host "Checking installed dependency consistency..."

Invoke-NativeCommand `
    -Description "pip dependency check" `
    -Command {
        & $BuildPython -m pip check
    }

$VerificationScript = Join-Path `
    ([System.IO.Path]::GetTempPath()) `
    "verify_autosubscriber_build_$PID.py"

$VerificationCode = @'
import sys
from importlib.metadata import PackageNotFoundError, version

import google.protobuf
import sentencepiece
import sentencepiece._sentencepiece

try:
    import google._upb._message as upb_message
except ImportError:
    upb_message = None

from transformers.utils import (
    is_protobuf_available,
    is_sentencepiece_available,
)

from transformers.models.xlm_roberta.tokenization_xlm_roberta import (
    XLMRobertaTokenizer,
)


def get_distribution_version(distribution_name: str) -> str:
    try:
        return version(distribution_name)
    except PackageNotFoundError as error:
        raise RuntimeError(
            f"Distribution metadata is missing for {distribution_name}."
        ) from error


protobuf_version = get_distribution_version("protobuf")
sentencepiece_version = get_distribution_version("sentencepiece")
transformers_version = get_distribution_version("transformers")
pyinstaller_version = get_distribution_version("pyinstaller")

print("Build Python:", sys.executable)
print("Python version:", sys.version)
print("Protobuf version:", protobuf_version)
print("Protobuf module:", google.protobuf.__file__)
print("SentencePiece version:", sentencepiece_version)
print("SentencePiece module:", sentencepiece.__file__)
print(
    "SentencePiece native extension:",
    sentencepiece._sentencepiece.__file__,
)
print(
    "UPB native extension:",
    getattr(upb_message, "__file__", "not loaded"),
)
print("Transformers version:", transformers_version)
print("PyInstaller version:", pyinstaller_version)
print(
    "Transformers detects protobuf:",
    is_protobuf_available(),
)
print(
    "Transformers detects SentencePiece:",
    is_sentencepiece_available(),
)
print(
    "XLM RoBERTa tokenizer:",
    XLMRobertaTokenizer.__module__,
)

if not is_protobuf_available():
    raise RuntimeError(
        "Transformers cannot detect protobuf in the build environment."
    )

if not is_sentencepiece_available():
    raise RuntimeError(
        "Transformers cannot detect SentencePiece in the build environment."
    )

if upb_message is None:
    raise RuntimeError(
        "The protobuf UPB native extension could not be imported."
    )

print("Dependency verification completed successfully.")
'@

try {
    Write-Host "Verifying protobuf and SentencePiece..."

    Set-Content `
        -LiteralPath $VerificationScript `
        -Value $VerificationCode `
        -Encoding UTF8

    Invoke-NativeCommand `
        -Description "Dependency verification" `
        -Command {
            & $BuildPython $VerificationScript
        }
}
finally {
    Remove-Item `
        -LiteralPath $VerificationScript `
        -Force `
        -ErrorAction SilentlyContinue
}

Write-Host "Removing previous build output..."

Remove-Item `
    -LiteralPath $BuildDirectory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

Remove-Item `
    -LiteralPath $DistExecutable `
    -Force `
    -ErrorAction SilentlyContinue

Remove-Item `
    -LiteralPath (Split-Path -Parent $LegacyDistConfig) `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

Write-Host "Building the application with PyInstaller..."

Invoke-NativeCommand `
    -Description "PyInstaller build" `
    -Command {
        & $BuildPython -m PyInstaller `
            $SpecFile `
            --clean `
            --noconfirm
    }

if (-not (Test-Path -LiteralPath $DistExecutable)) {
    throw "Build finished, but the executable was not found: $DistExecutable"
}

Write-Host "Checking dependencies inside the single executable..."

Invoke-NativeCommand `
    -Description "Packaged runtime verification" `
    -Command {
        & $DistExecutable --worker --check-runtime
    }

$WarningFile = Join-Path `
    $BuildDirectory `
    "autosubscriber_app\warn-autosubscriber_app.txt"

$CriticalWarnings = @()

if (Test-Path -LiteralPath $WarningFile) {
    $CriticalWarnings = Select-String `
        -LiteralPath $WarningFile `
        -Pattern '^missing module named (google[.]protobuf|google[.]_upb|sentencepiece) -' `
        -ErrorAction SilentlyContinue

    if ($CriticalWarnings) {
        Write-Host ""
        Write-Warning "Potential protobuf or SentencePiece warnings were detected:"

        foreach ($Warning in $CriticalWarnings) {
            Write-Warning $Warning.Line
        }

    }
}

if ($CriticalWarnings) {
    throw "Critical packaging warnings were detected."
}

Remove-Item `
    -LiteralPath $BuildDirectory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

$DistFiles = @(
    Get-ChildItem `
        -LiteralPath $DistDirectory `
        -Recurse `
        -File
)

$AllowedDistFiles = @(
    $DistExecutable
    $DistConfig
)

$UnexpectedDistFiles = @(
    $DistFiles | Where-Object { $_.FullName -notin $AllowedDistFiles }
)

$DistDirectories = @(
    Get-ChildItem `
        -LiteralPath $DistDirectory `
        -Recurse `
        -Directory
)

if ($UnexpectedDistFiles.Count -or $DistDirectories.Count) {
    throw "The dist directory contains unexpected application library files."
}

$ExecutableInfo = Get-Item `
    -LiteralPath $DistExecutable

Write-Host ""
Write-Host "Build completed successfully."
Write-Host "Executable: $($ExecutableInfo.FullName)"
Write-Host "Size: $($ExecutableInfo.Length) bytes"
Write-Host "Modified: $($ExecutableInfo.LastWriteTime)"
Write-Host ""
Write-Host "Portable config: $DistConfig"
Write-Host "Application libraries are bundled inside the executable."
Write-Host ""
