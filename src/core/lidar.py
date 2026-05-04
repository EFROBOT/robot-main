try:
    from rplidar import RPLidar
except ImportError as exc:
    RPLidar = None
    _RPLIDAR_IMPORT_ERROR = exc


class Lidar:
    def __init__(self, port="/dev/ttyACM1", logs=None):
        if RPLidar is None:
            raise RuntimeError(f"Impossible d'importer rplidar: {_RPLIDAR_IMPORT_ERROR}")
        self.logs = logs
        self.lidar = RPLidar(port)
        if self.logs:
            self.logs.log("RPi", f"Lidar connecté sur {port}")

    def scan(self, distance_cm=20):
        distance_mm = distance_cm * 10
        obstacles = []

        for scan in self.lidar.iter_scans():
            for _, angle, dist in scan:
                if 0 < dist < distance_mm:
                    obstacles.append({
                        "angle": round(angle, 1),
                        "distance_cm": round(dist / 10, 1),
                    })
            if obstacles:
                return obstacles

        return obstacles

    def stop(self):
        if not hasattr(self, "lidar") or self.lidar is None:
            return
        try:
            self.lidar.stop()
            self.lidar.disconnect()
        finally:
            self.lidar = None
            if self.logs:
                self.logs.log("RPi", "Lidar déconnecté")
