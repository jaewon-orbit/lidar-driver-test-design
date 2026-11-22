# 02. Gap Analysis

Baseline: tier4/nebula 4e02244, Pandar XT32. See 00_scope.md.

## Method
1. Read sources A to D and record candidates (C-xx)
2. Verify each candidate: schema behavior with scripts/probe_schema.py (L1), code reading for runtime behavior, node runs without a sensor for launch behavior (L2), replay of nebula's recorded XT32 data for output behavior (L3)
3. Promote verified candidates to GAP entries. Merge candidates with the same root cause
4. Mark every assumption as an assumption. Facts come with a file and line reference

File abbreviations:
- model schema: src/nebula_hesai/nebula_hesai/schema/PandarXT32.schema.json
- hesai schema: src/nebula_hesai/nebula_hesai/schema/lidar_hesai.json
- core schemas: src/nebula_core/nebula_core_ros/schema/*.json
- wrapper: src/nebula_hesai/nebula_hesai/src/hesai_ros_wrapper.cpp
- probe: docs/evidence/probe-2026-11-22.md
- L2 run: docs/evidence/l2-run-2026-11-22.md
- L3 run: docs/evidence/l3-replay-2026-11-23.md

## Summary

| ID | Title | Category | Verified by |
|---|---|---|---|
| GAP-001 | Model-specific schema constraints are not enforced | Inconsistency | probe (L1) |
| GAP-002 | rotation_speed allowed values differ across three places | Inconsistency | code reading, L2 run |
| GAP-003 | ptp_lock_threshold applicability differs between docs and code | Inconsistency | code reading |
| GAP-004 | additionalProperties at "/**" level has no effect | Inconsistency | probe (L1) |
| GAP-005 | multicast_ip pattern accepts any string | Inconsistency | probe (L1) |
| GAP-006 | cut_angle range depends on FoV; only the driver checks the relation | Inconsistency | probe (L1), code reading, L3 run |
| GAP-007 | PTP transport rule is documented as a restriction but handled as auto-correction | Inconsistency | probe (L1), code reading, L2 run |
| GAP-008 | Ports and MTU have no upper bound while code uses uint16_t | Missing | probe (L1), code reading, L2 run |
| GAP-009 | min_range and max_range are optional, unordered, with differing defaults | Missing | probe (L1), code reading, L2 run |
| GAP-010 | rotation_speed and diagnostics rate bounds must change together | Interaction undefined | code reading, L2 run |
| GAP-011 | num_frame_transition default differs between schema and code | Inconsistency | code reading, L2 run |
| GAP-012 | "Dual" return mode means different modes per model | Ambiguity | code reading, L2 run |
| GAP-013 | Degenerate FoV settings are not defined in the user docs | Ambiguity | doc reading, code reading, L2 run, L3 run |
| GAP-014 | diag_span has no unit | Missing | doc reading |
| GAP-015 | Schema defaults are strings for numeric and boolean types | Inconsistency | doc reading |

---

### GAP-001: Model-specific schema constraints are not enforced
- Category: Inconsistency (written constraints vs effective behavior)
- Parameters: sensor_model, return_mode, rotation_speed, gnss_port, diagnostics
- Evidence:
  - Schema: enum, minimum, maximum, multipleOf and required are written next to "$ref" in model schema L63-L66, L76-L87, L112-L115 and hesai schema L6-L20, L34-L38, L45-L51. The schemas declare draft-07 (L2), where keywords next to "$ref" are ignored
  - Probe: rotation_speed=123, sensor_model=NotAModel, sensor_model=PandarAT128, return_mode=NotAMode and diagnostics without pointcloud_publish_rate all pass (C-01a to C-01f)
  - Control: constraints without "$ref" work (cloud_min_angle=-1 and ptp_domain=128 are rejected)
- Assumption: The authors intended these constraints to apply, since they wrote them per model. I treat the written constraints as the expected behavior
- Impact: A param file for the wrong model, an invalid RPM or an unknown return mode passes file validation. Errors appear only at launch, or not at all if the runtime also accepts the value
- Question: Should these keywords be wrapped in "allOf" with the "$ref", or the schemas moved to draft 2019-09 or later?
- Linked test cases: TC-SCH-010 to TC-SCH-015, TC-SCH-019 (L1, automated)

### GAP-002: rotation_speed allowed values differ across three places
- Category: Inconsistency
- Parameters: rotation_speed
- Evidence:
  - Schema: hesai schema L45-L51, 300 to 1200, multipleOf 60
  - Runtime range: wrapper L199-L212, integer_range 300 to 1200 step 300 (300, 600, 900, 1200)
  - Runtime description: wrapper L199-L212, additional_constraints "300, 600, 1200"
  - Default YAML: PandarXT32.param.yaml L24, 600
  - L2 run (TC-RUN-001, 3 of 3 runs): rotation_speed=900 is accepted and the node starts with "Rotation Speed: 900". `ros2 param describe` shows Min 300, Max 1200, Step 300 and "Additional constraints: 300, 600, 1200". rotation_speed=360 aborts startup with InvalidParameterValueException (TC-RUN-005)
- Assumption: XT32 supports 300, 600 and 1200 RPM (5, 10 and 20 Hz), as the runtime description says. To be confirmed with the vendor manual (source E). The L2 run shows what the driver accepts, not what the sensor supports, so it does not settle this
- Impact: 900 is accepted by the schema and, as observed at L2, by the runtime range, but is not listed as supported. Once GAP-001 is fixed, values like 360 would pass the schema but fail at launch
- Question: Is 900 RPM supported on XT32, and which source is authoritative?
- Linked test cases: TC-SCH-018 (L1, automated), TC-RUN-001 (L2, run 2026-11-22). Related: TC-SCH-016 (L1, automated, linked to REQ-ROT-01)

### GAP-003: ptp_lock_threshold applicability differs between docs and code
- Category: Inconsistency
- Parameters: ptp_lock_threshold
- Evidence:
  - Doc: common.md L29, "Only applies to OT128 and QT128"
  - Code: src/nebula_hesai/nebula_hesai_hw_interfaces/src/hesai_hw_interface.cpp L1164-L1176 writes the value to Pandar128E4X, QT128, XT16, XT32 and XT32M. OT128 is not in this list
  - Schema: model schema L146, required for XT32
- Assumption: The code reflects actual behavior and the doc is outdated
- Impact: Users following the doc may treat this value as unused on XT32, while the driver writes it to the sensor. The value decides when the sensor reports locked or tracking, which changes the diagnostic status
- Question: Is the list in common.md outdated, and does OT128 apply this value in another code path?
- Linked test cases: TC-PTP-010 (L4, not run)

### GAP-004: additionalProperties at "/**" level has no effect
- Category: Inconsistency
- Parameters: (structure)
- Evidence:
  - Schema: model schema L161 puts "additionalProperties": false inside "properties" of "/**", so it is read as a property name, not a rule
  - Probe: an unknown key next to ros__parameters passes (C-02). Control: an unknown key inside ros__parameters is rejected (CTRL-3), where the same rule is placed correctly (L151)
- Assumption: The intent is to forbid unknown keys at "/**" level, like one level below
- Impact: Parameters placed at the wrong level are silently ignored instead of being reported
- Question: Can the keyword be moved out of "properties"?
- Linked test cases: TC-SCH-020 (L1, automated)

### GAP-005: multicast_ip pattern accepts any string
- Category: Inconsistency
- Parameters: multicast_ip
- Evidence:
  - Schema: communication.json L54, the pattern ends with "|", an empty alternative. "pattern" is not anchored, so the empty alternative matches every string
  - Probe: multicast_ip="not-an-ip" passes (C-05). This rule is not next to a "$ref", so it is independent of GAP-001
- Assumption: Valid values are an empty string (multicast disabled) or an address in 224.0.0.0 to 239.255.255.255
- Impact: Typos are only found when the socket is opened
- Question: Should the pattern be "^$|^(...)$"?
- Linked test cases: TC-SCH-021 (L1, automated)

### GAP-006: cut_angle range depends on FoV; only the driver checks the relation
- Category: Inconsistency (originally recorded as Interaction undefined, changed after the driver check was found)
- Parameters: cut_angle, cloud_min_angle, cloud_max_angle
- Evidence:
  - Doc: common.md L107, cut_angle must be in (cloud_min_angle, cloud_max_angle], or [0, 360) for a 360 deg FoV
  - Schema: hesai schema L91-L97, 0 to 360 with no relation to FoV
  - Runtime: wrapper L169-L176, 0 to 360 step 0.01. The description says "Cannot be equal to the start angle in a non-360 deg FoV", worded differently from the doc
  - Probe: cut_angle=360 with FoV 0 to 360 passes (C-06)
  - Driver check: validate_decoder_settings (src/nebula_hesai/nebula_hesai_decoders/include/nebula_hesai_decoders/hesai_decoder_settings.hpp L46-L59), called at startup (wrapper L365), rejects a cut_angle outside the FoV, a cut_angle equal to the start of a partial FoV, and cut_angle=360 for a 0 to 360 FoV. nebula's unit tests cover these rules, including a FoV that crosses 0 deg (src/nebula_hesai/nebula_hesai_decoders/tests/test_hesai_decoder_settings.cpp L77-L144)
  - L3 run (TC-FOV-010, 3 of 3 runs): cut_angle=360 with FoV 0 to 360 aborts startup with "Cannot cut a 360deg FoV at 360deg. Cut at 0deg instead." FoV 90 to 315 with the default cut_angle 0 aborts with "Cannot cut scan outside of the FoV."
- Assumption: The earlier assumption (values outside the doc range are rejected before connecting) is confirmed by the driver check, also for a FoV that crosses 0 deg. The remaining gap is the schema, which accepts these values
- Impact: A param file that passes schema validation can still stop the driver at launch. With the default cut_angle 0, a partial FoV must contain 0 deg and must not start at 0 deg; otherwise cut_angle has to be set (hesai_decoder_settings.hpp L46-L53)
- Question: Should the schema express the cut_angle rule (for example with if/then), so that file validation matches the driver check?
- Linked test cases: TC-SCH-022 (L1, automated), TC-FOV-010 (L3, run 2026-11-23)

### GAP-007: PTP transport rule is documented as a restriction but handled as auto-correction
- Category: Inconsistency
- Parameters: ptp_profile, ptp_transport_type
- Evidence:
  - Doc: common.md L19, "For 802.1as and automotive, only L2 is allowed"
  - Schema: hesai schema L65-L70 has no rule. The same file uses if/then elsewhere (L150-L163), so the rule is expressible
  - Probe: ptp_profile=802.1as with UDP passes (C-07)
  - Runtime: wrapper L240-L253 logs a WARN, sets the internal config to L2 (L251) and calls set_parameter to change the parameter to L2 (L252). The parameter is declared read-only (L240), and the result of set_parameter is not checked
  - L2 run (TC-RUN-002, 3 of 3 runs): the WARN is logged and the logged configuration shows "PTP Transport Type: L2", but `ros2 param get` returns UDP. `ros2 param describe` shows "Read only: true". An external `ros2 param set` to L2 is refused with "cannot be set because it is read-only". Control: the same command changes min_range (read-write) to 0.1
- Assumption: Auto-correction is the intended behavior, and the doc should describe it. I also assume the update at L252 is meant to succeed, so that the parameter shows the value in use. That it fails for the read-only reason is inferred from the external set result, not traced inside rclcpp
- Impact: The parameter reports UDP while the driver uses L2. Users and tools that read parameters see the wrong value. Only the WARN line and the configuration log show the value in use
- Question: Should the schema reject this combination, or should the doc describe the auto-correction? Should the update at L252 succeed (for example, by checking its result), so that the parameter matches the value in use?
- Linked test cases: TC-SCH-023, TC-SCH-046 (L1, automated), TC-RUN-002 (L2, run 2026-11-22: Fail)
- Upstream issue: https://github.com/tier4/nebula/issues/564 (reported 2026-11-23)

### GAP-008: Ports and MTU have no upper bound while code uses uint16_t
- Category: Missing
- Parameters: data_port, gnss_port, packet_mtu_size
- Evidence:
  - Schema: communication.json L20-L26, L32-L38, L58-L64, minimum 0 and no maximum
  - Code: nebula_common.hpp L312 and L331, hesai_common.hpp L181, all uint16_t. Declared without a range in wrapper L157-L158 and L192
  - Probe: data_port=70000, gnss_port=70000 and packet_mtu_size=0 pass (C-10a to C-10c)
  - L2 run (TC-RUN-003, 3 of 3 runs): data_port=70000 is accepted. The logged configuration shows "Data Port: 4464" (70000 - 65536), while `ros2 param get` returns 70000. `ros2 param describe` shows an integer, read-only, with no range
  - Code path: rclcpp returns integer parameters as int64_t (/opt/ros/jazzy/include/rclcpp/rclcpp/parameter_value.hpp L261-L267). The wrapper stores the value in data_port, a uint16_t field (L157, nebula_common.hpp L312). The hardware interface opens the data socket with this field (src/nebula_hesai/nebula_hesai_hw_interfaces/src/hesai_hw_interface.cpp L228)
- Assumption: Valid ports are 1 to 65535, and MTU must be large enough for one sensor packet (exact minimum to confirm)
- Impact: A data_port above 65535 is silently wrapped to a different port (observed at L2). With a sensor, the driver would open the data socket on that port (code reading, L228; not observed, because launch_hw=false opens no socket). gnss_port and packet_mtu_size are declared the same way (L158, L192) but were not run
- Question: Can maximum 65535 be added, and is there a minimum MTU?
- Linked test cases: TC-SCH-025, TC-SCH-026 (L1, automated), TC-RUN-003 (L2, run 2026-11-22). Related: TC-SCH-024 (L1, automated, linked to REQ-NET-03)

### GAP-009: min_range and max_range are optional, unordered, with differing defaults
- Category: Missing
- Parameters: min_range, max_range
- Evidence:
  - Schema: not in the required list (model schema L120-L150). misc.json L66-L77 gives defaults 0.3 and 300.0, minimum 0, no ordering rule
  - Default YAML: 0.05 and 120.0
  - Runtime: wrapper L190-L191 declares both without a default value or range
  - Probe: min_range=200 with max_range=100 passes (C-13)
  - L2 run (TC-RUN-004, 3 of 3 runs): with the min_range line removed from the default YAML, startup aborts with rclcpp::ParameterTypeException "expected [double] got [not set]". The message does not name the parameter. Control: the unchanged YAML starts (TC-RUN-006)
- Assumption: min_range must be less than max_range. The earlier assumption that omitting min_range fails at launch is confirmed at L2. Omitting max_range was not run
- Impact: An inverted range would filter out every point (assumption, not run). Schema and runtime disagree on whether min_range is required: the schema marks it optional, the driver does not start without it, and the error does not say which parameter is missing
- Question: Should both be required, and should the schema enforce min_range < max_range?
- Linked test cases: TC-SCH-027 (L1, automated), TC-RUN-004 (L2, run 2026-11-22)

### GAP-010: rotation_speed and diagnostics rate bounds must change together
- Category: Interaction undefined
- Parameters: rotation_speed, diagnostics.pointcloud_publish_rate
- Evidence:
  - Default YAML: L24 rotation_speed 600, L33-L38 bounds 9.5 to 10.5 Hz (OK) and 9.0 to 11.0 Hz (WARN)
  - Code: src/nebula_hesai/nebula_hesai/include/nebula_hesai/decoder_wrapper.hpp L96-L122. The nominal rate is computed from rotation_speed, the bounds come from parameters, and a mismatch only logs a startup WARN
  - Docs: no statement that the bounds must follow rotation_speed
  - L2 run (TC-DIAG-001, 3 of 3 runs): rotation_speed=1200 with the default bounds logs "The configured sensor framerate (1200 RPM = 20.00 Hz) is outside the configured framerate bounds: 9.50 - 10.50", and the node keeps running. rotation_speed=900 logs the same WARN with 15.00 Hz (TC-RUN-001)
- Assumption: The driver's rate calculation is confirmed by the WARN text (1200 RPM gives 20 Hz, 900 RPM gives 15 Hz). The diagnostic status during operation is assumed, not observed: no packets arrive with launch_hw=false
- Impact: Changing only rotation_speed to 1200 gives a startup WARN (observed at L2). The diagnostic would then report ERROR while the sensor works normally (assumption, needs recorded data at that rate or a sensor)
- Question: Should the default bounds be derived from rotation_speed, or should the docs state this rule?
- Linked test cases: TC-DIAG-001 (L2, run 2026-11-22)

### GAP-011: num_frame_transition default differs between schema and code
- Category: Inconsistency
- Parameters: diagnostics.pointcloud_publish_rate.num_frame_transition
- Evidence:
  - Schema and code: diagnostics.json L43-L48 default 3; decoder_wrapper.hpp L112-L113 default 1. The XT32 YAML does not set it
  - L2 run (TC-DIAG-003, 3 of 3 runs): with the default XT32 YAML, `ros2 param dump` shows num_frame_transition: 1
- Assumption: The generated docs show 3, while the driver uses 1
- Impact: The diagnostic status changes after 1 frame instead of 3, so it may flap more than users expect
- Question: Which default is intended?
- Linked test cases: TC-DIAG-002 (L3, not run: the available recording has no packet gap, see L3 run), TC-DIAG-003 (L2, run 2026-11-22)

### GAP-012: "Dual" return mode means different modes per model
- Category: Ambiguity
- Parameters: return_mode
- Evidence:
  - Code: hesai_common.hpp L617-L657. For XT32, "Dual" equals "LastStrongest". For QT64, "Dual" equals "LastFirst". The XT32 enum (model schema L78-L86) lists both "Dual" and "LastStrongest" without saying they are the same
  - L2 run (TC-RM-001 and TC-RM-002, 3 of 3 runs each): return_mode=Dual and return_mode=LastStrongest both log "Return Mode: LastStrongest". The parameter keeps the value as written (Dual)
- Assumption: For XT32, "Dual" is an alias of "LastStrongest". Confirmed at the driver configuration level by the L2 run. What the sensor outputs in this mode needs a sensor (L4)
- Impact: A config copied between models silently changes meaning
- Question: Can the docs state what "Dual" maps to per model?
- Linked test cases: TC-RM-001, TC-RM-002 (L2, run 2026-11-22)

### GAP-013: Degenerate FoV settings are not defined in the user docs
- Category: Ambiguity
- Parameters: cloud_min_angle, cloud_max_angle
- Evidence:
  - Docs and schema: common.md L93-L94 allows a FoV that crosses 0 deg. misc.json L17-L30 and wrapper ranges allow each value in 0 to 360 independently. The user docs do not define cloud_min_angle == cloud_max_angle, or cloud_min_angle=360
  - Code: src/nebula_core/nebula_core_decoders/include/nebula_core_decoders/angles.hpp L81-L84 states that equal start and end angles cover the full circle and that a zero-width sector cannot be defined. nebula's unit test uses 90 to 90 as a FoV (test_hesai_decoder_settings.cpp L108-L109)
  - L2 run (TC-FOV-011, 3 of 3 runs): cloud_min_angle=90 with cloud_max_angle=90 is accepted. The node starts and logs "FoV Start: 90" and "FoV End: 90". `ros2 param describe` shows each angle as an integer from 0 to 360, step 1, with no rule between them
  - L3 run (TC-FOV-011 replay, 3 of 3 runs): with 90 to 90, all 4 decoded scans are equal to the scans with 0 to 360 (same stamps, point counts and coordinates)
- Assumption: My earlier assumption (equal angles mean an empty FoV and should be rejected) is contradicted by the code and the L3 run: equal angles mean the full circle. Whether users are meant to rely on this is open, because the user docs do not say it. cloud_min_angle=360 was not run
- Impact: A user who sets equal angles expecting a narrow or empty FoV gets a full scan without a warning
- Question: Should the docs state that equal angles mean 360 deg, or should the driver reject them? Is 360 a valid start angle?
- Linked test cases: TC-FOV-011 (L2, run 2026-11-22; replayed at L3 on 2026-11-23)

### GAP-014: diag_span has no unit
- Category: Missing
- Parameters: diag_span
- Evidence: topic.json L18-L24, description "Diagnostics rate", default 1000, no unit
- Assumption: Milliseconds, based on the default value
- Impact: Users cannot tell how to change the diagnostics period
- Question: What is the unit?
- Linked test cases: none (doc review only)

### GAP-015: Schema defaults are strings for numeric and boolean types
- Category: Inconsistency
- Parameters: many
- Evidence: hesai schema L47 ("600"), L60 ("0"); hardware.json L8 ("true"); diagnostics.json L33 and L38 ("9.0", "11.0") while L16 and L21 are numbers; hesai schema L32 (multicast_ip default is two quote characters as text)
- Assumption: Defaults should have the same type as the parameter
- Impact: Generated docs and any tool that reads defaults get the wrong type
- Question: Can defaults be typed consistently?
- Linked test cases: TC-SCH-030 (L1, automated)

---

## Candidate mapping

| Candidate | Result |
|---|---|
| C-01 | GAP-001, and the rotation_speed part also in GAP-002 |
| C-02 | GAP-004 |
| C-03, C-13 | GAP-009 |
| C-04 | Scope note (generated docs) |
| C-05 | GAP-005 |
| C-06 | GAP-006 |
| C-07 | GAP-007 |
| C-08 | GAP-003 |
| C-09 | GAP-010 (first guess was partly wrong: bounds are used, but not linked to rotation_speed) |
| C-10 | GAP-008 |
| C-11 | GAP-013 |
| C-12 | GAP-015 |
| C-14 | GAP-014 |
| C-15 | GAP-011 |
| C-16 | GAP-012 |
| C-17 | Tooling note below, not counted as a GAP |

## Tooling note (C-17)
- check-jsonschema 0.39.0 cannot load the original schema files: a relative "$ref" inside a file reached through another relative "$ref" is resolved to a wrong path. Removing "$id" does not help. Replacing "$id" with each file's absolute file URI works (probe, "Schema loading comparison")
- The relative "$id" values (lidar_hesai.json L168, core schemas use "nebula_ros_base/...", an old package name) are part of the cause, but the tool's behavior is too
- nebula's own CI uses autoware-github-actions/json-schema-check v1.69.1 (.github/workflows/json-schema-check.yaml). I have not checked how it loads schemas, so this is not reported as a nebula defect
- Lesson: the first probe run counted tool errors as "reject" because both use exit code 1. The BASE case exposed it. The probe now separates pass, reject and error, and checks BASE and a control before trusting any result
