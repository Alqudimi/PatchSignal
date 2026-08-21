from pathlib import Path

import yaml

payload = yaml.safe_load(Path(__file__).parents[1].joinpath("action.yml").read_text(encoding="utf-8"))
assert payload["name"] == "PatchSignal"
assert payload["runs"]["using"] == "composite"
assert {"repo", "base", "head", "format", "output", "fail-on"} <= set(payload["inputs"])
assert len(payload["runs"]["steps"]) == 2
print("action_yaml_ok")
