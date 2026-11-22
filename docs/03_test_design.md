# 03. Test Design

Baseline: tier4/nebula 4e02244, Pandar XT32. File abbreviations follow 02_gap_analysis.md.

## 1. Requirements
Requirements are taken from the docs, schemas and code. Each one keeps its source so a reviewer can check it.

| REQ ID | Requirement | Source |
|---|---|---|
| REQ-SCH-01 | The param file contains every required parameter and no unknown parameter | model schema L120-L151 |
| REQ-MODEL-01 | sensor_model is PandarXT32 in the XT32 param file | model schema L63-L66 |
| REQ-NET-01 | host_ip and sensor_ip are IPv4 addresses | communication.json L39-L45, L65-L71 |
| REQ-NET-02 | multicast_ip is empty or a multicast address | communication.json L51-L57 |
| REQ-NET-03 | data_port, gnss_port and packet_mtu_size are integers of at least 0 | communication.json L20-L38, L58-L64 |
| REQ-NET-04 | udp_socket_receive_buffer_size_bytes is at least 256 | hesai schema L39-L44 |
| REQ-FOV-01 | cloud_min_angle and cloud_max_angle are integers from 0 to 360 | misc.json L17-L30 |
| REQ-FOV-02 | The FoV may cross 0 deg (e.g. 270 to 90) | common.md L94 |
| REQ-FOV-03 | The output point cloud has exactly the configured FoV | common.md L96-L97 |
| REQ-CUT-01 | cut_angle is in (cloud_min_angle, cloud_max_angle], or [0, 360) for 360 deg FoV, and sets scan timing as in the examples table | common.md L43-L46, L82-L89, L107 |
| REQ-SYNC-01 | sync_angle is an integer from 0 to 359 | hesai schema L84-L90 |
| REQ-ROT-01 | rotation_speed is one of the supported RPM values | hesai schema L45-L51, wrapper L199-L212 |
| REQ-RM-01 | return_mode is one of the 7 XT32 values | model schema L76-L87 |
| REQ-PTP-01 | ptp_profile is 1588v2, 802.1as or automotive | hesai schema L52-L57, common.md L11 |
| REQ-PTP-02 | ptp_domain is an integer from 0 to 127 | hesai schema L58-L64 |
| REQ-PTP-03 | 802.1as and automotive use only L2 transport | common.md L19 |
| REQ-PTP-05 | ptp_lock_threshold is an integer from 1 to 100 microseconds | hesai schema L77-L83 |
| REQ-PTP-06 | Hardware monitor: locked is OK, tracking is WARNING, frozen and free run are ERROR | common.md L33 |
| REQ-RNG-01 | min_range and max_range are numbers of at least 0 | misc.json L66-L77 |
| REQ-DRT-01 | dual_return_distance_threshold is from 0.01 to 0.5 | misc.json L59-L65 |
| REQ-DIAG-01 | Point cloud publish rate is OK, WARN or ERROR by the configured bounds | diagnostics.json L6-L51 |

## 2. Techniques

| Technique | Applied to | Why |
|---|---|---|
| Equivalence partitioning | return_mode, sensor_model, ptp_profile, IP strings, parameter types | These take values from a set. One value per class (valid, invalid, wrong type) is enough |
| Boundary value analysis | angles, rotation_speed, ports, ptp_domain, ptp_lock_threshold, dual_return_distance_threshold, buffer size | Ranges are where docs, schema and code types disagree (GAP-002, GAP-008). Each boundary gets the value on it and the value just outside |
| Decision table | ptp_profile x ptp_transport_type, model x return_mode | Validity depends on a combination, not one value (GAP-007, GAP-012) |
| State transition | PTP sync state and diagnostic status | REQ-PTP-06 maps states to statuses. The transition timing is not documented, so transitions get their own cases |
| Interaction cases | cut_angle with FoV, min_range with max_range, rotation_speed with diagnostics bounds | The docs define rules across parameters that no single-value check covers (GAP-006, GAP-009, GAP-010) |
| Pairwise (planned) | FoV x cut_angle x rotation_speed | Full combinations are 27 or more. Pairwise keeps all pairs with 9 cases (see section 5) |

## 3. Executable levels

| Level | Meaning | Needs |
|---|---|---|
| L1 | Checked with files only (schema validation) | Python, check-jsonschema |
| L2 | Checked by launching the ROS node without a sensor (launch_hw=false) | ROS 2 container |
| L3 | Checked with recorded sensor data | rosbag of XT32 |
| L4 | Needs a real sensor | XT32 and a PTP master |

L1 cases are automated in tests/test_param_schema.py. L2 to L4 cases are designed but not executed in this project unless noted.

## 4. Rules used when writing cases
- Valid values are tested next to invalid ones. A schema that rejects everything would also pass a set of invalid-only cases
- Expected results linked to a GAP describe the documented or assumed behavior, not the current behavior. Where the current behavior differs, the expected result says "known gap: currently passes"
- When the expected result comes from an assumption, the basis column says Assumption and the text starts with "(assumption)"
- Priority: High if a wrong value can produce wrong data or a silent misconfiguration, Medium if it produces a visible error or warning, Low for documentation only

## 5. Pairwise plan (L3, not yet executed)

| # | FoV | cut_angle | rotation_speed |
|---|---|---|---|
| 1 | 0 to 360 | 0 | 300 |
| 2 | 0 to 360 | 180 | 600 |
| 3 | 0 to 360 | 359 | 1200 |
| 4 | 90 to 315 | 315 (end) | 300 |
| 5 | 90 to 315 | 180 (inside) | 600 |
| 6 | 90 to 315 | 91 (near start) | 1200 |
| 7 | 270 to 90 | 90 (end) | 300 |
| 8 | 270 to 90 | 0 (inside) | 600 |
| 9 | 270 to 90 | 271 (near start) | 1200 |
