"""L1 test cases: schema validation of the XT32 param file.

Each test id is a test case id from docs/04_test_cases.csv.
Cases linked to a GAP are marked xfail(strict=True). They describe the
documented or assumed behavior, which the current schema does not enforce.
If nebula fixes a gap, the test passes unexpectedly and fails the run,
which is the signal to update docs/02_gap_analysis.md.

Schema loading: the original files use relative "$id" values that break
$ref resolution (see the tooling note in docs/02_gap_analysis.md). The
schema_copies fixture copies the schemas and replaces "$id" with each copy's
absolute file URI. Schema content is not otherwise changed.
"""
import csv
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT = Path(__file__).resolve().parents[1]
NEBULA = ROOT / "nebula"
SCHEMA_DIRS = [
    Path("src/nebula_hesai/nebula_hesai/schema"),
    Path("src/nebula_core/nebula_core_ros/schema"),
]
MODEL_SCHEMA = Path("src/nebula_hesai/nebula_hesai/schema/PandarXT32.schema.json")
PARAM = NEBULA / "src/nebula_hesai/nebula_hesai/config/PandarXT32.param.yaml"
TEST_CASES = ROOT / "docs/04_test_cases.csv"
XT32_RETURN_MODES = [
    "Last", "Strongest", "LastStrongest", "First", "LastFirst", "FirstStrongest", "Dual",
]

G001 = "GAP-001: keywords next to $ref are ignored under draft-07"
G002 = "GAP-002 (assumption): 900 RPM is accepted but not listed as supported"
G004 = "GAP-004: additionalProperties at /** level is inside properties"
G005 = "GAP-005: multicast_ip pattern ends with an empty alternative"
G006 = "GAP-006: cut_angle is not checked against the FoV"
G007 = "GAP-007: profile and transport combination is not checked"
G008 = "GAP-008 (assumption): no upper bound for ports, no lower bound for MTU"
G009 = "GAP-009 (assumption): min_range < max_range is not checked"
G015 = "GAP-015: some defaults are strings for numeric or boolean types"


# ---------- fixtures ----------

@pytest.fixture(scope="session")
def schema_copies(tmp_path_factory):
    out = tmp_path_factory.mktemp("schemas").resolve()
    for rel in SCHEMA_DIRS:
        for src in (NEBULA / rel).glob("*.json"):
            data = json.loads(src.read_text())
            dst = out / rel / src.name
            data["$id"] = dst.as_uri()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(json.dumps(data, indent=2))
    return out


@pytest.fixture(scope="session")
def validator(schema_copies):
    resources = []
    for path in schema_copies.rglob("*.json"):
        data = json.loads(path.read_text())
        resources.append((data["$id"], Resource.from_contents(data, default_specification=DRAFT7)))
    registry = Registry().with_resources(resources)
    schema = json.loads((schema_copies / MODEL_SCHEMA).read_text())
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, registry=registry)


@pytest.fixture
def doc():
    return yaml.safe_load(PARAM.read_text())


def messages(validator, doc):
    return [
        f"{'.'.join(map(str, e.absolute_path))}: {e.message}"
        for e in validator.iter_errors(doc)
    ]


# ---------- mutations ----------

def params(doc):
    return doc["/**"]["ros__parameters"]


def set_(**values):
    def mutate(doc):
        params(doc).update(values)
    return mutate


def _parent(doc, path):
    node = params(doc)
    *parents, last = path.split(".")
    for key in parents:
        node = node[key]
    return node, last


def set_at(path, value):
    def mutate(doc):
        node, last = _parent(doc, path)
        node[last] = value
    return mutate


def remove(path):
    def mutate(doc):
        node, last = _parent(doc, path)
        del node[last]
    return mutate


def add_top_level(key, value):
    def mutate(doc):
        doc["/**"][key] = value
    return mutate


def no_change(doc):
    pass


def case(tc_id, mutate, gap=None):
    marks = [pytest.mark.xfail(strict=True, reason=gap)] if gap else []
    return pytest.param(tc_id, mutate, id=tc_id, marks=marks)


# ---------- cases ----------

PASS_CASES = [
    case("TC-SCH-001", no_change),
    case("TC-SCH-005", set_(cloud_min_angle=0)),
    case("TC-SCH-007", set_(cloud_max_angle=360)),
    case("TC-SCH-016", set_(rotation_speed=300)),
    case("TC-SCH-017", set_(rotation_speed=1200)),
    case("TC-SCH-024", set_(data_port=65535)),
    case("TC-SCH-028", set_(ptp_domain=127)),
    case("TC-SCH-033", set_(sync_angle=359)),
    case("TC-SCH-035", set_(dual_return_distance_threshold=0.01)),
    case("TC-SCH-041", set_(multicast_ip="")),
    case("TC-SCH-042", set_(sensor_model="PandarXT32")),
    case("TC-SCH-043", set_(ptp_profile="802.1as", ptp_transport_type="L2")),
    case("TC-SCH-044", set_(ptp_profile="automotive", ptp_transport_type="L2")),
    case("TC-SCH-045", set_(ptp_profile="1588v2", ptp_transport_type="L2")),
    case("TC-SCH-047", set_(min_range=0)),
    case("TC-SCH-052", set_(cloud_min_angle=0, cloud_max_angle=360, cut_angle=359.99)),
    case("TC-SCH-054", set_(cloud_min_angle=270, cloud_max_angle=90)),
]

