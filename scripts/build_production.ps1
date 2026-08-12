param(
    [switch]$RecreateEnvironment,
    [switch]$BuildInstaller
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
    throw "Thiếu model bundle. Chạy: .venv\Scripts\python scripts\prepare_vieneu_v3.py"
}
if (-not (Test-Path -LiteralPath $LockFile -PathType Leaf)) {
    throw "Thiếu requirements\production.lock. Không build từ dependency chưa khóa."
}

if ($RecreateEnvironment -and (Test-Path -LiteralPath $BuildVenv)) {
    $ResolvedBuildVenv = (Resolve-Path -LiteralPath $BuildVenv).Path
    if (-not $ResolvedBuildVenv.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Từ chối xóa virtual environment ngoài project."
    }
    Remove-Item -LiteralPath $ResolvedBuildVenv -Recurse -Force
}

if (-not (Test-Path -LiteralPath $BuildPython -PathType Leaf)) {
    py -3.11 -m venv $BuildVenv
}

& $BuildPython -c "import sys; assert sys.version_info[:2] == (3, 11), sys.version"
& $BuildPython -m pip install --upgrade "pip==26.1.1"
& $BuildPython -m pip install --require-hashes -r $LockFile
& $BuildPython -m pip install --no-deps --no-build-isolation $ProjectRoot
& $BuildPython (Join-Path $ProjectRoot "scripts\prepare_vieneu_v3.py") --destination $ModelBundle --validate-only

$env:VNTTS_ENVIRONMENT = "production"
$env:VNTTS_LOG_LEVEL = "INFO"
& $BuildPython -m PyInstaller --noconfirm --clean (Join-Path $ProjectRoot "packaging\vntts.spec")

$Executable = Join-Path $DistDirectory "GPHI-TTS.exe"
$BundledManifest = Join-Path $DistDirectory "_internal\resources\models\vieneu-v3\manifest.json"
$BundledG2PData = Join-Path $DistDirectory "_internal\sea_g2p\sea_g2p.bin"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "PyInstaller không tạo GPHI-TTS.exe."
}
if (-not (Test-Path -LiteralPath $BundledManifest -PathType Leaf)) {
    throw "Artifact thiếu model manifest."
}
if (-not (Test-Path -LiteralPath $BundledG2PData -PathType Leaf)) {
    throw "Artifact thiếu từ điển sea_g2p.bin cần cho bước tổng hợp."
}

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
    throw "Smoke test tổng hợp thật bằng GPHI-TTS.exe thất bại."
}
if (-not (Test-Path -LiteralPath $SmokeWav -PathType Leaf) -or (Get-Item -LiteralPath $SmokeWav).Length -le 44) {
    throw "Smoke test không tạo được tệp WAV hợp lệ."
}
if (-not (Test-Path -LiteralPath $SmokeMp3 -PathType Leaf) -or (Get-Item -LiteralPath $SmokeMp3).Length -le 128) {
    throw "Smoke test không tạo được tệp MP3 hợp lệ."
}
Write-Host "Smoke test artifact: WAV + MP3 OK"

# PyInstaller's windowed executable or antivirus scanning can retain a short-lived
# read lock after the smoke process exits. Wait for exclusive access so the
# archive step does not fail intermittently on GPHI-TTS.exe.
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
    throw "GPHI-TTS.exe vẫn bị tiến trình khác khóa sau 120 giây. Hãy đóng ứng dụng và build lại."
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
        if ($Attempt -eq 3) {
            throw
        }
        Write-Warning "Nén artifact thất bại do file đang bận; thử lại lần $($Attempt + 1)/3."
        Start-Sleep -Seconds 5
    }
}
if (-not $ArchiveCreated) {
    throw "Không thể tạo archive production."
}
Get-FileHash -LiteralPath $PortableArchive -Algorithm SHA256 |
    ForEach-Object { "$($_.Hash.ToLower())  $([IO.Path]::GetFileName($PortableArchive))" } |
    Set-Content -LiteralPath "$PortableArchive.sha256" -Encoding ascii

if ($BuildInstaller) {
    $InnoCompiler = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($null -eq $InnoCompiler) {
        throw "Không tìm thấy iscc.exe của Inno Setup."
    }
    & $InnoCompiler.Source (Join-Path $ProjectRoot "packaging\windows\installer.iss")
}

Write-Host "Artifact portable: $PortableArchive"
Write-Host "Smoke test tổng hợp bằng artifact: đã đạt."
Write-Host "Vẫn nên kiểm tra artifact trên Windows sạch và tắt mạng trước khi phát hành."
