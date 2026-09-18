# mb_nmb_handler.py
# ─────────────────────────────────────────────────────────────────────────────
# Standalone MB / NMB handler.
# All path config comes from YAML tokens — nothing hardcoded here.
#
# YAML keys needed:
# mb_src_path : source path template (supports {description} and all placeholders)
# mb_dst_path : destination path template
# nmb_dst_path : nmb render destination path template
# ─────────────────────────────────────────────────────────────────────────────
import sys
deadline_utils = "/tools/packages/deadline_utils/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python/deadline_utils"
sys.path.append(deadline_utils)
import os
import json
import shutil
import subprocess
import fx
import re
from silhouette.deadline_actions import *

class MbNmbHandler:
    def __init__(self, packager):
        self.p = packager

    # ── internal helpers ──────────────────────────────────────────────────────
    def _get_descriptions(self, matte_key):
        paths = list(self.p.template_input_data.get(matte_key, {}).values())
        if not paths:
            print(f"[MbNmbHandler] no paths found under '{matte_key}'")
            return []
        project_path = fx.activeProject().path
        try:
            project_name_fields = self.p.get_fields_from_path(
                os.path.dirname(project_path), "silhouette_shot_work"
            )
            project_field_name = project_name_fields["name"]
        except Exception:
            project_field_name = ""
        result = []
        for src_path in paths:
            try:
                if "alpha" in os.path.basename(src_path):
                    fields = self.p.get_fields_from_path(
                        src_path, "silhouette_shot_render_pub_stereo_alpha"
                    )
                else:
                    seq = src_path.split(".")[-2]
                    fields = self.p.get_fields_from_path(
                        src_path, "silhouette_shot_render_pub_stereo", seq
                    )
                description = fields["name"].replace(project_field_name + "_", "")
            except Exception as e:
                print(f"[_get_descriptions] template resolution failed for {src_path}: {e}")
                description = os.path.basename(os.path.dirname(src_path))
            print(f"[_get_descriptions] src : {src_path}")
            print(f"[_get_descriptions] desc : {description}")
            result.append((description, src_path))
        return result

    def _resolve(self, template, description):
        """Inject description into placeholders and resolve template string."""
        local_ph = dict(self.p.placeholders)
        local_ph["description"] = description
        return self.p.apply_placeholders(template, local_ph)

    # ── NMB helpers: motion blur + recursive per-object blur disable/restore ─
    def _collect_and_disable_blur_recursive(self, item, originals):
        """
        Recursively traverse RotoNode children (layers, shapes, etc.).
        Collect (blur_property, original_value) pairs and set blur to 0.
        This follows the exact logic from the standalone disable_blur_recursive script.
        """
        try:
            blur_prop = item.property("blur")
            if blur_prop is not None:
                originals.append((blur_prop, blur_prop.value))
                blur_prop.setValue(0)
        except Exception:
            pass  # item has no 'blur' property — ignore
        # Recurse into children
        try:
            for child in item.children:
                self._collect_and_disable_blur_recursive(child, originals)
        except Exception:
            pass

    def _restore_blur(self, originals):
        """Restore previously saved blur values after NMB render submission."""
        for blur_prop, original_value in originals:
            try:
                blur_prop.setValue(original_value)
            except Exception:
                pass

    # ── public functions ──────────────────────────────────────────────────────
    def run_mb_copy(self, **args):
        """
        Copy MB frames from artist selected src paths to mb_dst_path.
        src comes from template_input_data["MB_matte_path"] (UI selection).
        """
        mb_dst_tpl = self.p.placeholders.get("mb_dst_path")
        if not mb_dst_tpl:
            print("[run_mb_copy] 'mb_dst_path' not set in YAML tokens — skipping")
            return
        pairs = self._get_descriptions("MB_matte_path")
        if not pairs:
            return
        submitted = []
        for description, src_path in pairs:
            resolved_src = src_path  # already real path from artist selection
            resolved_dst = self.p.out_path + self._resolve(mb_dst_tpl, description)
            os.makedirs(os.path.dirname(resolved_dst), exist_ok=True)
            print(f"[run_mb_copy] description : {description}")
            print(f"[run_mb_copy] src : {resolved_src}")
            print(f"[run_mb_copy] dst : {resolved_dst}")
            job_id = self.p.copying_render_files(resolved_src, resolved_dst)
            if job_id:
                submitted.append(job_id)
                print(f"[run_mb_copy] job_id : {job_id}")
        if submitted:
            self.p.job_id = submitted[-1]
            print(f"[run_mb_copy] all job ids : {submitted}")
        else:
            print("[run_mb_copy] no jobs submitted")

    def _strip_frame_ext_suffix(self, path):
        """
        sfxcmd's fx_command.py appends its own '.{frame}.{ext}' when writing
        per-frame output for -args publish paths — it does not substitute
        '%0Nd' tokens. If we hand it a path that already ends in a literal
        '.%0Nd.ext' (needed elsewhere, e.g. copying_render_files' regex
        parser), we get a doubled suffix:
            ..._nmb_v001.%04d.exr.0986.exr
        Strip that trailing pattern so sfxcmd receives a bare path and adds
        the frame number itself, producing the correct:
            ..._nmb_v001.0986.exr
        """
        return re.sub(r'\.%0\d+d\.\w+$', '', path)

    def run_nmb_render(self, **args):
        """
        Render NMB (No Motion Blur) version using CommandLine submission on a
        temporary project copy. Follows the full disable sequence from the
        standalone NMB script:
          - disable motionBlur.enable on all RotoNodes
          - recursively disable 'blur' property on every child item (layers/shapes)
          - set NMB output paths
          - save
          - create temp project copy + feather removal
          - submit CommandLine jobs
          - restore original motion blur + blur values on live session
        """
        nmb_dst_tpl = self.p.placeholders.get("nmb_dst_path")
        if not nmb_dst_tpl:
            print("[run_nmb_render] 'nmb_dst_path' not set in YAML tokens — skipping")
            return
        pairs = self._get_descriptions("MB_matte_path")
        if not pairs:
            print("[run_nmb_render] No MB_matte_path found — skipping NMB render")
            return

        print("[run_nmb_render] Starting NMB render process (CommandLine)...")
        session_live = fx.activeSession()
        roto_nodes = session_live.getNodes("RotoNode")
        output_nodes = session_live.getNodes("OutputNode")

        # resolve description → bare NMB dest path (no frame/ext — matches OutputNode.path convention)
        desc_to_dst = {}
        for description, _ in pairs:
            resolved_dst = self.p.out_path + self._resolve(nmb_dst_tpl, description)
            os.makedirs(os.path.dirname(resolved_dst), exist_ok=True)
            bare_dst = self._strip_frame_ext_suffix(resolved_dst)
            desc_to_dst[description] = bare_dst
            print(f"[run_nmb_render] {description} → {bare_dst}")

        try:
            project_field_name = self.p.get_fields_from_path(
                os.path.dirname(fx.activeProject().path), "silhouette_shot_work"
            )["name"]
        except Exception:
            project_field_name = ""

        # map each OutputNode → its NMB destination, remember original path for restore
        node_to_new_path = {}
        node_original_paths = {}
        for output_node in output_nodes:
            try:
                node_path = output_node.properties["path"].value + ".%04d.exr"
                node_fields = self.p.get_fields_from_path(
                    node_path, "silhouette_shot_render_pub_stereo"
                )
                node_desc = node_fields["name"].replace(project_field_name + "_", "")
            except Exception as e:
                print(f"[run_nmb_render] Could not resolve description for '{output_node.label}': {e}")
                continue
            if node_desc in desc_to_dst:
                node_original_paths[output_node] = output_node.properties["path"].value
                node_to_new_path[output_node] = desc_to_dst[node_desc]

        if not node_to_new_path:
            print("[run_nmb_render] No output nodes mapped to NMB destinations. Aborting.")
            return

        # ─────────────────────────────────────────────────────────────────────
        # FULL DISABLE SEQUENCE (matches standalone NMB script)
        # 1. Disable motion blur on all RotoNodes
        # 2. Recursively disable 'blur' on every child item that has the property
        # ─────────────────────────────────────────────────────────────────────
        for roto_node in roto_nodes:
            try:
                roto_node.property("motionBlur.enable").setValue(False)
            except Exception as e:
                print(f"[run_nmb_render] Could not disable motion blur on {roto_node}: {e}")

        blur_originals = []
        for roto_node in roto_nodes:
            self._collect_and_disable_blur_recursive(roto_node, blur_originals)

        if blur_originals:
            print(f"[run_nmb_render] Disabled 'blur' on {len(blur_originals)} roto items for NMB render")
        else:
            print("[run_nmb_render] No 'blur' properties found to disable")

        # Apply NMB destination paths to the mapped OutputNodes (live session)
        for output_node, new_path in node_to_new_path.items():
            output_node.properties["path"].value = new_path

        try:
            fx.activeProject().save()
            print("[run_nmb_render] Saved live project with NMB paths + motion blur + blur disabled")
        except Exception as e:
            print(f"[run_nmb_render] ⚠️ Could not save project before copy: {e}")

        # ── Create temp project copy for isolated NMB render ─────────────────
        try:
            project_path = fx.activeProject().path
            base_dir = os.path.join(project_path.split("/scripts/")[0], "scripts")
            end_dir = project_path.split("/scripts/")[1]
            hidden_folder_path = os.path.join(base_dir, ".tmp_nmb")
            os.makedirs(hidden_folder_path, exist_ok=True)

            try:
                fields = self.p.get_fields_from_path(
                    os.path.dirname(project_path), "silhouette_shot_work"
                )
                field_name = fields.get("name", "unknown")
            except Exception:
                field_name = "unknown"

            nmb_project_name = end_dir.replace(f"_{field_name}_", f"_{field_name}_nmb_")
            nmb_script_path = os.path.join(hidden_folder_path, nmb_project_name)
            nmb_script_path = os.path.dirname(nmb_script_path)

            if os.path.exists(nmb_script_path):
                try:
                    shutil.rmtree(nmb_script_path)
                    print(f"[run_nmb_render] Removed old temp project: {nmb_script_path}")
                except Exception as e:
                    print(f"[run_nmb_render] Failed to remove old temp project: {e}")

            try:
                shutil.copytree(os.path.dirname(project_path), nmb_script_path)
                print(f"[run_nmb_render] Created temp NMB project: {nmb_script_path}")
                for root, dirs, files in os.walk(nmb_script_path):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), 0o777)
                    for f in files:
                        os.chmod(os.path.join(root, f), 0o777)
            except Exception as e:
                print(f"[run_nmb_render] Failed to create temp project copy: {e}")
                return

            # Remove feathers from the temp project (clean NMB)
            try:
                from silhouette_package import feather_removal
                feather_removal.remove_all_feathers_from_path(nmb_script_path)
                print("[run_nmb_render] Feather removal complete")
            except Exception as e:
                print(f"[run_nmb_render] ❌ Feather removal failed: {e}")

            start_frame = self.p.render_ui.startFrameInput.text()
            end_frame = self.p.render_ui.endFrameInput.text()
            frame_range = f"{start_frame}-{end_frame}"
            batch_name = os.path.basename(project_path).split(".")[0]

            # file path, not folder — required by submit_render_commandline
            nmb_scene_file = os.path.join(nmb_script_path, "project.sfx")

            submitted_job_ids = []
            for output_node in node_to_new_path:
                job_name = f"{batch_name}_{output_node.label}_nmb_render"
                try:
                    job_id = submit_render_commandline(
                        session=session_live,
                        batch_name=batch_name,
                        job_name=job_name,
                        frames=frame_range,
                        output=output_node.label,
                        department="Roto",
                        scene_file=nmb_scene_file,
                    )
                    if job_id:
                        submitted_job_ids.append(job_id)
                        print(f"[run_nmb_render] ✅ submitted '{output_node.label}' → JobID={job_id}")
                    else:
                        print(f"[run_nmb_render] ⚠️ no job_id for '{output_node.label}'")
                except Exception as e:
                    print(f"[run_nmb_render] Failed to submit CommandLine job for '{output_node.label}': {e}")

            if submitted_job_ids:
                self.p.job_id = submitted_job_ids[-1]
                print(f"[run_nmb_render] All NMB job IDs: {submitted_job_ids}")
            else:
                print("[run_nmb_render] ⚠️ No NMB jobs submitted")

        finally:
            # ── RESTORE live session exactly as it was before NMB processing ──
            for roto_node in roto_nodes:
                try:
                    roto_node.property("motionBlur.enable").setValue(True)
                except Exception:
                    pass

            self._restore_blur(blur_originals)

            for output_node, original_path in node_original_paths.items():
                try:
                    output_node.properties["path"].value = original_path
                except Exception:
                    pass

            try:
                fx.activeProject().save()
                print("[run_nmb_render] Restored live project (motion blur + blur + original paths)")
            except Exception:
                pass
