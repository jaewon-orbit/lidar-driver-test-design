# 00. Analysis Scope

## Target
- Driver: tier4/nebula
- Sensor model: Hesai Pandar XT32 (support status ✅ in docs/supported_sensors.md, line 17)
- Pinned commit: 4e02244695879e823f570f13449d95cb642cd35a (2026-11-20)
- Analysis start date: 2026-11-22

## Sources
| # | Source | Path (at pinned commit) |
|---|---|---|
| A | Parameter docs | docs/parameters/vendors/hesai/common.md, xt32.md |
| B | JSON schema | src/nebula_hesai/nebula_hesai/schema/PandarXT32.schema.json (including $ref targets) |
| C | Default YAML | src/nebula_hesai/nebula_hesai/config/PandarXT32.param.yaml |
| D | Config struct in code | HesaiSensorConfiguration (path to be recorded during source collection) |
| E | Vendor manual | Hesai Pandar XT32 user manual (public availability to be checked) |

## In scope
- Cross-checking XT32 ROS 2 parameters across sources A to E
- Parameter types, defaults, allowed ranges, and combination rules
- Automating checks that can be verified with files only (L1)

## Out of scope
- Other models such as XT32M (support status ⚠️, not a stable baseline)
- Accuracy of decoder point calculations
- Real sensor connection and network performance

## Principles
- Web docs track the latest main branch and may change, so the repository docs/ at the pinned commit is the baseline
- Confirmed facts and my own assumptions are always marked separately
- xt32.md and the top of common.md are generated from the schemas. Only hand-written statements in common.md are recorded in the doc_* columns of the inventory
- Code struct: src/nebula_hesai/nebula_hesai_common/include/nebula_hesai_common/hesai_common.hpp L178-L201 (inherits LidarConfigurationBase, nebula_common.hpp L328)
