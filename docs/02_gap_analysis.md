# 02. Gap Analysis

## Candidates (unverified)
These are hypotheses found while reading sources. Each will be verified before being promoted to a GAP entry.

| ID | Summary | Source | How to verify |
|---|---|---|---|
| C-01 | Keywords next to $ref may be ignored under draft-07 (sensor_model enum, return_mode enum, diagnostics required) | PandarXT32.schema.json L63-L66, L76-L87, L112-L115 | L1 test: set sensor_model=PandarAT128 and check if schema validation passes |
| C-02 | "additionalProperties": false is placed inside "properties" of "/**", so it may act as a property name instead of a rule | PandarXT32.schema.json L161 | L1 test: add an unknown key under "/**" and check if validation passes |
| C-03 | min_range and max_range are not required, while most other parameters are | PandarXT32.schema.json L120-L150 | Check code defaults and docs for behavior when omitted |
| C-04 | xt32.md is generated from the schema, so A and B cannot disagree for model docs; real cross-checks are common.md vs schema vs code | docs/parameters/vendors/hesai/xt32.md | Note in scope |
