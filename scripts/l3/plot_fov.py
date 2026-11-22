import glob
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Wedge

out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)

panels = [
    ("/ws/l3/out3/TC-FOV-001/r1", 0, 360, "TC-FOV-001: FoV 0 to 360 (default)"),
    ("/ws/l3/out3/TC-FOV-002/r1", 90, 315, "TC-FOV-002: FoV 90 to 315, cut_angle 315"),
    ("/ws/l3/out3/TC-FOV-003/r1", 270, 90, "TC-FOV-003: FoV 270 to 90 (crosses 0 deg)"),
    ("/ws/l3/out4/TC-FOV-011-replay/r1", 90, 90, "TC-FOV-011: FoV 90 to 90 (equal angles)"),
]


def last_cloud(d):
    files = sorted(glob.glob(os.path.join(d, "cloud_*.npz")))
    if not files:
        return None, None
    z = np.load(files[-1])
    return z["data"], int(z["stamp"])


ref, ref_stamp = last_cloud(panels[0][0])
ref_r = np.hypot(ref["x"], ref["y"])
R = float(np.percentile(ref_r, 98))
print(f"plot radius (98th percentile of xy distance) = {R:.1f} m")

fig, axes = plt.subplots(2, 2, figsize=(12, 12))
for ax, (d, fmin, fmax, title) in zip(axes.flat, panels):
    a, stamp = last_cloud(d)
    ax.scatter(ref["x"], ref["y"], s=0.3, c="0.80", linewidths=0, label="default output (0 to 360)", zorder=1)
    if a is not None:
        ax.scatter(a["x"], a["y"], s=0.3, c="tab:blue", linewidths=0, label="output with this FoV", zorder=2)
        n = len(a)
    else:
        n = 0
    if fmin != fmax and not (fmin == 0 and fmax == 360):
        ax.add_patch(Wedge((0, 0), R, 90 - fmax, 90 - fmin, color="tab:orange", alpha=0.10, zorder=0))
        for ang in (fmin, fmax):
            t = np.radians(ang)
            ax.plot([0, R * np.sin(t)], [0, R * np.cos(t)], color="tab:orange", lw=1.2, zorder=3)
            ax.text(0.85 * R * np.sin(t), 0.85 * R * np.cos(t), f"{ang} deg", color="tab:orange",
                    ha="center", va="bottom", fontsize=10, zorder=4,
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1))
    ax.plot(0, 0, marker="+", color="k")
    ax.set_xlim(-R, R)
    ax.set_ylim(-R, R)
    ax.set_aspect("equal")
    ax.set_title(f"{title}\n{n} points, scan stamp {stamp}", fontsize=10)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.grid(True, lw=0.3)
axes.flat[0].legend(loc="lower left", markerscale=20, fontsize=8)
fig.suptitle("Pandar XT32 replay, top view. Azimuth 0 deg is +y and increases toward +x.\n"
             "Data: nebula test_resources/decoder_ground_truth/xt32 (tier4/nebula 4e02244, Apache-2.0)",
             fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.95))
p1 = os.path.join(out_dir, "fov_top_view.png")
fig.savefig(p1, dpi=130)
print(f"wrote {p1}")

fig = plt.figure(figsize=(9, 7))
ax = fig.add_subplot(projection="3d")
m = ref_r <= R
sel = np.where(m)[0][::3]
sc = ax.scatter(ref["x"][sel], ref["y"][sel], ref["z"][sel], s=0.4, c=ref["z"][sel], cmap="viridis", linewidths=0)
ax.set_xlim(-R, R)
ax.set_ylim(-R, R)
ax.set_zlim(-R / 4, R / 4)
ax.set_box_aspect((1, 1, 0.25))
ax.view_init(elev=28, azim=-60)
ax.set_xlabel("x [m]")
ax.set_ylabel("y [m]")
ax.set_zlabel("z [m]")
fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.12, label="z [m]")
ax.set_title(f"Pandar XT32 replay, default config, one scan ({len(ref)} points, every 3rd shown)\n"
             "Data: nebula test_resources/decoder_ground_truth/xt32 (tier4/nebula 4e02244, Apache-2.0)",
             fontsize=9)
p2 = os.path.join(out_dir, "control_scan_3d.png")
fig.savefig(p2, dpi=130, bbox_inches="tight")
print(f"wrote {p2}")
