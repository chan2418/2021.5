import sys

b_show_name = "ie_flx"
sys.path.insert(0, "/tools/projects/{}/install/core/python".format(b_show_name))
sys.path.append(
    "/tools/packages/python/3.9.6/platform-linux/arch-x86_64/os-rocky-9.2/python/site-packages/"
)
import re
import sys

import sgtk


def auto_unregister_and_recreate(tk, project_name, shot_name):
    """
    Automatically unregisters conflicting folder paths and recreates
    the filesystem structure for a given shot.

    Args:
        tk           : Already initialized sgtk instance
        project_name : The project name (e.g., 'ie_flx')
        shot_name    : The shot code  (e.g., 'FLX-3009-0220')
    """
    print("=" * 60)
    print("ShotGrid Path Conflict Auto-Fix")
    print("=" * 60)
    print(f"Project  : {project_name}")
    print(f"Shot     : {shot_name}")
    print("=" * 60)

    try:
        # ── Step 1: Find the Shot entity in ShotGrid ─────────────────────────
        print(f"\n[STEP 1] Looking up Shot '{shot_name}' in ShotGrid...")
        sg = tk.shotgun
        shot = sg.find_one(
            "Shot", [["code", "is", shot_name]], ["id", "code", "project"]
        )

        if not shot:
            print(f"[ERROR] Shot '{shot_name}' not found in ShotGrid.")
            sys.exit(1)

        shot_id = shot["id"]
        shot_code = shot["code"]
        print(f"         Found Shot: {shot_code} (ID: {shot_id})")

        # ── Step 2: Unregister the conflicting old path ───────────────────────
        print(f"\n[STEP 2] Unregistering conflicting path for Shot '{shot_code}'...")
        conflict_path = "/projects/{}/{}".format(project_name, shot_name)
        print(f"         Unregistering path: {conflict_path}")

        unreg_cmd = sgtk.get_command("unregister_folders", tk)
        unreg_cmd.execute({"path": conflict_path})
        print("         Unregister successful.")

        # ── Step 3: Recreate the filesystem structure ─────────────────────────
        print(f"\n[STEP 3] Recreating filesystem structure for Shot '{shot_code}'...")
        tk.create_filesystem_structure("Shot", shot_id)
        print("         Filesystem structure created successfully.")

        # ── Step 4: Verify ────────────────────────────────────────────────────
        print(f"\n[STEP 4] Verifying context from Shot '{shot_code}'...")
        context = tk.context_from_entity("Shot", shot_id)
        print(f"         Context: {context}")

        print("\n" + "=" * 60)
        print("Fix applied successfully!")
        print("=" * 60)

    except sgtk.TankError as e:
        print(f"\n[TANK ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")
        sys.exit(1)


def set_sgtk_auth():
    """
    Authenticates the user with Shotgun and sets the authenticated user in Shotgun Toolkit (sgtk).
    This method uses the ShotgunAuthenticator to prompt the user for authentication credentials,
    retrieves the authenticated user, and then sets this user in the Shotgun Toolkit (sgtk) context.

    Returns:
        ShotgunUser: The authenticated Shotgun user.

    Raises:
        ShotgunAuthenticationError: If the authentication fails for any reason.
    """

    proxy_ip = "10.10.4.121:3128"
    sa = sgtk.authentication.ShotgunAuthenticator()
    user = sa.create_script_user(
        api_script="silhouette_my_task",
        api_key="cllnjxceqgaa7~pafXthdlaxm",
        host="https://basilic.shotgrid.autodesk.com",
        http_proxy=proxy_ip,
    )
    sgtk.set_authenticated_user(user)

    return user


def fix_from_error_message(error_message):
    """
    Parses the TankError message and auto-extracts
    project name and shot name to fix the conflict.

    Args:
        error_message (str): The full TankError message string.
    """
    print("\n[PARSER] Extracting info from error message...")
    user = set_sgtk_auth()
    print("USER:", user)
    print("AUTH USER:", sgtk.get_authenticated_user())

    # Extract new path  -> /projects/ie_flx/FLX-3009-0220
    new_path_match = re.search(r"path '(/projects/([^/]+)/([^']+))'", error_message)
    # Extract old path  -> /projects/ie_flx/FLX_3009_0220
    old_path_match = re.search(
        r"another path '(/projects/([^/]+)/([^']+))'", error_message
    )
    # Extract shot name from tank command hint
    shot_name_match = re.search(
        r"tank Shot ([\w\-]+) unregister_folders", error_message
    )

    if not new_path_match or not shot_name_match:
        print("[ERROR] Could not parse error message.")
        sys.exit(1)

    project_name = new_path_match.group(2)
    shot_name = shot_name_match.group(1)
    old_path = old_path_match.group(1) if old_path_match else "Unknown"

    print(f"         Project      : {project_name}")
    print(f"         Shot         : {shot_name}")
    print(f"         Old Path     : {old_path}")
    print(f"         New Path     : {new_path_match.group(1)}")

    # ── Bootstrap toolkit using the project tank path ─────────────────────────
    project_tank_path = "/tools/projects/{}".format(project_name)
    print(f"\n[BOOTSTRAP] Initializing toolkit from: {project_tank_path}")

    try:
        # This uses the existing pipeline config — no script credentials needed
        tk = sgtk.sgtk_from_path(project_tank_path)

        print(f"[BOOTSTRAP] Toolkit initialized successfully: {tk}")
    except sgtk.TankError as e:
        print(f"[BOOTSTRAP ERROR] {e}")
        sys.exit(1)

    auto_unregister_and_recreate(tk, project_name, shot_name)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    error_msg = """
    tank.errors.TankError: Folder creation aborted: The path '/projects/ie_flx/FLX-3009-0220'
    cannot be created because another path '/projects/ie_flx/FLX_3009_0220' is already
    associated with Shot FLX-3009-0220. This typically happens if an item in PTR is renamed
    or if the path naming in the folder creation configuration is changed. In order to continue
    you can either change the Shot back to its previous name or you can unregister the currently
    associated folders by running the following command: 'tank Shot FLX-3009-0220 unregister_folders'
    and then try again.
    """

    fix_from_error_message(error_msg)
