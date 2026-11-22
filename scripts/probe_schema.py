"""Probe how PandarXT32.schema.json handles gap candidate values.

This is an exploration script, not the test suite. Each case mutates the
default XT32 YAML, validates it with check-jsonschema, and compares the
result with what the docs or other sources say should happen.
CTRL cases are controls that the schema must reject if the tool works.

Schema loading (C-17): the original files declare relative "$id" values such
as "nebula_hesai/schema/lidar_hesai.json", which break $ref resolution in
check-jsonschema. The script first compares three ways of loading the schemas
and uses the first one where BASE passes and CTRL-1 is rejected:
  original     schema files as they are
  id_removed   "$id" removed in temp copies
  id_absolute  "$id" replaced with each temp copy's absolute file URI
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

NEBULA = Path("nebula")
SCHEMA_DIRS = [
    Path("src/nebula_hesai/nebula_hesai/schema"),
    Path("src/nebula_core/nebula_core_ros/schema"),
]
MODEL_SCHEMA = Path("src/nebula_hesai/nebula_hesai/schema/PandarXT32.schema.json")
PARAM = NEBULA / "src/nebula_hesai/nebula_hesai/config/PandarXT32.param.yaml"
VARIANTS = ["original", "id_removed", "id_absolute"]


def params(doc):
    return doc["/**"]["ros__parameters"]


def set_params(**values):
    def mutate(doc):
        params(doc).update(values)
    return mutate


def add_top_level_key(doc):
    doc["/**"]["unknown_key"] = 1


def add_param_key(doc):
    params(doc)["unknown_key"] = 1


def empty_diagnostics(doc):
    params(doc)["diagnostics"] = {}


def no_change(doc):
    pass


# (case id, description, mutation, expected result per docs or other sources)
CASES = [
    ("BASE", "default YAML", no_change, "pass"),
    ("CTRL-1", "cloud_min_angle=-1", set_params(cloud_min_angle=-1), "reject"),
    ("CTRL-2", "ptp_domain=128", set_params(ptp_domain=128), "reject"),
    ("CTRL-3", "unknown key inside ros__parameters", add_param_key, "reject"),
    ("C-01a", "rotation_speed=123", set_params(rotation_speed=123), "reject"),
    ("C-01b", "rotation_speed=900", set_params(rotation_speed=900), "unclear"),
    ("C-01c", "sensor_model=PandarAT128", set_params(sensor_model="PandarAT128"), "reject"),
    ("C-01d", "sensor_model=NotAModel", set_params(sensor_model="NotAModel"), "reject"),
    ("C-01e", "return_mode=NotAMode", set_params(return_mode="NotAMode"), "reject"),
    ("C-01f", "diagnostics without pointcloud_publish_rate", empty_diagnostics, "reject"),
    ("C-02", "unknown key next to ros__parameters", add_top_level_key, "reject"),
    ("C-05", "multicast_ip=not-an-ip", set_params(multicast_ip="not-an-ip"), "reject"),
    ("C-06", "cut_angle=360 with FoV 0-360", set_params(cut_angle=360), "reject"),
    ("C-07", "ptp_profile=802.1as with UDP",
     set_params(ptp_profile="802.1as", ptp_transport_type="UDP"), "reject"),
    ("C-10a", "data_port=70000", set_params(data_port=70000), "reject"),
    ("C-10b", "gnss_port=70000", set_params(gnss_port=70000), "reject"),
    ("C-10c", "packet_mtu_size=0", set_params(packet_mtu_size=0), "reject"),
    ("C-13", "min_range=200, max_range=100",
     set_params(min_range=200.0, max_range=100.0), "reject"),
]


def prepare_schemas(workdir, variant):
    if variant == "original":
        return (NEBULA / MODEL_SCHEMA).resolve()
    out = workdir / variant
    for rel in SCHEMA_DIRS:
        for src in (NEBULA / rel).glob("*.json"):
            data = json.loads(src.read_text())
            dst = out / rel / src.name
            if variant == "id_removed":
                data.pop("$id", None)
            elif variant == "id_absolute":
                data["$id"] = dst.as_uri()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(json.dumps(data, indent=2))
    return out / MODEL_SCHEMA


def validate(schema, doc, workdir, name):
    path = workdir / f"{name}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    result = subprocess.run(
        ["check-jsonschema", "--schemafile", str(schema), str(path)],
        capture_output=True,
        text=True,
    )
    log = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return "pass", log
    if result.returncode == 1 and "Schema validation errors" in log:
        return "reject", log
    return f"error({result.returncode})", log


def tail(log, n=3):
    lines = [line.strip() for line in log.splitlines() if line.strip()]
    return "\n    ".join(lines[-n:])


def main():
    base_text = PARAM.read_text()
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp).resolve()

        print("## Schema loading comparison (BASE should pass, CTRL-1 should reject)\n")
        chosen = None
        for variant in VARIANTS:
            schema = prepare_schemas(workdir, variant)
            base, base_log = validate(schema, yaml.safe_load(base_text), workdir, f"{variant}-base")
            doc = yaml.safe_load(base_text)
            set_params(cloud_min_angle=-1)(doc)
            ctrl, _ = validate(schema, doc, workdir, f"{variant}-ctrl")
            print(f"- {variant}: BASE={base}, CTRL-1={ctrl}")
            if base != "pass":
                print(f"    {tail(base_log)}")
            if chosen is None and base == "pass" and ctrl == "reject":
                chosen = (variant, schema)

        if chosen is None:
            print("\nNo variant works. Stopping.")
            return 1

        variant, schema = chosen
        print(f"\nUsing variant: {variant}\n")
        print("| case | description | expected | actual | match |")
        print("|---|---|---|---|---|")
        details = []
        for case_id, desc, mutate, expected in CASES:
            doc = yaml.safe_load(base_text)
            mutate(doc)
            actual, log = validate(schema, doc, workdir, case_id)
            match = "-" if expected == "unclear" else ("yes" if actual == expected else "NO")
            print(f"| {case_id} | {desc} | {expected} | {actual} | {match} |")
            if actual != "pass":
                details.append(f"[{case_id}]\n    {tail(log)}")
        print("\n## Details for non-pass cases (last lines)\n")
        print("\n".join(details))
    return 0


if __name__ == "__main__":
    sys.exit(main())
