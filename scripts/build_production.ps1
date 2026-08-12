param(
    [switch]$RecreateEnvironment,
    [switch]$BuildInstaller,
    [switch]$SkipArtifactSmokeTest,
    [switch]$PackageExistingArtifact
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildVenv = Join-Path $ProjectRoot ".venv-build"
$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"
$ModelBundle = Join-Path $ProjectRoot "resources\models\vieneu-v3"
$LockFile = Join-Path $ProjectRoot "requirements\production.lock"
$DistDirectory = Join-Path $ProjectRoot "dist\GPHI-TTS"
$ReleaseDirectory = Join-Path $ProjectRoot "release"
$Version = "0.1.0"

Set-Location -LiteralPath $ProjectRoot

if (-not (Test-Path -LiteralPath (Join-Path $ModelBundle "manifest.json") -PathType Leaf)) {
    throw "Missing model bundle. Run: .venv\Scripts\python scripts\prepare_vieneu_v3.py"
}
if (-not (Test-Path -LiteralPath $LockFile -PathType Leaf)) {
    throw "Missing requirements\production.lock. Refusing to build from unlocked dependencies."
}

if ($PackageExistingArtifact -and $RecreateEnvironment) {
    throw "Do not use -PackageExistingArtifact together with -RecreateEnvironment."
}

if ($RecreateEnvironment -and (Test-Path -LiteralPath $BuildVenv)) {
    $ResolvedBuildVenv = (Resolve-Path -LiteralPath $BuildVenv).Path
    if (-not $ResolvedBuildVenv.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a virtual environment outside the project."
    }
    Remove-Item -LiteralPath $ResolvedBuildVenv -Recurse -Force
}

if (-not $PackageExistingArtifact) {
    if (-not (Test-Path -LiteralPath $BuildPython -PathType Leaf)) {
        py -3.11 -m venv $BuildVenv
    }

    & $BuildPython -c "import sys; assert sys.version_info[:2] == (3, 11), sys.version"
    & $BuildPython -m pip install --upgrade "pip==26.1.1"
    & $BuildPython -m pip install --require-hashes -r $LockFile
    & $BuildPython -m pip install --no-deps --no-build-isolation $ProjectRoot
    & $BuildPython -c "import torch; assert '+cu128' in torch.__version__, torch.__version__"
    & $BuildPython (Join-Path $ProjectRoot "scripts\prepare_vieneu_v3.py") --destination $ModelBundle --validate-only

    $env:VNTTS_ENVIRONMENT = "production"
    $env:VNTTS_LOG_LEVEL = "INFO"
    & $BuildPython -m PyInstaller --noconfirm --clean (Join-Path $ProjectRoot "packaging\vntts.spec")
}
else {
    Write-Warning "Packaging the existing dist\GPHI-TTS artifact; dependencies and PyInstaller will not run again."
}

$Executable = Join-Path $DistDirectory "GPHI-TTS.exe"
$BundledManifest = Join-Path $DistDirectory "_internal\resources\models\vieneu-v3\manifest.json"
$BundledG2PData = Join-Path $DistDirectory "_internal\sea_g2p\sea_g2p.bin"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "PyInstaller did not create GPHI-TTS.exe."
}
if (-not (Test-Path -LiteralPath $BundledManifest -PathType Leaf)) {
    throw "Artifact is missing the model manifest."
}
if (-not (Test-Path -LiteralPath $BundledG2PData -PathType Leaf)) {
    throw "Artifact is missing sea_g2p.bin required for synthesis."
}

