#!/usr/bin/env bash
# Runs one L2 case inside the nebula-dev container. See docs/evidence/l2-run-2026-11-22.md.
# Usage: l2_run_case.sh CASE_ID RUN_NUMBER PARAM_FILE [extra --ros-args items]
# Optional env: DESCRIBE="param1 param2" runs ros2 param describe, TRYSET="name value" tries ros2 param set.
CASE="$1"; RUN="$2"; CFG="$3"; shift 3
OUT="/ws/l2/out2/$CASE/r$RUN"
CAL=/ws/nebula/install/nebula_hesai_decoders/share/nebula_hesai_decoders/calibration/PandarXT32.csv
rm -rf "$OUT" && mkdir -p "$OUT"
source /ws/nebula/install/setup.bash
echo "cfg: $CFG" > "$OUT/args.txt"
echo "extra_args: $*" >> "$OUT/args.txt"
timeout -s INT 25 ros2 run nebula_hesai hesai_ros_wrapper_node --ros-args --params-file "$CFG" -p launch_hw:=false -p calibration_file:="$CAL" "$@" > "$OUT/node.log" 2>&1 &
pid=$!
sleep 6
node=""
tries=0
for i in 1 2 3 4 5 6; do
  tries=$i
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  node=$(ros2 node list --no-daemon 2>/dev/null | grep -x '/hesai_ros_wrapper')
  if [ -n "$node" ]; then break; fi
  sleep 1
done
if kill -0 "$pid" 2>/dev/null; then alive=yes; else alive=no; fi
echo "alive_after_discovery=$alive node=${node:-none} discovery_tries=$tries" > "$OUT/probe.txt"
if [ -n "$node" ]; then
  ros2 param dump "$node" > "$OUT/params.yaml" 2>&1
  for p in $DESCRIBE; do ros2 param describe "$node" "$p" >> "$OUT/describe.txt" 2>&1; done
  if [ -n "$TRYSET" ]; then
    ros2 param set "$node" $TRYSET > "$OUT/tryset.txt" 2>&1
    echo "tryset_exit=$?" >> "$OUT/tryset.txt"
    echo "value after set attempt:" >> "$OUT/tryset.txt"
    ros2 param get "$node" "${TRYSET%% *}" >> "$OUT/tryset.txt" 2>&1
  fi
fi
wait "$pid"
echo $? > "$OUT/exit_code"
echo "case=$CASE run=$RUN alive=$alive node=${node:-none} exit=$(cat "$OUT/exit_code")"
