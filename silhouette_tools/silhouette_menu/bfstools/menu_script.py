import sys
from pathlib import Path

print("[BFSTools] menu_script.py started")

src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)
print(f"[BFSTools] src path added: {src_path}")

try:
    import bfstools  # noqa

    print("[BFSTools] bfstools imported ok")
except Exception as e:
    print(f"[BFSTools] bfstools import failed: {e}")

try:
    from bfstools.actions import bfs_menu_review  # noqa

    print("[BFSTools] bfs_menu_review loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_review failed: {e}")

try:
    from bfstools.actions import bfs_menu_publish  # noqa

    print("[BFSTools] bfs_menu_publish loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_publish failed: {e}")

try:
    from bfstools.actions import bfs_menu_save  # noqa

    print("[BFSTools] bfs_menu_save loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_save failed: {e}")

try:
    from bfstools.actions import bfs_menu_my_task  # noqa

    print("[BFSTools] bfs_menu_my_task loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_my_task failed: {e}")

try:
    from bfstools.actions import bfs_menu_bpackage  # noqa

    print("[BFSTools] bfs_menu_bpackage loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_bpackage failed: {e}")

try:
    from bfstools.actions import bfs_menu_sync_frame  # noqa

    print("[BFSTools] bfs_menu_sync_frame loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_sync_frame failed: {e}")

try:
    from bfstools.actions import bfs_menu_renamer  # noqa

    print("[BFSTools] bfs_menu_renamer loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_renamer failed: {e}")

try:
    from bfstools.actions import bfs_menu_debugger  # noqa

    print("[BFSTools] bfs_menu_debugger loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_debugger failed: {e}")

try:
    from bfstools.actions import bfs_menu_staging  # noqa

    print("[BFSTools] bfs_menu_staging loaded")
except Exception as e:
    print(f"[BFSTools] bfs_menu_staging failed: {e}")

print("[BFSTools] menu_script.py done")
