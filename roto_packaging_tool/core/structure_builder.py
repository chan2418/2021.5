# roto_packaging_tool/core/structure_builder.py
import os
import yaml


class StructureBuilder:
    def __init__(self, config_file, tokens):
        """
        Load a config YAML and prepare tokens for replacement.
        :param config_file: path to mxp.yaml / bfu.yaml
        :param tokens: dict like {"shot": "B001C020", "out_version": "v003", ...}
        """
        with open(config_file, "r") as f:
            self.cfg = yaml.safe_load(f)
        self.tokens = tokens

    def resolve(self, template: str) -> str:
        """Replace placeholders in template string with tokens."""
        if not template:
            return ""
        return template.format(**self.tokens)

    def get_case(self, subgroup, dept="roto"):
        """
        Return the case block for a given subgroup (wam/sos/mro/clh/dm2).
        """
        try:
            return self.cfg["cases"][subgroup][dept]
        except KeyError as e:
            raise ValueError(f"Subgroup '{subgroup}' or dept '{dept}' not found in config") from e

    def collect_files(self, subgroup, dept="roto"):
        """
        Return a flat list of resolved file paths from the YAML structure.
        Example: { "nuke": "...nk", "sfx": "...sfx", "exr": "...exr" }
        """
        structure = self.expand_structure(subgroup, dept)

        collected = {"nuke": None, "sfx": None, "exr": None}

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k.endswith(".nk"):
                        collected["nuke"] = k
                    elif k.endswith(".sfx"):
                        collected["sfx"] = k
                    elif k.endswith(".exr") or "%04d.exr" in k:
                        collected["exr"] = k
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, str):
                if node.endswith(".nk"):
                    collected["nuke"] = node
                elif node.endswith(".sfx"):
                    collected["sfx"] = node
                elif node.endswith(".exr") or "%04d.exr" in node:
                    collected["exr"] = node

        walk(structure)
        return collected

    def build_paths(self, subgroup, dept="roto"):
        """
        Return resolved paths (flat dict: exr/nuke/sfx/folders).
        """
        case = self.get_case(subgroup, dept)
        return {
            "exr": self.resolve(case["exr_path"]),
            "nuke": self.resolve(case["nuke_file"]),
            "sfx": self.resolve(case["sfx_file"]),
            "folders": [self.resolve(f) for f in case["folders"]],
        }

    def expand_structure(self, subgroup, dept="roto"):
        """
        Expand full nested YAML structure with tokens applied.
        """
        case = self.get_case(subgroup, dept)
        raw_structure = case.get("folders", [])

        def resolve_node(node):
            if isinstance(node, dict):
                resolved = {}
                for k, v in node.items():
                    key = self.resolve(k)
                    resolved[key] = resolve_node(v)
                return resolved
            elif isinstance(node, list):
                return [resolve_node(item) for item in node]
            elif isinstance(node, str):
                return self.resolve(node)
            return node

        return resolve_node(raw_structure)




# 🔹 Example usage
if __name__ == "__main__":
    tokens = {
        "shot": "B001C020",
        "sg_plate_name": "bg01",
        "plate_name": "bg01",
        "out_version": "v003",
        "plate_version": "v0003",
    }

    builder = StructureBuilder("../configs/bfu.yaml", tokens)
    paths = builder.build_paths("wam")
    print("Flat Paths:", paths)

    structure = builder.expand_structure("wam")
    print("Tree Structure:", structure)
