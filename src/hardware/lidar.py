from rplidar import RPLidar

lidar = RPLidar('COM11')

try:
    for scan in lidar.iter_scans():
        close_points = [(angle, dist) for _, angle, dist in scan if dist < 200]
        if close_points:
            print(f"ALERTE ! {len(close_points)} points à moins de 20cm")
            for angle, dist in close_points:
                print(f"  → {dist/10:.1f}cm à {angle:.0f}°")
finally:
    lidar.stop()
    lidar.disconnect()