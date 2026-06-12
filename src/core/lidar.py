try:
    from rplidar import RPLidar
except ImportError as exc:
    RPLidar = None
    _RPLIDAR_IMPORT_ERROR = exc


class Lidar:
    def __init__(self, port="/dev/ttyUSB0", logs=None):
        if RPLidar is None:
            raise RuntimeError(f"Impossible d'importer rplidar: {_RPLIDAR_IMPORT_ERROR}")
        self.logs = logs
        self.port = port
        self.lidar = RPLidar(port)
        self._iter_mesures = None
        if self.logs:
            self.logs.log("RPi", f"Lidar connecte sur {port}")

    def _assurer_iter_mesures(self):
        if self._iter_mesures is None:
            self._iter_mesures = self.lidar.iter_measures(scan_type="normal", max_buf_meas=100000)

    def _reinitialiser_iter_mesures(self):
        self._iter_mesures = None
        try:
            self.lidar.stop()
        except Exception:
            pass
        try:
            self.lidar.clean_input()
        except Exception:
            pass

    def scan(self, distance_cm=10, min_distance_cm=1, max_measures=1600):
        """Collect one scan cycle from lidar measures.

        This implementation uses iter_measures directly to avoid intermittent
        unpack errors observed with some iter_scans flows.
        """
        distance_mm = distance_cm * 10
        min_distance_mm = min_distance_cm * 10
        obstacles = []
        scan_demarre = False

        try:
            self._assurer_iter_mesures()
            if self._iter_mesures is None:
                return []
            index = 0
            while index < max_measures:
                index += 1
                mesure = next(self._iter_mesures)
                try:
                    if not isinstance(mesure, (list, tuple)):
                        continue

                    if len(mesure) >= 4:
                        nouveau_scan = bool(mesure[0])
                        angle = float(mesure[-2])
                        dist = float(mesure[-1])
                    elif len(mesure) >= 3:
                        nouveau_scan = False
                        angle = float(mesure[-2])
                        dist = float(mesure[-1])
                    else:
                        continue
                except (TypeError, ValueError, IndexError):
                    continue


                if nouveau_scan:
                    if scan_demarre and obstacles:
                        return obstacles
                    scan_demarre = True

                if not scan_demarre or dist <= 0:
                    if index >= max_measures:
                        return obstacles
                    continue

                #self.logs.log("ERR", f"distance: {dist}")
                if min_distance_mm <= dist < distance_mm:
                    obstacles.append({
                        "angle": round(angle, 1),
                        "distance_cm": round(dist / 10, 1),
                    })
            return obstacles
        except Exception as exc:
            if self.logs:
                self.logs.log("ERR", f"Lidar scan exception: {type(exc).__name__}: {exc}; reset flux")
            self._reinitialiser_iter_mesures()
            return []

    def stop(self):
        if not hasattr(self, "lidar") or self.lidar is None:
            return
        try:
            self._iter_mesures = None
            self.lidar.stop()
            self.lidar.disconnect()
        finally:
            self.lidar = None
            if self.logs:
                self.logs.log("RPi", "Lidar déconnecte")
