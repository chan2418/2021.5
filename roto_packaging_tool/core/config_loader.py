# config_loader.py
import yaml
import os

class ConfigLoader:
    def __init__(self, base_dir):
        self.base_dir = base_dir

    def load_yaml(self, name):
        path = os.path.join(self.base_dir, f"{name}.yaml")
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def load_global(self):
        return self.load_yaml("global")

    def load_show(self, show_name):
        return self.load_yaml(show_name)
