from rplidar import RPLidar

class Lidar:
    def __init__(self, port='/dev/ttyACM1 '):
        self.lidar = RPLidar(port)
        print(f"Lidar connecté sur {port}")

    def scan(self, distance_cm=20):
        """
        Scanne et retourne les obstacles détectés sous la distance donnée.
        
        Entrée : distance_cm (float) — seuil de détection en cm
        Sortie : liste de dicts [{"angle": float, "distance_cm": float}, ...]
        """
        distance_mm = distance_cm * 10
        obstacles = []

        for scan in self.lidar.iter_scans():
            for _, angle, dist in scan:
                if 0 < dist < distance_mm:
                    obstacles.append({
                        "angle": round(angle, 1),
                        "distance_cm": round(dist / 10, 1)
                    })
            if obstacles:
                return obstacles

    def stop(self):
        self.lidar.stop()
        self.lidar.disconnect()
        print("Lidar déconnecté.")
