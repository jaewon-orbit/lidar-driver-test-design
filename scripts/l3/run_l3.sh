#!/usr/bin/env bash
CASE="$1"; RUN="$2"; shift 2
OUT="/ws/l3/out3/$CASE/r$RUN"
CFG=/ws/nebula/install/nebula_hesai/share/nebula_hesai/config/PandarXT32.param.yaml
CAL=/ws/nebula/install/nebula_hesai_decoders/share/nebula_hesai_decoders/calibration/PandarXT32.csv
BAG=/ws/nebula/src/nebula_hesai/nebula_hesai/test_resources/decoder_ground_truth/xt32/1673400677802009732
export FASTDDS_DEFAULT_PROFILES_FILE=/ws/l3diag/fastdds_shm.xml
export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/l3diag/fastdds_shm.xml
rm -rf "$OUT" && mkdir -p "$OUT"
source /ws/nebula/install/setup.bash
echo "extra_args: $*" > "$OUT/args.txt"
timeout -s INT 90 ros2 run nebula_hesai hesai_ros_wrapper_node --ros-args --params-file "$CFG" -p launch_hw:=false -p calibration_file:="$CAL" "$@" > "$OUT/node.log" 2>&1 &
npid=$!
sleep 5
if ! kill -0 "$npid" 2>/dev/null; then
  wait "$npid"; echo $? > "$OUT/node_exit"
  echo "case=$CASE run=$RUN node=exited_at_startup node_exit=$(cat "$OUT/node_exit")"
  exit 0
fi
python3 /ws/l3/sub.py "$OUT" > "$OUT/sub.log" 2>&1 &
spid=$!
ready=no
for i in $(seq 1 30); do
  if [ -f "$OUT/ready" ]; then ready=yes; break; fi
  sleep 0.5
done
subs=0
for i in $(seq 1 20); do
  subs=$(ros2 topic info /pandar_points 2>/dev/null | awk '/Subscription count/ {print $3}')
  if [ "${subs:-0}" -ge 1 ]; then break; fi
  sleep 0.5
done
echo "sub_ready=$ready graph_subscription_count=$subs" > "$OUT/ready_check.txt"
if [ "$ready" = yes ] && [ "${subs:-0}" -ge 1 ]; then
  sleep 2
  timeout 40 ros2 bag play --delay 3 "$BAG" > "$OUT/play.log" 2>&1
  echo $? > "$OUT/play_exit"
  sleep 3
else
  echo "subscriber not ready" > "$OUT/play.log"
  echo skipped > "$OUT/play_exit"
fi
kill -INT "$spid" 2>/dev/null; wait "$spid"
kill -INT "$npid" 2>/dev/null; wait "$npid"; echo $? > "$OUT/node_exit"
python3 /ws/l3/convert.py "$OUT" > "$OUT/convert.log" 2>&1
n=$(ls "$OUT"/cloud_*.npz 2>/dev/null | wc -l)
echo "case=$CASE run=$RUN node=ran $(cat "$OUT/ready_check.txt") play_exit=$(cat "$OUT/play_exit") clouds=$n node_exit=$(cat "$OUT/node_exit")"
