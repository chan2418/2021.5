# roto_packaging_tool/core/package_manager.py
import os
from core.structure_builder import StructureBuilder
from core.render_manager import RenderManager


class PackageManager:
    def __init__(self, config_dir, tools_paths, out_path):
        self.config_dir = config_dir
        self.tools_paths = tools_paths
        self.out_path = out_path

    def run_packaging(self, show, subgroup, tokens):
        """
        Run Nuke packaging workflow using YAML + StructureBuilder.
        """
        config_file = os.path.join(self.config_dir, f"{show}.yaml")
        builder = StructureBuilder(config_file, tokens)

        # 🔹 Collect resolved file paths from folder structure
        files = builder.collect_files(subgroup)

        placeholders = {
            **tokens,
            "exr_path": files.get("exr"),
            "write_node_path": files.get("exr"),   # write path = EXR path
            "nuke_coloroverlay_template": builder.cfg["cases"][subgroup]["roto"].get(
                "nuke_coloroverlay_template"
            ),
            "mate_snippet": builder.cfg["cases"][subgroup]["roto"].get("mate_snippet", {}),
        }

        rm = RenderManager(self.tools_paths, self.out_path)

        # 🔹 Run Nuke render
        job_id = rm.run_render(placeholders, name=f"{tokens['shot']}_roto")

        return {"nuke_job": job_id}
