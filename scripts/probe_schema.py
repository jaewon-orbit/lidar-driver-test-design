"""Probe how PandarXT32.schema.json handles gap candidate values.

This is an exploration script, not the test suite. Each case mutates the
default XT32 YAML, validates it with check-jsonschema, and compares the
result with what the docs or other sources say should happen.
CTRL cases are controls that the schema must reject if the tool works.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

NEBULA = Path("nebula")
SCHEMA = NEBULA / "src/nebula_hesai/nebula_hesai/schema/PandarXT32.schema.json"
PARAM = NEBULA / "src/nebula_hesai/nebula_hesai/config/PandarXT32.param.yaml"


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


def validate(doc, tmpdir, case_id):
    path = Path(tmpdir) / f"{case_id}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    result = subprocess.run(
        ["check-jsonschema", "--schemafile", str(SCHEMA), str(path)],
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def main():
    base_text = PARAM.read_text()
    rows, details = [], []
    with tempfile.TemporaryDirectory() as tmpdir:
        for case_id, desc, mutate, expected in CASES:
            doc = yaml.safe_load(base_text)
            mutate(doc)
            code, log = validate(doc, tmpdir, case_id)
            actual = {0: "pass", 1: "reject"}.get(code, f"error({code})")
            if expected == "unclear":
                match = "-"
            else:
                match = "yes" if actual == expected else "NO"
            rows.append((case_id, desc, expected, actual, match))
            if actual != "pass":
                details.append(f"[{case_id}]\n{log}\n")

    print("| case | description | expected | actual | match |")
    print("|---|---|---|---|---|")
    for row in rows:
        print("| " + " | ".join(row) + " |")
    print("\n## Details for non-pass cases\n")
    print("\n".join(details))
    return 0


if __name__ == "__main__":
    sys.exit(main())
