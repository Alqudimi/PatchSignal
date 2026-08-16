from pathlib import Path

import yaml

payload = yaml.safe_load(Path(__file__).parents[1].joinpath(".github", "workflows", "ci.yml").read_text())
assert payload["name"] == "CI"
assert "jobs" in payload and "quality" in payload["jobs"]
print("workflow_yaml_ok")
