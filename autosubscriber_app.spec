# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    copy_metadata,
)


sentencepiece_datas, sentencepiece_binaries, sentencepiece_hiddenimports = (
    collect_all("sentencepiece")
)

protobuf_datas, protobuf_binaries, protobuf_hiddenimports = (
    collect_all("google.protobuf")
)


datas = [
    ("config.default.ini", "."),
    (
        "app/assets/branding",
        "app/assets/branding",
    ),
    (
        "app/assets/sites",
        "app/assets/sites",
    ),
    (
        "extensions/AutoTubeYouTube-nonstop.crx",
        "extensions",
    ),
    (
        "ytmonsterru_assets/canvas1.png",
        "ytmonsterru_assets",
    ),
    (
        "ytmonsterru_assets/canvas2.png",
        "ytmonsterru_assets",
    ),
]

build_metadata_path = os.environ.get("AUTOSUBSCRIBER_BUILD_METADATA_PATH")
if build_metadata_path:
    datas.append((build_metadata_path, "app"))

datas += sentencepiece_datas
datas += protobuf_datas

# Transformers checks protobuf through package metadata.
# Bundling only google.protobuf modules is not sufficient.
datas += copy_metadata("protobuf")


binaries = []

binaries += sentencepiece_binaries
binaries += protobuf_binaries


hiddenimports = []

hiddenimports += collect_submodules("app")
hiddenimports += collect_submodules("selenium_codes")
hiddenimports += collect_submodules("selenium")
hiddenimports += collect_submodules("undetected_chromedriver")

hiddenimports += collect_submodules(
    "transformers.models.xlm_roberta"
)

hiddenimports += collect_submodules(
    "transformers.models.trocr"
)

hiddenimports += collect_submodules("google.protobuf")

hiddenimports += sentencepiece_hiddenimports
hiddenimports += protobuf_hiddenimports

hiddenimports += [
    "sentencepiece",
    "sentencepiece._sentencepiece",
    "sentencepiece.sentencepiece_model_pb2",
    "sentencepiece.sentencepiece_pb2",

    "google.protobuf",
    "google.protobuf.descriptor",
    "google.protobuf.descriptor_database",
    "google.protobuf.descriptor_pb2",
    "google.protobuf.descriptor_pool",
    "google.protobuf.internal",
    "google.protobuf.internal.api_implementation",
    "google.protobuf.internal.builder",
    "google.protobuf.internal.containers",
    "google.protobuf.internal.decoder",
    "google.protobuf.internal.encoder",
    "google.protobuf.internal.enum_type_wrapper",
    "google.protobuf.internal.extension_dict",
    "google.protobuf.internal.message_listener",
    "google.protobuf.internal.python_message",
    "google.protobuf.internal.type_checkers",
    "google.protobuf.json_format",
    "google.protobuf.message",
    "google.protobuf.message_factory",
    "google.protobuf.reflection",
    "google.protobuf.symbol_database",
    "google.protobuf.text_encoding",
    "google.protobuf.text_format",

    # Recent protobuf releases use the UPB native backend.
    "google._upb",
    "google._upb._message",

    "transformers.models.xlm_roberta",
    "transformers.models.xlm_roberta.configuration_xlm_roberta",
    "transformers.models.xlm_roberta.tokenization_xlm_roberta",

    "transformers.models.trocr",
    "transformers.models.trocr.configuration_trocr",
    "transformers.models.trocr.processing_trocr",
]

hiddenimports = list(dict.fromkeys(hiddenimports))


a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        "scripts/pyinstaller_transformers_runtime.py",
    ],
    excludes=[
        "screenshots",
        ".venv",
        ".cache",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name="AutosubscriberApp",
    icon="app/assets/branding/autosubscriber-logo.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    upx_exclude=[],
    runtime_tmpdir=None,
)
