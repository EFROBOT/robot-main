import math
import time
import threading
import cv2

from core.logs import Logs
from core.mecanum import Mecanum
from core.camera import Camera
from core.lidar import Lidar
from world.map import Map


class Robot(Mecanum):
    def __init__(
        self,
        port=None,
        port_lidar=None,
        baudrate=115200,
        camera_id=0,
        x_init=0.0,
        y_init=0.0,
        angle_init_deg=0.0,
        team="yellow",
        
    ):
        self.logs = Logs(maxlen=400)
        super().__init__(
            logs=self.logs,
            port=port,
            baudrate=baudrate,
            x_init=x_init,
            y_init=y_init,
            angle_init_deg=angle_init_deg,
        )

        self.camera = Camera(camera_id=camera_id, logs=self.logs)
        self.lidar = None
        if port_lidar:
            try:
                self.lidar = Lidar(port=port_lidar, logs=self.logs)
            except Exception as exc:
                self.logs.log("ERR", str(exc))
        self.surveiller_lidar()

        self.map = Map(team=team)
        self.inventaire = []

        self.running = False
        self.last_align_time = 0.0
        self.align_interval_ms = 50

    def setup(self):
        if not self.camera.load_calibration():
            self.logs.log("INFO", "Aucune calibration trouvée, paramètres par défaut.")
            self.camera.use_default_calibration()

        if not self.camera.open():
            raise RuntimeError(f"Impossible d'ouvrir la caméra {self.camera.camera_id}")

    def run(self):
        self.running = True
        try:
            while self.running:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    self.logs.log("ERR", "Erreur de lecture caméra.")
                    break

                markers = self.camera.aruco.detect_markers(frame)
                self.camera.aruco.draw_marker(frame, markers)

                if markers:
                    self.align_to_marker(markers[0])
                else:
                    self.move(0, 0, 0)

                cv2.imshow("Robot", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.running = False
        finally:
            self.stop()

    def stop(self):
        self.running = False
        super().stop()
        self.camera.release()
        cv2.destroyAllWindows()

    def align_to_marker(self, marker):
        now = time.time() * 1000
        if now - self.last_align_time >= self.align_interval_ms:
            self.last_align_time = now

    def set_team(self, team):
        self.map = Map(team=team)

        half_x = 32 / 2
        half_y = 28 / 2
        if team == "yellow":
            self.x = 0 + half_x
            self.y = 2000 - half_y
            self.angle_deg = 0
        else:
            self.x = 3000 - half_x
            self.y = 2000 - half_y
            self.angle_deg = 180

    def get_state(self):
        return {
            "robot": {
                "x": self.x,
                "y": self.y,
                "angle_deg": self.angle_deg,
                "angle_rad": math.radians(self.angle_deg),
                "nb_caisses": len(self.inventaire),
                "width": 32,
                "height": 28,
            },
            "nids": [self.map._z2d(z) for z in self.map.nids.values()],
            "garde_mangers": [self.map._z2d(z) for z in self.map.garde_mangers.values()],
            "exclusion": [self.map._z2d(z) for z in self.map.exclusion.values()],
            "ramassage": [self.map._z2d(z) for z in self.map.ramassage.values()],
            "caisses": [self.map._z2d(z) for z in self.map.caisses.values()],
            "strategie_en_cours": False,
        }

    def get_logs(self):
        return self.logs.get_lines()
            
    def surveiller_lidar(self):
            if not self.lidar:
                return
            def boucle():
                ignorer_jusqu_a = 0
                while self.lidar:
                    try:
                        for scan in self.lidar.lidar.iter_scans():
                            if not self.lidar:
                                break
                            if time.time() < ignorer_jusqu_a:
                                continue
                            obstacles = [(a, d) for _, a, d in scan if 50 <= d < 300]
                            if obstacles:
                                self.logs.log("LIDAR", f"Obstacle détecté ({len(obstacles)} pts), arrêt 10s")
                                self.send_raw("STOP")
                                ignorer_jusqu_a = time.time() + 15
                    except Exception as exc:
                        self.logs.log("ERR", f"Lidar: {exc}")
                        try:
                            self.lidar.lidar.stop()
                            self.lidar.lidar.clean_input()
                        except Exception:
                            pass
                        time.sleep(1)
            threading.Thread(target=boucle, daemon=True).start()