REJECT_CASES = [
    case("TC-SCH-002", remove("sync_angle")),
    case("TC-SCH-003", set_(unknown_key=1)),
    case("TC-SCH-004", set_(rotation_speed="600")),
    case("TC-SCH-006", set_(cloud_min_angle=-1)),
    case("TC-SCH-008", set_(cloud_max_angle=361)),
    case("TC-SCH-009", set_(cloud_min_angle=1.5)),
    case("TC-SCH-010", set_(rotation_speed=123), G001),
    case("TC-SCH-011", set_(sensor_model="PandarAT128"), G001),
    case("TC-SCH-012", set_(sensor_model="NotAModel"), G001),
    case("TC-SCH-013", set_(return_mode="NotAMode"), G001),
    case("TC-SCH-014", set_(diagnostics={}), G001),
    case("TC-SCH-015", set_(rotation_speed=1260), G001),
    case("TC-SCH-018", set_(rotation_speed=900), G002),
    case("TC-SCH-019", set_(rotation_speed=240), G001),
    case("TC-SCH-020", add_top_level("unknown_key", 1), G004),
    case("TC-SCH-021", set_(multicast_ip="not-an-ip"), G005),
    case("TC-SCH-022", set_(cloud_min_angle=0, cloud_max_angle=360, cut_angle=360), G006),
    case("TC-SCH-023", set_(ptp_profile="802.1as", ptp_transport_type="UDP"), G007),
    case("TC-SCH-025", set_(data_port=65536), G008),
    case("TC-SCH-026", set_(packet_mtu_size=0), G008),
    case("TC-SCH-027", set_(min_range=200.0, max_range=100.0), G009),
    case("TC-SCH-029", set_(ptp_domain=128)),
    case("TC-SCH-031", set_(ptp_lock_threshold=0)),
    case("TC-SCH-032", set_(ptp_lock_threshold=101)),
    case("TC-SCH-034", set_(sync_angle=360)),
    case("TC-SCH-036", set_(dual_return_distance_threshold=0.005)),
    case("TC-SCH-037", set_(sensor_ip="192.168.1.256")),
    case("TC-SCH-038", set_(udp_socket_receive_buffer_size_bytes=255)),
    case("TC-SCH-039", set_(ptp_profile="gPTP")),
    case("TC-SCH-046", set_(ptp_profile="automotive", ptp_transport_type="UDP"), G007),
    case("TC-SCH-048", set_(min_range=-0.1)),
    case("TC-SCH-049", set_(max_range=-1.0)),
    case("TC-SCH-050", remove("diagnostics.pointcloud_publish_rate.frequency_ok.min_hz")),
    case("TC-SCH-051", set_at("diagnostics.pointcloud_publish_rate.frequency_ok.min_hz", "9.5")),
    case("TC-SCH-053", set_(cut_angle=-0.01)),
]


# ---------- tests ----------

@pytest.mark.parametrize("tc_id, mutate", PASS_CASES)
def test_value_passes_schema(validator, doc, tc_id, mutate):
    mutate(doc)
    errors = messages(validator, doc)
    assert not errors, f"{tc_id} expected to pass, got: {errors}"


@pytest.mark.parametrize("tc_id, mutate", REJECT_CASES)
def test_value_is_rejected(validator, doc, tc_id, mutate):
    mutate(doc)
    assert messages(validator, doc), f"{tc_id} expected to be rejected, but the schema accepted it"


@pytest.mark.parametrize("mode", XT32_RETURN_MODES)
def test_TC_SCH_040_documented_return_modes_pass(validator, doc, mode):
    set_(return_mode=mode)(doc)
    errors = messages(validator, doc)
    assert not errors, f"TC-SCH-040 return_mode={mode} expected to pass, got: {errors}"


TYPE_CHECK = {
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
}


def _find_default_mismatches(node, where, out):
    if isinstance(node, dict):
        declared = node.get("type")
        if declared in TYPE_CHECK and "default" in node and not TYPE_CHECK[declared](node["default"]):
            out.append(f"{where}: default {node['default']!r} is not {declared}")
        for key, value in node.items():
            _find_default_mismatches(value, f"{where}/{key}", out)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _find_default_mismatches(value, f"{where}/{i}", out)


@pytest.mark.xfail(strict=True, reason=G015)
def test_TC_SCH_030_defaults_match_declared_type(schema_copies):
    mismatches = []
    for path in sorted(schema_copies.rglob("*.json")):
        _find_default_mismatches(json.loads(path.read_text()), path.name, mismatches)
    assert not mismatches, "\n".join(mismatches)


# ---------- consistency with docs/04_test_cases.csv ----------

def _l1_rows():
    with open(TEST_CASES, newline="") as f:
        return [r for r in csv.DictReader(f) if r["executable_level"] == "L1"]


def test_every_l1_case_is_automated():
    automated = {p.id for p in PASS_CASES + REJECT_CASES} | {"TC-SCH-030", "TC-SCH-040"}
    documented = {r["tc_id"] for r in _l1_rows()}
    assert documented - automated == set(), f"not automated: {sorted(documented - automated)}"
    assert automated - documented == set(), f"not in test case list: {sorted(automated - documented)}"


def test_known_gaps_match_xfail_marks():
    xfail_ids = {p.id for p in PASS_CASES + REJECT_CASES if p.marks} | {"TC-SCH-030"}
    known_gap_ids = {r["tc_id"] for r in _l1_rows() if "known gap" in r["expected"]}
    assert xfail_ids == known_gap_ids, (
        f"xfail only: {sorted(xfail_ids - known_gap_ids)}, "
        f"csv only: {sorted(known_gap_ids - xfail_ids)}"
    )
