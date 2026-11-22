import glob
import os
import sys

import numpy as np
import sensor_msgs_py.point_cloud2 as pc2
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2

d = sys.argv[1]
for i, f in enumerate(sorted(glob.glob(os.path.join(d, "cloud_*.cdr")))):
    msg = deserialize_message(open(f, "rb").read(), PointCloud2)
    data = pc2.read_points(msg, skip_nans=False)
    stamp = msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec
    np.savez(f[:-4] + ".npz", data=data, stamp=stamp)
    if i == 0:
        with open(os.path.join(d, "fields.txt"), "w") as fo:
            fo.write(" ".join(fl.name for fl in msg.fields))
