#!/usr/bin/env python3
"""Configure generated Flutter Android Gradle project for owner-held release signing."""
from __future__ import annotations

import os
import re
from pathlib import Path


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"Required signing environment variable is missing: {name}")
    return value


def main() -> None:
    keystore = Path(required("ANDROID_KEYSTORE_PATH")).resolve()
    alias = required("ANDROID_KEY_ALIAS")
    required("ANDROID_KEYSTORE_PASSWORD")
    required("ANDROID_KEY_PASSWORD")
    if not keystore.is_file():
        raise SystemExit("Configured Android keystore file does not exist.")
    repo_root = Path(__file__).resolve().parents[2]
    if keystore.is_relative_to(repo_root):
        raise SystemExit("Keystore must remain outside the checked-out repository.")

    gradle = Path(__file__).resolve().parents[1] / "android" / "app" / "build.gradle.kts"
    source = gradle.read_text(encoding="utf-8")
    if 'create("release")' in source or 'create("upload")' in source:
        raise SystemExit("Release signing configuration already exists; refusing to overwrite it.")

    signing_config = """
    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("ANDROID_KEYSTORE_PATH"))
            storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
            keyAlias = System.getenv("ANDROID_KEY_ALIAS")
            keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
        }
    }
"""
    android_end = re.search(r"\n}\s*\nflutter\s*\{", source)
    if not android_end:
        raise SystemExit("Could not safely locate the generated android { } block.")
    source = source[:android_end.start()] + "\n" + signing_config + source[android_end.start():]

    debug_signing = 'signingConfig = signingConfigs.getByName("debug")'
    if debug_signing in source:
        source = source.replace(debug_signing, 'signingConfig = signingConfigs.getByName("release")')
    else:
        release_block = re.search(
            r'buildTypes\s*\{\s*(?:getByName\("release"\)|release)\s*\{', source
        )
        if release_block:
            source = (
                source[:release_block.end()]
                + '\n            signingConfig = signingConfigs.getByName("release")'
                + source[release_block.end():]
            )
        else:
            android_end = re.search(r"\n}\s*\nflutter\s*\{", source)
            if not android_end:
                raise SystemExit("Could not safely locate the generated android { } block.")
            build_types = """
    buildTypes {
        getByName("release") {
            signingConfig = signingConfigs.getByName("release")
        }
    }
"""
            source = source[:android_end.start()] + "\n" + build_types + source[android_end.start():]

    gradle.write_text(source, encoding="utf-8")
    print("Owner-controlled Android release signing configured; private key remains outside the repository.")


if __name__ == "__main__":
    main()