if (-not $SkipArtifactSmokeTest) {
    $SmokeDirectory = Join-Path $ProjectRoot "build\production-smoke"
    $SmokeWav = Join-Path $SmokeDirectory "smoke.wav"
    $SmokeMp3 = Join-Path $SmokeDirectory "smoke.mp3"
    New-Item -ItemType Directory -Path $SmokeDirectory -Force | Out-Null
    foreach ($SmokeOutput in @($SmokeWav, $SmokeMp3)) {
        if (Test-Path -LiteralPath $SmokeOutput) {
            Remove-Item -LiteralPath $SmokeOutput -Force
        }
    }
    $SmokeProcess = Start-Process `
        -FilePath $Executable `
        -ArgumentList @("--production-smoke", "`"$SmokeWav`"") `
        -Wait `
        -PassThru `
        -WindowStyle Hidden
    if ($SmokeProcess.ExitCode -ne 0) {
        throw "Real synthesis smoke test with GPHI-TTS.exe failed."
    }
    if (-not (Test-Path -LiteralPath $SmokeWav -PathType Leaf) -or (Get-Item -LiteralPath $SmokeWav).Length -le 44) {
        throw "Smoke test did not create a valid WAV file."
    }
    if (-not (Test-Path -LiteralPath $SmokeMp3 -PathType Leaf) -or (Get-Item -LiteralPath $SmokeMp3).Length -le 128) {
        throw "Smoke test did not create a valid MP3 file."
    }
    Write-Host "Smoke test artifact: WAV + MP3 OK"

    $CudaAvailable = (& $BuildPython -c "import torch; print('1' if torch.cuda.is_available() else '0')").Trim() -eq "1"
    if ($CudaAvailable) {
        $GpuSmokeWav = Join-Path $SmokeDirectory "smoke-gpu.wav"
        $GpuSmokeMp3 = Join-Path $SmokeDirectory "smoke-gpu.mp3"
        foreach ($SmokeOutput in @($GpuSmokeWav, $GpuSmokeMp3)) {
            if (Test-Path -LiteralPath $SmokeOutput) {
                Remove-Item -LiteralPath $SmokeOutput -Force
            }
        }
        $GpuSmokeProcess = Start-Process `
            -FilePath $Executable `
            -ArgumentList @("--production-smoke", "`"$GpuSmokeWav`"", "cuda") `
            -Wait `
            -PassThru `
            -WindowStyle Hidden
        if ($GpuSmokeProcess.ExitCode -ne 0) {
            throw "PyTorch/CUDA smoke test with GPHI-TTS.exe failed."
        }
        if (-not (Test-Path -LiteralPath $GpuSmokeWav -PathType Leaf) -or (Get-Item -LiteralPath $GpuSmokeWav).Length -le 44) {
            throw "GPU smoke test did not create a valid WAV file."
        }
        if (-not (Test-Path -LiteralPath $GpuSmokeMp3 -PathType Leaf) -or (Get-Item -LiteralPath $GpuSmokeMp3).Length -le 128) {
            throw "GPU smoke test did not create a valid MP3 file."
        }
        Write-Host "Smoke test artifact PyTorch/CUDA: WAV + MP3 OK"
    }
    else {
        Write-Host "CUDA is unavailable on the build machine; ONNX/CPU fallback was verified."
    }
}
else {
    Write-Warning "EXE smoke test was skipped. Test the ZIP on a Windows machine that permits the app before release."
}

# PyInstaller's windowed executable can retain a short-lived read lock after
# the smoke process exits. This wait is unnecessary when no EXE was launched;
# antivirus scanners may allow archive reads while denying exclusive access.
if (-not $SkipArtifactSmokeTest) {
    $ExecutableUnlocked = $false
    for ($Attempt = 1; $Attempt -le 24; $Attempt++) {
        try {
            $Probe = [System.IO.File]::Open(
                $Executable,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::None
            )
            $Probe.Dispose()
            $ExecutableUnlocked = $true
            break
        }
        catch [System.IO.IOException] {
            if ($Attempt -lt 24) {
                Start-Sleep -Seconds 5
            }
        }
    }
    if (-not $ExecutableUnlocked) {
        throw "GPHI-TTS.exe is still locked after 120 seconds. Close the app and build again."
    }
}

New-Item -ItemType Directory -Path $ReleaseDirectory -Force | Out-Null
$PortableArchive = Join-Path $ReleaseDirectory "GPHI-TTS-$Version-win-x64.zip"
if (Test-Path -LiteralPath $PortableArchive) {
    Remove-Item -LiteralPath $PortableArchive -Force
}
$ArchiveCreated = $false
for ($Attempt = 1; $Attempt -le 3; $Attempt++) {
    try {
        if (Test-Path -LiteralPath $PortableArchive) {
            Remove-Item -LiteralPath $PortableArchive -Force
        }
        Compress-Archive -LiteralPath $DistDirectory -DestinationPath $PortableArchive -CompressionLevel Optimal -ErrorAction Stop
        $ArchiveCreated = $true
        break
    }
    catch {
        if ($Attempt -lt 3) {
            Write-Warning "Artifact compression failed because a file is busy; retry $($Attempt + 1)/3."
            Start-Sleep -Seconds 5
        }
    }
}
if (-not $ArchiveCreated) {
    # Compress-Archive requests restrictive sharing on Windows and can fail
    # while antivirus is scanning a readable unsigned EXE. bsdtar uses normal
    # shared reads and is included with supported Windows versions.
    $Tar = Get-Command tar.exe -ErrorAction SilentlyContinue
    if ($null -ne $Tar) {
        if (Test-Path -LiteralPath $PortableArchive) {
            Remove-Item -LiteralPath $PortableArchive -Force
        }
        Write-Warning "Compress-Archive could not read the scanned EXE; falling back to Windows tar.exe."
        & $Tar.Source -a -c -f $PortableArchive -C (Split-Path $DistDirectory -Parent) (Split-Path $DistDirectory -Leaf)
        $ArchiveCreated = $LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $PortableArchive -PathType Leaf)
    }
}
if (-not $ArchiveCreated) {
    throw "Unable to create the production archive."
}
Get-FileHash -LiteralPath $PortableArchive -Algorithm SHA256 |
    ForEach-Object { "$($_.Hash.ToLower())  $([IO.Path]::GetFileName($PortableArchive))" } |
    Set-Content -LiteralPath "$PortableArchive.sha256" -Encoding ascii

if ($BuildInstaller) {
    $InnoCompiler = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($null -eq $InnoCompiler) {
        throw "Inno Setup iscc.exe was not found."
    }
    & $InnoCompiler.Source (Join-Path $ProjectRoot "packaging\windows\installer.iss")
}

Write-Host "Artifact portable: $PortableArchive"
if ($SkipArtifactSmokeTest) {
    Write-Warning "Artifact was not smoke-tested on this build machine because -SkipArtifactSmokeTest was used."
}
else {
    Write-Host "Artifact synthesis smoke test passed."
}
Write-Host "Test the artifact on a clean offline Windows machine before release."
