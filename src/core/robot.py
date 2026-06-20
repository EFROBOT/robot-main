import math
import time
import threading
import cv2
from core.logs import Logs
from core.mecanum import Mecanum
from core.camera import Camera
from core.lidar import Lidar
from core.leds import BandeauLED
from core.affinite_cpu import fixer_affinite_cpu
from world.map import Map, TERRAIN_WIDTH, TERRAIN_HEIGHT
from core.servomoteur import init_servo, set_angle_servo


class Robot(Mecanum):
    def __init__(self, team, port=None, port_lidar=None, baudrate=115200, camera_id=0, x_init=0.0, y_init=0.0, angle_init_deg=0.0):
        self.logs = Logs(maxlen=400)
        super().__init__(logs=self.logs, port=port, baudrate=baudrate, x_init=x_init, y_init=y_init, angle_init_deg=angle_init_deg)

        self.camera = Camera(camera_id=camera_id, logs=self.logs)
        self.leds = BandeauLED(num_pixels=61, brightness=0.5, logs=self.logs)
        self.lidar = None
        if port_lidar:
            try:
                self.lidar = Lidar(port=port_lidar, logs=self.logs)
            except Exception as exc:
                self.logs.log("ERR", str(exc))
 
        init_servo()
        self.set_team(team)
        self.team = team
        self.map = Map(team=team)
        self.inventaire = []
        self.zone_ramassage = None
        self.tirette_en_place = True
        self.match_demarre = False 
        self.running = False
        self.last_align_time = 0.0
        self.align_interval_ms = 50
        self._lidar_thread_started = False
        # Tolérance hors table pour le filtrage Lidar (0 = strictement dans [0..W]x[0..H]).
        self.marge_ignore_lidar_cm = -10.0
        self.decalage_angle_lidar_deg = 0.0
        self.sens_angle_lidar = -1.0

        self.direction_vers_bas = True
        self.surveiller_lidar()

    def setup(self):
        if not self.camera.load_calibration():
            self.logs.log("INFO", "Aucune calibration trouvée, paramètres par défaut.")
            self.camera.use_default_calibration()

        if not self.camera.open():
            raise RuntimeError(f"Impossible d'ouvrir la caméra {self.camera.camera_id}")

    def set_team(self, team):
        if team == "yellow":
            self.send_raw("TJ")
        elif team == "blue":
            self.send_raw("TB")
        else:
            self.logs.log("ERR", "No team set")

    def stop(self):
        self.running = False
        if self.lidar:
            try:
                self.lidar.stop()
            except Exception as exc:
                self.logs.log("ERR", f"Erreur stop Lidar: {exc}")
            finally:
                self.lidar = None
        if self.leds:
            try:
                self.leds.stop()
            except Exception as exc:
                self.logs.log("ERR", f"Erreur stop LEDs: {exc}")
            finally:
                self.leds = None
        super().stop()
        try:
            self.camera.release()
        except Exception as exc:
            self.logs.log("ERR", f"Erreur release camera: {exc}")
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    def align_to_marker(self, marker):
        now = time.time() * 1000
        if now - self.last_align_time >= self.align_interval_ms:
            self.last_align_time = now

    def get_state(self):
        zone_view = None
        if self.zone_ramassage is not None:
            zone_view = {
                "distance": self.zone_ramassage["distance"],
                "decalage_x": self.zone_ramassage["decalage_x"],
                "angle": self.zone_ramassage["angle"],
            }

        return {
            "robot": {
                "x": self.x,
                "y": self.y,
                "team": self.team,
                "tirette_en_place": self.tirette_en_place,
                "match_demarre": self.match_demarre,
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
            "zone_ramassage_detectee": zone_view,
            "strategie_en_cours": False,
        }

    def get_logs(self):
        return self.logs.get_lines()

    # ------------------------------------------------------------------
    # Option pince
    
    def pince_navigation(self):
        self.send_raw("Pince Navigation")

    def pince_homologation(self):
        self.send_raw("Pince Homologation")

    def pince_recuperer_et_stocker(self, rotation_active, attendre=True, timeout=20):
        self.mouvement_termine.clear()
        self.send_raw(f"Pince_RecupererEtStocker {int(rotation_active)}")
        if attendre:
            return self.mouvement_termine.wait(timeout=timeout)
        return True

    # Option servo
    def fermer_porte(self):
        set_angle_servo(103)

    def ouvrir_porte(self):
        set_angle_servo(0)


    #--- LIDAR detection -------------
    def _obstacle_peut_etre_ignore(self, obstacle):
        distance_cm = float(obstacle.get("distance_cm", 0.0))
        angle_lidar_deg = float(obstacle.get("angle", 0.0))
        cap_deg = (self.angle_deg + self.decalage_angle_lidar_deg) % 360.0
        if getattr(self, "_marche_arriere", False):
            cap_deg = (cap_deg + 180.0) % 360.0

        angle_monde_deg = (cap_deg + (self.sens_angle_lidar * angle_lidar_deg)) % 360.0
        angle_rad = math.radians(angle_monde_deg)
        x_obs = self.x + distance_cm * math.cos(angle_rad)
        y_obs = self.y + distance_cm * math.sin(angle_rad)
        marge_cm = min(0.0, float(self.marge_ignore_lidar_cm))
        if x_obs < -marge_cm or x_obs > TERRAIN_WIDTH + marge_cm:
            self.logs.log("LIDAR", f"Obstacle ignoré (hors limites x): {obstacle}, position estimée: ({x_obs:.1f}, {y_obs:.1f})")
            return True
        if y_obs < -marge_cm or y_obs > TERRAIN_HEIGHT + marge_cm:
            self.logs.log("LIDAR", f"Obstacle ignoré (hors limites y): {obstacle}, position estimée: ({x_obs:.1f}, {y_obs:.1f})")
            return True
        self.logs.log("LIDAR", f"Obstacle valide: {obstacle}, position estimée: ({x_obs:.1f}, {y_obs:.1f})")
        return False

    def surveiller_lidar(self):
        # Utilisation de getattr au cas où _lidar_thread_started ne serait pas encore initialisé
        if getattr(self, "lidar", None) is None or getattr(self, "_lidar_thread_started", False):
            return

        self._lidar_thread_started = True

        # ==========================================
        # AJOUT CRUCIAL : Démarrer l'acquisition série en tâche de fond
        # C'est ici que tu définis tes distances de détection
        # ==========================================
        self.lidar.scan(distance_cm=44, min_distance_cm=1)

        def boucle():
            # Super pratique pour isoler ce thread critique sur un cœur de la Raspberry Pi
            fixer_affinite_cpu(0, logs=self.logs, nom_thread="lidar")
            
            while getattr(self, "lidar", None) is not None:
                try:
                    # scan() est maintenant instantané (non-bloquant)
                    obstacles = self.lidar.scan()
                except Exception as exc:
                    self.logs.log("ERR", f"Lidar scan error: {exc}")
                    time.sleep(0.5)
                    continue

                if getattr(self, "leds", None) and self.leds.pixels:
                    self.leds.eteindre()

                if obstacles:
                    obstacles_valides = []
                    for obstacle in obstacles:
                        angle_lidar_deg = float(obstacle.get("angle", 0.0)) % 360.0
                        
                        if getattr(self, "leds", None):
                            n_leds = max(1, int(self.leds.num_pixels))
                            index = int((angle_lidar_deg / 360.0) * n_leds)
                            if index >= n_leds:
                                index = n_leds - 1
                                
                            if self._obstacle_peut_etre_ignore(obstacle):
                                self.leds.set_pixel(index, (255, 128, 0)) # Orange : ignoré
                            else:
                                self.leds.set_pixel(index, (255, 0, 0))   # Rouge : danger
                                obstacles_valides.append(obstacle)
                        else:
                            if not self._obstacle_peut_etre_ignore(obstacle):
                                obstacles_valides.append(obstacle)

                    if getattr(self, "leds", None) and self.leds.pixels:
                        self.leds.show()

                    if obstacles_valides:
                        self.send_raw("STOP")
                        self.logs.log("LIDAR", f"Arrêt prioritaire Lidar ({len(obstacles_valides)} pts réels)")

                # La boucle tourne à 10 Hz. 
                # C'est parfait car scan() ne bloque plus.
                time.sleep(0.1) 

        threading.Thread(target=boucle, daemon=True).start()