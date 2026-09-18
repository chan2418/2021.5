import os
import re
import shutil
import zlib
from datetime import datetime

import fx


def remove_all_feathers():
    """Called from Silhouette script editor - uses active project path"""
    project_path = fx.activeProject().path
    sfx_folder = os.path.dirname(project_path)
    _patch_folder(sfx_folder)


def remove_all_feathers_from_path(sfx_folder):
    """Called externally with explicit folder - no fx dependency needed"""
    _patch_folder(sfx_folder)


def _patch_folder(sfx_folder):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def patch_xml(xml_str):
        xml_str = re.sub(r"\s*<Feather>[^<]*</Feather>", "", xml_str)
        xml_str = re.sub(
            r'(<Property id="feather">)\s*<Key[^>]*>.*?</Key>\s*(</Property>)',
            r"\1<Value></Value>\2",
            xml_str,
            flags=re.DOTALL,
        )
        return xml_str

    # ── project.sfx (zlib compressed XML) ────────────────────
    project_path = os.path.join(sfx_folder, "project.sfx")
    try:
        if os.path.exists(project_path):
            shutil.copy2(project_path, project_path + f".bak_{timestamp}")
            with open(project_path, "rb") as f:
                raw = f.read()
            xml_str = zlib.decompress(raw[4:]).decode("utf-8", errors="replace")
            xml_patched = patch_xml(xml_str)
            if xml_patched != xml_str:
                new_bytes = xml_patched.encode("utf-8")
                new_compressed = zlib.compress(new_bytes, level=6)
                new_header = len(new_bytes).to_bytes(4, "big")
                with open(project_path, "wb") as f:
                    f.write(new_header + new_compressed)
                print("✅ project.sfx feathers removed")
    except Exception as e:
        print(f"❌ project.sfx patch error: {e}")

    # ── *.fsx (plain text XML) ────────────────────────────────
    try:
        for fname in os.listdir(sfx_folder):
            if fname.endswith(".fsx"):
                fsx_path = os.path.join(sfx_folder, fname)
                shutil.copy2(fsx_path, fsx_path + f".bak_{timestamp}")
                with open(fsx_path, "r", encoding="latin-1") as f:
                    xml_str = f.read()
                xml_patched = patch_xml(xml_str)
                if xml_patched != xml_str:
                    with open(fsx_path, "w", encoding="latin-1") as f:
                        f.write(xml_patched)
                    print(f"✅ {fname} feathers removed")
    except Exception as e:
        print(f"❌ .fsx patch error: {e}")
