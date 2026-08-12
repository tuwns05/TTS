# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)


project_root = Path(SPECPATH).resolve().parent
source_root = project_root / "src"
model_root = project_root / "resources" / "models" / "vieneu-v3"
licenses_root = project_root / "packaging" / "licenses"

if not (model_root / "manifest.json").is_file():
    raise SystemExit("Thiếu bundle model. Chạy scripts/prepare_vieneu_v3.py trước.")

datas = [
    (str(source_root / "vntts" / "config" / "default.yaml"), "vntts/config"),
    (str(source_root / "vntts" / "ui" / "resources" / "styles.qss"), "vntts/ui/resources"),
    (str(model_root), "resources/models/vieneu-v3"),
    (str(licenses_root), "licenses"),
]
datas += collect_data_files("vieneu")
datas += collect_data_files("vieneu_utils")
datas += collect_data_files("sea_g2p")
datas += copy_metadata("vieneu")

hiddenimports = [
    "lameenc",
    "vieneu.v3turbo",
    "vieneu._v3_turbo_engine.onnx_runtime_lite",
    "vieneu._v3_turbo_engine.onnx_denoiser",
    "vieneu._v3_turbo_engine.speaker",
    "vieneu._v3_turbo_engine.speaker.onnx_extractor",
]
hiddenimports += collect_submodules("vieneu_utils")
hiddenimports += collect_submodules("sea_g2p")

binaries = collect_dynamic_libs("onnxruntime")

a = Analysis(
    [str(source_root / "vntts" / "__main__.py")],
    pathex=[str(source_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "gradio",
        "fastapi",
        "uvicorn",
        "vieneu.fast",
        "vieneu.remote",
        "vieneu.standard",
        "vieneu.turbo",
        "vieneu.core_xpu",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GPHI-TTS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GPHI-TTS",
)
