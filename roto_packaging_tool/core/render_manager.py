# roto_packaging_tool/core/render_manager.py
import os
import re
import subprocess
import logging
import time


class RenderManager:
    def __init__(self, tools_paths, out_path, tmp_root="/tmp/roto_packager"):
        """
        :param tools_paths: dict { "nuke": "/apps/nuke/Nuke12.2v7/Nuke12.2", ... }
        :param out_path: base output path from YAML
        :param tmp_root: temporary work directory
        """
        self.tools_paths = tools_paths
        self.out_path = out_path
        self.tmp_root = tmp_root
        self.job_id = None

        if not os.path.exists(tmp_root):
            os.makedirs(tmp_root, exist_ok=True)


    def get_work_range(self, placeholders=None, render_ui=None):
        """
        Try Silhouette fx API first, else fallback to placeholders or UI.
        Works in standalone and inside Silhouette.
        """
        try:
            import fx
            project = fx.activeProject()
            for i in project.sources:
                source_file_name = i.properties["path"].getValue()
                frame_range_match = re.search(r"\[(\d+)-(\d+)\]", source_file_name)
                if frame_range_match:
                    start_frame = int(frame_range_match.group(1))
                    end_frame = int(frame_range_match.group(2))
                    return start_frame, end_frame
        except Exception:
            pass  # not running inside Silhouette

        # If not in Silhouette → fallback to UI or placeholders
        if render_ui:
            try:
                start = int(render_ui.startFrameInput.text())
                end = int(render_ui.endFrameInput.text())
                return start, end
            except Exception:
                pass

        frame_range = (placeholders or {}).get("frame_range")
        if frame_range and "-" in frame_range:
            start, end = frame_range.split("-")
            return int(start), int(end)

        return 1001, 1001

    def mb_path_list(self):
        """
        TEMPORARY: Hard-coded matte EXR paths.
        Later this will be dynamic from Silhouette output nodes.
        """
        return [
            "/projects/arc_hs/B001C020/dept/publish/roto/render/B001C020_roto_test_matte01_v001/B001C020_roto_test_matte01_v001.%06d.exr",
            "/projects/arc_hs/B001C020/dept/publish/roto/render/B001C020_roto_test_matte02_v001/B001C020_roto_test_matte02_v001.%06d.exr"
        ]



    def apply_placeholders(self, template: str, placeholders: dict) -> str:
        """
        Replace {tokens} in template string with actual values.
        Example:
            template = "/show/{sg_plate_name}/{out_version}/{shot}.nk"
            placeholders = {"shot": "mech_207_043_0600", "sg_plate_name": "bg01", "out_version": "v001"}
            -> "/show/bg01/v001/mech_207_043_0600.nk"
        """
        try:
            return template.format(**placeholders)
        except KeyError as e:
            print(f"[WARN] Missing placeholder: {e}")
            return template


    # -----------------------------
    # 🔹 Create dynamic Nuke processor file
    # -----------------------------
    def create_roto_nkt_file(self, input_template_path, output_template_path, input_path,
                             write_path, startframe, endframe, mate_list_path, name,
                             layer_dict, additional_value, resolution, layer_path, bake):
        py_template = f"""
import sys
sys.path.append("/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python")
from processors import roto_coloroverlay_processor
input_template_path="{input_template_path}"
output_template_path="{output_template_path}"
startframe={startframe}
endframe={endframe}
mate_list_path="{mate_list_path}"
write_path="{write_path}"
input_path="{input_path}"
layer_path="{layer_path}"
addition_value="{additional_value}"
resolution="{resolution}"
layer_dict="{layer_dict}"
roto_coloroverlay_processor(input_template_path,output_template_path,input_path,
    write_path,startframe,endframe,mate_list_path,layer_dict,addition_value,resolution,layer_path,bake={bake})
"""
        mov_name = name.rsplit(".", 1)[0]
        proxy_template = os.path.join(self.tmp_root, f"{mov_name}.py")

        with open(proxy_template, "w") as cf:
            cf.write(py_template)

        return proxy_template

    # -----------------------------
    # 🔹 Create & Run Nuke Job
    # -----------------------------
    def create_nuke_job(self, name, proxy_template, nuke_template,
                        start_frame, end_frame, job_name="_proxy_action",
                        chunk=10, dependent="", deadline_render=True):

        # Frames per chunk
        chunk = int(end_frame) - int(start_frame) + 1

        # Logging setup
        log_path = os.path.join(self.tmp_root, f"{name}_nuke_job.log")
        logging.basicConfig(filename=log_path, level=logging.DEBUG, format="%(asctime)s %(message)s")

        # Bash runner script
        script = f"""#!/bin/bash
export PYTHONHOME=/apps/nuke/Nuke12.2v7
export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
{self.tools_paths['nuke']} -t "{proxy_template}"
"""
        script_path = os.path.join(self.tmp_root, f"{name}_run_nuke.sh")
        with open(script_path, "w") as file:
            file.write(script)
        subprocess.call(["chmod", "+x", script_path])

        logging.debug(f"Running script: {script}")
        try:
            result = subprocess.Popen([script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = result.communicate()
            logging.info(f"Output: {stdout}")
            logging.error(f"Error: {stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running Nuke script: {e}")
            return None

        # Deadline submission (if enabled)
        if deadline_render:
            try:
                from core.deadline_utils import get_info_txt, submit_to_deadline
                plugin_details, job_details = get_info_txt(
                    f"{name}_{job_name}", name,
                    "2d_pool", "2d_group",
                    start_frame, end_frame,
                    12.2, chunk, dependent,
                    department="Roto"
                )
                job_id = submit_to_deadline(plugin_details, job_details,
                                            os.path.join(self.tmp_root, nuke_template))
                logging.info(f"Template job created with ID: {job_id}")
                return job_id
            except Exception as e:
                logging.error(f"Error submitting to Deadline: {e}")
                return None

        return True


    def get_layer_dict(self):
        """
        Try to collect matte layers from Silhouette project.
        If not running inside Silhouette, return hard-coded mapping.
        """
        try:
            import fx
            mate_layer = {}
            for session in fx.activeProject().sessions:
                for output in session.outputs:
                    roto_node = self.get_connected_roto_node(output)
                    layers = roto_node.children
                    if not layers:
                        continue
                    top_layername = layers[0].label
                    mate_layer[output.properties["path"].value] = top_layername
            return mate_layer
        except Exception as e:
            print(f"[WARN] get_layer_dict fallback: {e}")
            # Hard-coded fallback
            return {
                "/projects/arc_hs/B001C020/dept/publish/roto/render/B001C020_roto_test_matte01_v001/B001C020_roto_test_matte01_v001.%06d.exr": "Matte01",
                "/projects/arc_hs/B001C020/dept/publish/roto/render/B001C020_roto_test_matte02_v001/B001C020_roto_test_matte02_v001.%06d.exr": "Matte02"
            }

    # -----------------------------
    # 🔹 High-level Render Wrapper
    # -----------------------------
    def run_render(self, placeholders, render_ui=None, name="roto_package"):
        self.placeholders = placeholders
        self.placeholders["extension"] = "exr"

        start_frame, end_frame = self.get_work_range(placeholders, render_ui)
        self.placeholders["frame_range"] = f"{start_frame}-{end_frame}"

        # Resolve EXR + NK paths
        exr_path_color_overlay = self.apply_placeholders(self.placeholders["exr_path"], placeholders)
        color_overlay_path = os.path.splitext(os.path.splitext(exr_path_color_overlay)[0])[0]

        write_path = placeholders["write_node_path"]
        write_path = os.path.join(self.out_path, self.apply_placeholders(write_path, placeholders))

        # Ensure full_source_path is set
        if not hasattr(self, "full_source_path"):
            if "source_path" in placeholders:
                self.full_source_path = placeholders["source_path"]
            else:
                self.full_source_path = "/projects/bte_ps/PSG_0020/in/plates/v001/IR_L01/4096x1728/PSG_0020_IR_L01_nk_v001.1001.exr"

        # Input template
        input_template_path = placeholders.get("nuke_coloroverlay_template")
        output_template_path = os.path.join(self.tmp_root, os.path.basename(write_path) + ".nk")

        # Create Nuke python processor
        
        mate_list_path = self.mb_path_list()

        # ✅ always refresh self.layer_dict before use
        self.layer_dict = self.get_layer_dict()
        layer_path = self.layer_dict  # keep same naming as old code
        print("resolution__________",self.full_source_path)

        resolution = os.path.basename(os.path.dirname(self.full_source_path))

        py_template = self.create_roto_nkt_file(
            input_template_path, output_template_path, self.full_source_path,
            write_path, start_frame, end_frame, mate_list_path, name,
            self.layer_dict, placeholders.get("mate_snippet", {}),
            resolution, layer_path, bake=True
        )


        return self.create_nuke_job(
            name, py_template,
            os.path.basename(write_path) + ".nk",
            start_frame, end_frame
        )
