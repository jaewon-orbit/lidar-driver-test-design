# Vendor Manual Check (Source E)

> Date: 2026-11-23
> Purpose: settle GAP-002 (supported rotation speeds) and check return modes against the vendor manual.

## 1. Document

| Item | Value |
|---|---|
| Title | PandarXT 32-Channel Mid-Range Mechanical Lidar User Manual |
| Doc version | X01-en-260710 |
| Classification | C0 (Public) |
| Obtained from | Hesai official download page (hesaitech.com, Downloads, XT32/16) |
| Size | 109 PDF pages |
| SHA256 | 62ca663c771ce562a6e262367bb1bd59a04964b94c09fe335ec1a6bbe9726ba9 |
| Stored in this repository | No. It is a Hesai document. This file records version, hash and page references only |

Page numbers below are the printed page numbers (PDF page minus 4).

## 2. Rotation speed

| Statement in the manual | Section | Page |
|---|---|---|
| Frame rate: 5 Hz, 10 Hz, 20 Hz | 1.5 Specifications | 15 |
| Horizontal resolution: 0.09° (5 Hz), 0.18° (10 Hz), 0.36° (20 Hz) | 1.5 Specifications | 15 |
| Motor Speed field, unit RPM: spin rate (RPM) = frame rate (Hz) × 60 | 3.1.2.4 Tail | 53 |
| Spin Rate options: 300, 600 RPM (default), 1200 RPM | 4.2.2 Function | 70 |

Result: the manual lists 300, 600 and 1200 RPM only. 900 RPM is not listed anywhere.

| Source | 900 RPM |
|---|---|
| B Schema (300 to 1200, multipleOf 60) | Accepted |
| D Runtime range (step 300) | Accepted (observed at L2, TC-RUN-001) |
| D Runtime description ("300, 600, 1200") | Not listed |
| E Vendor manual | Not listed |

Not covered by the manual: what the sensor does if it is asked to spin at 900 RPM. That needs a real sensor (L4) and stays open.

## 3. Return mode

| Statement in the manual | Section | Page |
|---|---|---|
| Single Return: Last, Strongest, First | 1.5 Specifications, 4.2.2 Function | 15, 70 |
| Dual Return: Last and Strongest (default), Last and First, First and Strongest | 1.5 Specifications, 4.2.2 Function | 15, 70 |
| Return Mode byte in the packet tail: 0x33 First, 0x37 Strongest, 0x38 Last, 0x39 Last and Strongest, 0x3B Last and First, 0x3C First and Strongest | 3.1.2.4 Tail | 53 |

Comparison with the schema enum (Last, Strongest, LastStrongest, First, LastFirst, FirstStrongest, Dual):
- The six modes in the manual each have a matching schema value
- `Dual` (the default in PandarXT32.param.yaml) has no mode of that name in the manual. Which sensor mode it maps to was not checked in the code. Recorded as an open point, not as a GAP

## 4. Changes made from this check
- GAP-002: assumption confirmed by the manual. Question updated
- docs/00_scope.md: source E filled in
- docs/01_parameter_inventory.csv: notes for rotation_speed and return_mode
- docs/04_test_cases.csv: TC-SCH-018 expected result cites the manual. The expectation that the schema should reject 900 is still an assumption
