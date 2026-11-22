import glob
import hashlib
import os
import sys

import numpy as np

d, fmin, fmax = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
gt = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
lines = []


def out(s):
    lines.append(s)
    print(s)


def circ(x):
    x = np.abs(x) % 360
    return np.minimum(x, 360 - x)


def inside(az):
    if fmin == fmax:
        return None
    if fmax < fmin:
        return (az >= fmin) | (az <= fmax)
    return (az >= fmin) & (az <= fmax)


files = sorted(glob.glob(os.path.join(d, "cloud_*.npz")))
fpath = os.path.join(d, "fields.txt")
out(f"fields: {open(fpath).read().strip() if os.path.exists(fpath) else '-'}")
out(f"clouds={len(files)}")

gt_xyz = None
if gt:
    raw = open(gt, "rb").read()
    i = raw.index(b"DATA binary\n") + len(b"DATA binary\n")
    gt_xyz = np.frombuffer(raw[i:], dtype=np.float32).reshape(-1, 3)
    out(f"reference_points={len(gt_xyz)}")

all_az = []
total_out = 0
max_out = 0.0
gt_match = "no"
for k, f in enumerate(files):
    z = np.load(f)
    a = z["data"]
    stamp = int(z["stamp"])
    s = f"cloud {k}: points={len(a)} stamp={stamp}"
    if len(a):
        x = a["x"].astype(np.float64)
        y = a["y"].astype(np.float64)
        az = np.degrees(np.arctan2(x, y)) % 360
        all_az.append(az)
        s += f" az_min={az.min():.3f} az_max={az.max():.3f}"
        ins = inside(az)
        if ins is not None:
            o = ~ins
            n_out = int(o.sum())
            total_out += n_out
            s += f" outside_fov={n_out}"
            if n_out:
                dist = np.minimum(circ(az[o] - fmin), circ(az[o] - fmax))
                max_out = max(max_out, float(dist.max()))
                s += f" max_outside_deg={dist.max():.4f}"
        if "azimuth" in a.dtype.names:
            af = a["azimuth"].astype(np.float64)
            afd = (np.degrees(af) if af.max() <= 2 * np.pi + 1e-3 else af) % 360
            m = (x * x + y * y) > 0.01
            if m.any():
                s += f" azimuth_field_vs_xy_max_deg={circ(afd[m] - az[m]).max():.4f}"
        if gt_xyz is not None and len(a) == len(gt_xyz):
            p = np.stack([a["x"], a["y"], a["z"]], axis=1).astype(np.float32)
            d1 = float(np.abs(p - gt_xyz).max())
            ip = np.lexsort((p[:, 2], p[:, 1], p[:, 0]))
            ig = np.lexsort((gt_xyz[:, 2], gt_xyz[:, 1], gt_xyz[:, 0]))
            d2 = float(np.abs(p[ip] - gt_xyz[ig]).max())
            s += f" reference_elementwise_max_diff_m={d1:.6f} reference_sorted_max_diff_m={d2:.6f}"
            if min(d1, d2) < 1e-3:
                gt_match = "yes"
    out(s)

if all_az:
    A = np.concatenate(all_az)
    occupied = set(np.floor(A).astype(int) % 360)
    if fmin == fmax:
        out(f"all_clouds: points={len(A)} occupied_1deg_bins={len(occupied)} of 360")
    else:
        fov_bins = [b for b in range(360) if inside(np.array([b + 0.5]))[0]]
        empty = [b for b in fov_bins if b not in occupied]
        outside_bins = sorted(int(b) for b in occupied if b not in fov_bins)
        out(f"all_clouds: points={len(A)} outside_fov={total_out} max_outside_deg={max_out:.4f}")
        out(f"all_clouds: empty_1deg_bins_in_fov={len(empty)} of {len(fov_bins)} occupied_bins_outside_fov={outside_bins[:20]}")
if gt:
    out(f"reference_match={gt_match}")
print("sig=" + hashlib.md5("\n".join(lines).encode()).hexdigest()[:12])
