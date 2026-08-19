from __future__ import annotations

import csv
import importlib.metadata as md
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "packaging" / "licenses" / "components"
MANIFEST = PROJECT_ROOT / "packaging" / "licenses" / "PYTHON_PACKAGES.csv"

# Direct production packages plus critical transitive/runtime packages that are
# known to be used by VieNeu/PySide6 in this project. Running this in a clean
# production environment intentionally over-includes license files rather than
# risking omission from a binary distribution.
PACKAGES = [
    "PyInstaller",
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "shiboken6",
    "vieneu",
    "torch",
    "torchaudio",
    "transformers",
    "numpy",
    "scipy",
    "psutil",
    "py-cpuinfo",
    "loguru",
    "PyYAML",
    "python-docx",
    "pypdf",
    "lameenc",
    "onnxruntime",
    "sea-g2p",
    "soundfile",
    "soxr",
    "tokenizers",
    "huggingface-hub",
]

LICENSE_WORDS = (
    "license",
    "licence",
    "copying",
    "copyright",
    "notice",
    "thirdpartynotice",
    "third_party_notice",
    "third-party-notice",
)


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._+-]+", "_", value)


def metadata_value(meta, key: str) -> str:
    value = meta.get(key) or ""
    return " ".join(str(value).split())


def project_urls(meta) -> str:
    values = meta.get_all("Project-URL") or []
    return " | ".join(" ".join(v.split()) for v in values)


def is_license_path(rel: Path) -> bool:
    lowered_parts = [p.lower() for p in rel.parts]
    name = rel.name.lower()
    if any(part in {"license", "licenses", "licence", "licences"} for part in lowered_parts):
        return True
    return any(word in name for word in LICENSE_WORDS)


def copy_license_files(dist: md.Distribution, target: Path) -> list[str]:
    copied: list[str] = []
    for rel in dist.files or []:
        rel_path = Path(str(rel))
        if not is_license_path(rel_path):
            continue
        src = Path(dist.locate_file(rel))
        if not src.is_file():
            continue
        # Skip unexpectedly huge non-text blobs. Real license bundles are small.
        try:
            if src.stat().st_size > 20 * 1024 * 1024:
                continue
        except OSError:
            continue
        dest = target / safe_name(str(rel_path).replace("/", "__").replace("\\", "__"))
        try:
            shutil.copy2(src, dest)
            copied.append(dest.name)
        except OSError as exc:
            print(f"WARN: could not copy {src}: {exc}")
    return sorted(set(copied))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # Remove only generated component folders; preserve standard license texts.
    for child in OUT.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        elif child.is_file():
            child.unlink()

    rows = []
    missing = []
    no_license_files = []

    for requested in PACKAGES:
        try:
            dist = md.distribution(requested)
        except md.PackageNotFoundError:
            missing.append(requested)
            print(f"MISSING: {requested}")
            continue

        name = dist.metadata.get("Name") or requested
        version = dist.version
        target = OUT / f"{safe_name(name)}-{safe_name(version)}"
        target.mkdir(parents=True, exist_ok=True)
        copied = copy_license_files(dist, target)

        license_expr = metadata_value(dist.metadata, "License-Expression")
        license_field = metadata_value(dist.metadata, "License")
        home = metadata_value(dist.metadata, "Home-page")
        urls = project_urls(dist.metadata)

        meta_text = (
            f"Name: {name}\n"
            f"Version: {version}\n"
            f"License-Expression: {license_expr}\n"
            f"License metadata: {license_field}\n"
            f"Home-page: {home}\n"
            f"Project-URL: {urls}\n"
            f"License files copied: {', '.join(copied) if copied else 'NONE'}\n"
        )
        (target / "PACKAGE_METADATA.txt").write_text(meta_text, encoding="utf-8")

        if not copied:
            no_license_files.append(f"{name}=={version}")
            print(f"WARN: no license/copyright file found in wheel metadata for {name}=={version}")
        else:
            print(f"OK: {name}=={version}: {len(copied)} license/notice file(s)")

        rows.append(
            {
                "package": name,
                "version": version,
                "license_expression": license_expr,
                "license_metadata": license_field,
                "home_page": home,
                "project_urls": urls,
                "copied_files": " | ".join(copied),
            }
        )

    with MANIFEST.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["package"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nManifest: {MANIFEST}")
    print(f"Licenses: {OUT}")

    if missing:
        print("\nERROR: critical packages missing from this environment:")
        for item in missing:
            print(f"  - {item}")
        print("Run this script only after installing the exact production lock.")
        return 2

    if no_license_files:
        print("\nREVIEW REQUIRED: these wheels did not expose a recognizable license file:")
        for item in no_license_files:
            print(f"  - {item}")
        print("Check the exact wheel/upstream project and add its license manually before release.")
        return 3

    print("\nPASS: principal production package license files were exported.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
