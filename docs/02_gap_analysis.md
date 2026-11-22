# 02. Gap Analysis

## Candidates (unverified)
These are hypotheses found while reading sources. Each will be verified before being promoted to a GAP entry.
Paths: model schema = src/nebula_hesai/nebula_hesai/schema/PandarXT32.schema.json, hesai schema = src/nebula_hesai/nebula_hesai/schema/lidar_hesai.json, core schemas = src/nebula_core/nebula_core_ros/schema/*.json

| ID | Summary | Source | How to verify |
|---|---|---|---|
| C-01 | Keywords next to $ref may be ignored under draft-07. Affected: sensor_model enum, return_mode enum, diagnostics required (model schema), sensor_model enum, rotation_speed min/max/multipleOf, gnss_port default/minimum (hesai schema) | model schema L63-L66, L76-L87, L112-L115; hesai schema L6-L20, L34-L38, L45-L51 | L1: rotation_speed=123, sensor_model=PandarAT128 |
| C-02 | "additionalProperties": false sits inside "properties" of "/**", so it may act as a property name instead of a rule | model schema L161 | L1: add an unknown key under "/**" |
| C-03 | min_range and max_range are not required, while most other parameters are | model schema L120-L150 | Check code defaults when omitted |
| C-04 | xt32.md and the top of common.md are generated from schemas, so only hand-written parts of common.md can disagree with the schema | xt32.md L1, common.md L3 | Note in scope |
| C-05 | multicast_ip pattern ends with "|", an empty alternative that may match any string | communication.json L54 | L1: multicast_ip="not-an-ip" |
| C-06 | Doc limits cut_angle to (cloud_min_angle, cloud_max_angle], or [0, 360) for 360 deg FoV, but schema allows 0-360 regardless of FoV. Wrap-around FoV case (e.g. 270 to 90) is not described | common.md L107; hesai schema L91-L97 | L1: cut_angle=360 with FoV 0-360 |
| C-07 | Doc says only L2 is allowed for 802.1as and automotive, but schema does not enforce it. Schema already uses if/then elsewhere | common.md L19; hesai schema L65-L70, L150-L163 | L1: ptp_profile=802.1as, ptp_transport_type=UDP |
| C-08 | Doc says ptp_lock_threshold only applies to OT128 and QT128, but it is required in the XT32 schema | common.md L29; model schema L146 | Check code for XT32 handling |
| C-09 | Diagnostics publish rate bounds assume 10 Hz and are not tied to rotation_speed. rotation_speed=1200 (20 Hz) may trigger false errors | PandarXT32.param.yaml L24, L33-L38 | Check how diagnostics are evaluated in code |
| C-10 | data_port, gnss_port, packet_mtu_size have minimum 0 and no maximum. gnss_port is uint16_t in code | communication.json L20-L26, L32-L38, L58-L64; hesai_common.hpp L181 | L1: gnss_port=70000, packet_mtu_size=0 |
| C-11 | Behavior for cloud_min_angle == cloud_max_angle, or cloud_min_angle=360, is not defined | common.md L93-L94; misc.json L17-L30 | Check code |
| C-12 | Schema defaults are strings for integer and boolean types ("600", "true"), and multicast_ip default is two quote characters as text | hesai schema L32, L47; hardware.json L8 | Note, check generated docs |
| C-13 | No rule that min_range must be less than max_range | misc.json L66-L77 | L1: min_range=200, max_range=100 |
| C-14 | diag_span is described as "Diagnostics rate" with no unit | topic.json L18-L24 | Check code |

## Notes from code reading
Runtime ranges are ROS parameter descriptors in src/nebula_hesai/nebula_hesai/src/hesai_ros_wrapper.cpp.
- Base structs: nebula_common.hpp L301-L334. data_port (L312) and packet_mtu_size (L331) are uint16_t
- C-01: rotation_speed allowed values disagree across three places. Schema: 300-1200, multipleOf 60. Runtime range: 300-1200 step 300 (300, 600, 900, 1200). Runtime description: "300, 600, 1200". hesai_ros_wrapper.cpp L199-L212. XT32 supported RPM to check in vendor manual
- C-06: cut_angle runtime range is 0-360 step 0.01 with no FoV relation (L169-L176). Description says "Cannot be equal to the start angle in a non-360 deg FoV", which is worded differently from common.md L107
- C-07 confirmed: a WARN is logged and the parameter is overwritten to L2 (L243-L253). Doc wording suggests rejection, code auto-corrects
- C-08 contradicts docs: hesai_hw_interface.cpp L1164-L1176 applies ptp_lock_threshold to Pandar128E4X, QT128, XT16, XT32, XT32M. Doc says it only applies to OT128 and QT128, and OT128 is not in this list
- C-10: data_port, gnss_port (L157-L158) and packet_mtu_size (L192) are declared as uint16_t with no range. Overflow behavior to check at L2
- C-13: min_range and max_range are declared with no range (L190-L191)
- Matching ranges (schema and runtime agree): udp_socket_receive_buffer_size_bytes min 256, sync_angle 0-359, cloud_min_angle and cloud_max_angle 0-360, ptp_domain 0-127, ptp_lock_threshold 1-100, dual_return_distance_threshold 0.01-0.5
- C-09: rate bounds are built from rotation_speed via get_scan_rate_hz (decoder_wrapper.hpp L96-L99). Whether YAML diagnostics bounds are used is still to check
- C-09 partly confirmed: YAML bounds are used (decoder_wrapper.hpp L101-L110). If the nominal rate from rotation_speed is outside frequency_ok, only a startup WARN is logged (L115-L122). So rotation_speed and diagnostics bounds must be changed together, and this rule is not in the docs
- C-15 (new): num_frame_transition default is 3 in diagnostics.json L43-L48 but 1 in code (decoder_wrapper.hpp L112-L113). frequency_ok.max_hz and frequency_warn.max_hz default to infinity in code when omitted, which the schema does not describe
- C-16 (new): "Dual" maps to a different mode per model. XT32: Dual = LastStrongest. QT64: Dual = LastFirst (hesai_common.hpp L617-L657). Docs do not state this. XT32 return_mode enum in schema matches the 7 strings in code
