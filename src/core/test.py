from rplidar import RPLidar
import time

lidar = RPLidar("/dev/ttyUSB0")
print(lidar.get_info())
print(lidar.get_health())
time.sleep(2)
for i, scan in enumerate(lidar.iter_scans()):
    print(f"scan {i}: {len(scan)} pts")
    if i >= 5:
        break
lidar.stop()
lidar.stop_motor()
lidar.disconnect()