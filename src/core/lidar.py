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
        self._measure_iter = None
        if self.logs:
            self.logs.log("RPi", f"Lidar connecte sur {port}")

    def _ensure_measure_iter(self):
        if self._measure_iter is None:
            self._measure_iter = self.lidar.iter_measures(scan_type="normal", max_buf_meas=3000)

    def _reset_measure_iter(self):
        self._measure_iter = None
        try:
            self.lidar.stop()
        except Exception:
            pass
        try:
            self.lidar.clean_input()
        except Exception:
            pass

    def scan(self, distance_cm=45, min_distance_cm=3, max_measures=1600):
        """Collect one scan cycle from lidar measures.

        This implementation uses iter_measures directly to avoid intermittent
        unpack errors observed with some iter_scans flows.
        """
        distance_mm = distance_cm * 10
        min_distance_mm = min_distance_cm * 10
        obstacles = []
        started_scan = False

        try:
            self._ensure_measure_iter()
            idx = 0
            while idx < max_measures:
                idx += 1
                measure = next(self._measure_iter)
                try:
                    if not isinstance(measure, (list, tuple)):
                        continue

                    if len(measure) >= 4:
                        new_scan = bool(measure[0])
                        angle = float(measure[-2])
                        dist = float(measure[-1])
                    elif len(measure) >= 3:
                        # Fallback shape without explicit new_scan flag
                        new_scan = False
                        angle = float(measure[-2])
                        dist = float(measure[-1])
                    else:
                        continue
                except (TypeError, ValueError, IndexError):
                    continue

                """
                if dist:
                    self.logs.log("ERR", f"dist: {dist}")
                """
                if new_scan and started_scan:
                    # End of one full rotation
                    self.logs.log("ERR", f"obstacles {obstacles}")
                    return obstacles

                if new_scan:
                    started_scan = True

                if not started_scan or dist <= 0:
                    if idx >= max_measures:
                        self.logs.log("ERR", f"obstacles max {obstacles}")
                        return obstacles
                    continue

                #self.logs.log("ERR", f"distance: {dist}")
                if min_distance_mm <= dist < distance_mm:
                    obstacles.append({
                        "angle": round(angle, 1),
                        "distance_cm": round(dist / 10, 1),
                    })
            self.logs.log("ERR", f"obstacles end {obstacles}")
            return obstacles
        except Exception as exc:
            if self.logs:
                self.logs.log("ERR", f"Lidar scan exception: {type(exc).__name__}: {exc}; reset flux")
            self._reset_measure_iter()
            return []

    def stop(self):
        if not hasattr(self, "lidar") or self.lidar is None:
            return
        try:
            self._measure_iter = None
            self.lidar.stop()
            self.lidar.disconnect()
        finally:
            self.lidar = None
            if self.logs:
                self.logs.log("RPi", "Lidar déconnecte")
