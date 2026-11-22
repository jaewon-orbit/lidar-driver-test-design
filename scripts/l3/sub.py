import os
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2

OUT = sys.argv[1]


class CloudSaver(Node):
    def __init__(self):
        super().__init__("l3_cloud_saver")
        self.count = 0
        self.ready = False
        self.create_subscription(PointCloud2, "/pandar_points", self.on_cloud, qos_profile_sensor_data, raw=True)
        self.create_timer(0.2, self.check_ready)

    def check_ready(self):
        if not self.ready and self.count_publishers("/pandar_points") > 0:
            with open(os.path.join(OUT, "ready"), "w") as f:
                f.write("1")
            self.ready = True

    def on_cloud(self, data):
        with open(os.path.join(OUT, f"cloud_{self.count:02d}.cdr"), "wb") as f:
            f.write(data)
        self.count += 1
        print(f"cloud {self.count} bytes={len(data)}", flush=True)


rclpy.init()
node = CloudSaver()
try:
    rclpy.spin(node)
except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
    pass
