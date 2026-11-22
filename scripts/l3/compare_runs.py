import glob
import hashlib
import os
import sys

import numpy as np

case_dir = sys.argv[1]
per_run = {}
for run in sorted(glob.glob(os.path.join(case_dir, "r*"))):
    clouds = {}
    for f in sorted(glob.glob(os.path.join(run, "cloud_*.npz"))):
        z = np.load(f)
        a = z["data"]
        xyz = np.stack([a["x"], a["y"], a["z"]], axis=1).astype(np.float32).tobytes()
        clouds[int(z["stamp"])] = (len(a), hashlib.md5(xyz).hexdigest()[:12])
    per_run[os.path.basename(run)] = clouds
stamps = sorted({s for c in per_run.values() for s in c})
for run, clouds in per_run.items():
    print(f"{run}: clouds={len(clouds)} stamps={sorted(clouds)}")
conflicts = 0
for s in stamps:
    seen = {c[s] for c in per_run.values() if s in c}
    runs_with = [r for r, c in per_run.items() if s in c]
    print(f"stamp {s}: in {len(runs_with)} of {len(per_run)} runs, distinct_contents={len(seen)} {sorted(seen)}")
    if len(seen) > 1:
        conflicts += 1
same_set = len({tuple(sorted(c)) for c in per_run.values()}) == 1
print(f"same_cloud_set_in_all_runs={'yes' if same_set else 'no'}")
print(f"content_conflicts_for_same_stamp={conflicts}")
