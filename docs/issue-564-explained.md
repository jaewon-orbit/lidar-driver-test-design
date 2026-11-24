# PTP Transport Type Mismatch in tier4/nebula (Issue #564)

## Summary

When the Hesai LiDAR driver in [tier4/nebula](https://github.com/tier4/nebula) receives an invalid PTP setting (`802.1as` with `UDP`), it quietly switches to the correct setting (`L2`) but keeps reporting the old value (`UDP`). The driver works correctly, but anyone who reads the parameter sees a value that is not in use. I found this by cross-checking the documentation against the code, confirmed it by running the driver, and reported it as [tier4/nebula#564](https://github.com/tier4/nebula/issues/564).

This write-up is part of my QA side project [lidar-driver-test-design](https://github.com/jaewon-orbit/lidar-driver-test-design), where it is tracked as GAP-007 and test case TC-RUN-002. All file paths and line numbers refer to nebula commit `4e02244`.

## The analogy, mapped

The README explains this issue with a McDonald's order. Each part of that story stands for something real in nebula.

| In the analogy | In nebula |
| --- | --- |
| The menu | Parameter docs, `common.md` line 19 |
| The kiosk | JSON schema check (file validation) |
| The kitchen | The driver, `hesai_ros_wrapper.cpp` |
| The receipt | The parameter value, read with `ros2 param get` |
| Ordering a McFlurry instead of fries | Setting `ptp_profile: 802.1as` with `ptp_transport_type: UDP` |
| The kiosk accepts the order | The schema check passes |
| The kitchen packs fries instead | The driver logs a warning and switches to L2 internally |
| The receipt still says McFlurry | The parameter still reads `UDP` |
| Option A, block the order | The schema rejects the combination |
| Option B, swap it and fix the receipt | Keep the auto-correction, describe it in the docs, and make the parameter read `L2` |

The sections below explain each part in technical terms.

## Background: the rule in the docs

The nebula parameter docs (`docs/parameters/vendors/hesai/common.md`, line 19) state:

> "For 802.1as and automotive, only L2 is allowed"

Three terms make this sentence readable.

**PTP (Precision Time Protocol)** keeps the clocks of networked devices in sync, down to microseconds. A self-driving car has a LiDAR, cameras, radar and GNSS, and each stamps its data with a time. If the camera clock runs 0.05 s ahead, a pedestrian seen at "10.000 s" by both sensors may really be two moments apart. At 60 km/h that is about 80 cm, enough to place the same person in two spots. PTP prevents this by having every device follow one master clock, much like a class setting their watches to the school bell.

**PTP profiles** are rulebooks for specific fields, built on top of PTP. Think of football: FIFA rules, futsal rules and local league rules share a game but differ in details. The Hesai driver supports three profiles.

| Profile | In plain words |
| --- | --- |
| `1588v2` | Default PTP, general purpose |
| `802.1as` | For fields with strict timing, such as audio, video and in-vehicle networks (also called gPTP) |
| `automotive` | A version of 802.1as tuned for cars |

**Transport type** (`ptp_transport_type`) is how the timing messages travel between devices.

| Transport | Analogy | What it means |
| --- | --- | --- |
| `UDP` | A letter sent through the post office, with an address | Messages carry an IP address and can pass through routers |
| `L2` | A note handed directly to the person at the next desk | Messages go straight over Ethernet with no IP layer. They stay on the local network, with simpler and more predictable delay |

So the rule means: if you use the 802.1as or automotive rulebook, timing messages must be handed over directly (L2). The 802.1as standard itself defines only this transport, because routing through IP adds delay that varies.

## The problem

The docs and the driver disagree on what happens when a user sets `ptp_profile: 802.1as` with `ptp_transport_type: UDP`, and the parameter ends up showing a value the driver does not use.

| Where | What it says or does |
| --- | --- |
| Docs | This combination is not allowed |
| Driver behavior | Logs a warning, switches to L2 internally, and keeps running |
| Parameter value read afterwards | Still `UDP` |

In the analogy, this is the receipt that says "McFlurry" while the bag holds fries.

The cause sits in `hesai_ros_wrapper.cpp`. Line 240 declares the parameter as read-only. Line 251 switches the internal config to L2. Line 252 tries to update the parameter to L2 as well, but because the parameter is read-only this update fails, and the code does not check the result.

## How it was found and confirmed

I checked the same rule in each place it lives, from files only up to a running driver.

1. **Docs.** Line 19 of `common.md` states the restriction.
2. **JSON schema.** The Hesai schema (lines 65 to 70) has no rule for this combination, although the same file uses `if/then` rules elsewhere (lines 150 to 163). A schema check with `802.1as` and `UDP` passes (candidate C-07).
3. **Code.** `hesai_ros_wrapper.cpp` lines 240 to 253 show auto-correction instead of rejection, and an unchecked update of a read-only parameter.
4. **Driver run without a sensor (TC-RUN-002).** I ran the driver node in a ROS 2 Jazzy container with `launch_hw:=false`, using the invalid combination. I repeated the run 3 times with identical results.

| Check | Result |
| --- | --- |
| Warning log | "PTP transport was set to 'UDP' but PTP profile '802.1as' only supports 'L2'. Setting it to 'L2'." |
| Logged configuration | `PTP Transport Type: L2` |
| `ros2 param get ptp_transport_type` | `UDP` |
| `ros2 param describe ptp_transport_type` | `Read only: true` |
| External `ros2 param set ptp_transport_type L2` | Refused: "cannot be set because it is read-only" |
| Control: the same command on `min_range` (read-write) | Changed to 0.1 as expected |

The control case matters. It shows that the refusal comes from this parameter being read-only, not from a broken setup.

**What a parameter read is:** a ROS 2 node holds its settings as parameters, which people and tools can read from outside, for example with `ros2 param get`. It is like opening a phone's settings screen to check whether Wi-Fi is on.

## Why it matters

The driver itself runs correctly on L2, so this is not an immediate safety problem. The risk is for people and tools that trust the parameter value.

| Situation | What can go wrong |
| --- | --- |
| Debugging a time sync failure | An engineer reads `UDP` and checks UDP routing and firewall rules, while the traffic is actually L2. Time is lost looking in the wrong place |
| Saving the configuration | `ros2 param dump` records `UDP`. Anyone reproducing an issue from that record works from the wrong setting |
| Automated checks | A script that asserts the transport is L2 fails even though L2 is in use (a false failure) |
| Other nodes reading the value | A monitoring node that configures itself from this parameter watches with the wrong setting |

Today the value actually in use appears only in the warning line and the startup configuration log. Without reading the logs, there is no way to know.

## What I asked the maintainers

I did not prescribe a fix. The design choice belongs to the maintainers, so I asked which behavior is intended.

1. **Align the docs and schema with the behavior.** Either make the schema reject `802.1as` or `automotive` with `UDP`, so the error shows up during file validation, or keep the auto-correction and describe it in the docs. In the analogy: the kiosk blocks the order (option A), or the menu explains the swap (part of option B).
2. **Make the parameter show the value in use.** Make the update at line 252 succeed and check its result, so that `ros2 param get` returns `L2`. In the analogy: if the kitchen packs fries, the receipt says fries (the rest of option B).

My own view is that rejecting the combination is cleaner, since failing early is usually preferred in safety-related software. Auto-correction may still be intentional, for example to keep older config files working, and both can coexist: reject in the schema, and correct with a warning at runtime.

## What the report included and what was not tested

- Exact commit (`4e02244`), reproduction steps, expected and actual output, and a code permalink
- Tested with the `802.1as` profile only. The `automotive` profile goes through the same code but was not run
- Run without a physical sensor (`launch_hw:=false`), so no real PTP traffic was observed
- That the update at line 252 fails for the read-only reason is inferred from the external set result, not traced inside rclcpp
