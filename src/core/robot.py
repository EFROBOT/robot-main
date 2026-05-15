import math
import time
import threading
import cv2

from core.logs import Logs
from core.mecanum import Mecanum
from core.camera import Camera
from core.lidar import Lidar
from core.ultrasson import Ultrasson
from core.servomoteur import init_servo, set_angle_servo
from core.affinite_cpu import fixer_affinite_cpu
from world.map import Map, TERRAIN_WIDTH, TERRAIN_HEIGHT


class Robot(Mecanum):
    def __init__(self, team, port=None, port_lidar=None, baudrate=115200, camera_id=0, x_init=0.0, y_init=0.0, angle_init_deg=0.0):
        self.logs = Logs(maxlen=400)
        super().__init__(logs=self.logs, port=port, baudrate=baudrate, x_init=x_init, y_init=y_init, angle_init_deg=angle_init_deg)

        self.camera = Camera(camera_id=camera_id, logs=self.logs)
        self.lidar = None
        if port_lidar:
            try:
                self.lidar = Lidar(port=port_lidar, logs=self.logs)
            except Exception as exc:
                self.logs.log("ERR", str(exc))

        self.surveiller_lidar()
        #self.surveiller_bord_map()
        #self.surveiller_zone_exclusion()
 
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
        # Distance de sécurité pour ignorer les retours Lidar venant des bords
        # du terrain (en cm, dans le repère monde).
        self.lidar_ignore_margin_cm = 45.0

        # Init 
        init_servo()

        # if ultrasson alors 
        """
        self.ultrason_front = Ultrasson(
            sensor_id="1", trig=23, echo=24, threshold=15
            )
        self.surveiller()"""


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
                
                zone = self.camera.aruco.detect_zone_ramassage(frame)
                self.zone_ramassage = zone
                self.camera.aruco.draw_zone_ramassage(frame, zone)

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
        
    def stop(self):
        """Arrête les mouvements du robot et ferme la caméra."""
        self.running = False
        super().stop()  # Envoie "STOP" au STM32
        self.camera.release()
        cv2.destroyAllWindows()


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

    def recuperer_caisses(self, recup, attendre=True, timeout=30):
        self.send_raw(f"Recuperer caisse {recup}")
        if attendre:
            ok = self.mouvement_pince_termine.wait(timeout=timeout)
            if not ok:
                self.logs.log("ERR", f"Timeout récupération caisses ({recup})")
            return ok
        return True

    def pince_navigation(self):
        self.send_raw("Pince Navigation")

    def pince_homologation(self):
        self.send_raw("Pince Homologation")

    # Option servo
    def securiser_caisses(self):
        set_angle_servo(103)

    def lacher_caisses(self):
        set_angle_servo(0)

    # ------------------------------------------------------------------
    
    def calculer_chemin_esquive(self, x_actuel, y_actuel, x_cible, y_cible, zones_a_eviter):
        marge = 20.0 
        
        for zone in zones_a_eviter:
            excl_x_min = (zone.center.x - (zone.width / 2.0)) - marge
            excl_x_max = (zone.center.x + (zone.width / 2.0)) + marge
            excl_y_min = (zone.center.y - (zone.height / 2.0)) - marge
            excl_y_max = (zone.center.y + (zone.height / 2.0)) + marge

            traverse_y = (y_actuel < excl_y_min and y_cible > excl_y_min) or (y_actuel > excl_y_max and y_cible < excl_y_max)
            traverse_x = (x_actuel > excl_x_min and x_actuel < excl_x_max) or (x_cible > excl_x_min and x_cible < excl_x_max)

            if traverse_y and traverse_x:
                x_contournement = excl_x_min - 10 if x_cible < zone.center.x else excl_x_max + 10
                y_contournement = excl_y_min - 10 
                
                self.logs.log("WARN", f"Obstacle esquivé : {zone.name}")
                return [(x_contournement, y_contournement), (x_cible, y_cible)]
        
        return [(x_cible, y_cible)]
        
    def attendre_fin_trajet(self, timeout=25.0):
        succes = self.mouvement_termine.wait(timeout)
        
        if not succes:
            self.logs.log("WARN", "Timeout: La STM32 n'a pas renvoyé 'C Ok'")

    # Top level for évitement objet
    def aller_a_coord_intelligent(self, x_cible, y_cible, zones_a_eviter=None):
        if zones_a_eviter is None:
            zones_a_eviter = []

        waypoints = self.calculer_chemin_esquive(self.x, self.y, x_cible, y_cible, zones_a_eviter)
        
        for point in waypoints:
            px, py = point
            self.aller_a_coord(px, py)
            self.attendre_fin_trajet()
            self.x, self.y = px, py

    # ------------------------------------------------------------------
    # Surveiller map
    """
    def surveiller_bord_map(self):
        marge = 2.0
        demi_largeur = 32.0 / 2
        demi_longueur = 28.0 / 2

        x_min = marge + demi_largeur
        x_max = 300.0 - (marge + demi_largeur)
        y_min = marge + demi_longueur
        y_max = 200.0 - (marge + demi_longueur)

        def boucle():
            while True:
                if getattr(self, 'match_demarre', False):
                    x, y = self.x, self.y
                    
                    if x < x_min or x > x_max or y < y_min or y > y_max:
                        self.send_raw("STOP")
                        self.logs.log("WARN", f"Limite carte atteinte: x={x:.1f}, y={y:.1f}")
                        
                        self.degager_du_bord(x, y, x_min, x_max, y_min, y_max)
                        time.sleep(2)

                time.sleep(0.1)

        threading.Thread(target=boucle, daemon=True).start()


    def surveiller_zone_exclusion(self):
        # Paramètres de sécurité
        marge = 5.0
        demi_largeur = 32.0 / 2  # 16.0
        demi_longueur = 28.0 / 2 # 14.0

        # Limites réelles de la zone (Centre: 150,180 | Largeur: 180 | Hauteur: 40)
        zone_x_min = 150.0 - (180.0 / 2) # 60.0
        zone_x_max = 150.0 + (180.0 / 2) # 240.0
        zone_y_min = 180.0 - (40.0 / 2)  # 160.0
        zone_y_max = 180.0 + (40.0 / 2)  # 200.0

        # Zone critique pour le CENTRE du robot (Zone + Marge + Taille Robot)
        excl_x_min = zone_x_min - marge - demi_largeur # 39.0
        excl_x_max = zone_x_max + marge + demi_largeur # 261.0
        excl_y_min = zone_y_min - marge - demi_longueur # 141.0
        excl_y_max = zone_y_max + marge + demi_longueur # 219.0

        def boucle():
            while True:
                x, y = self.x, self.y
                
                # Si le centre du robot rentre dans le rectangle critique
                if excl_x_min < x < excl_x_max and excl_y_min < y < excl_y_max:
                    self.send_raw("STOP")
                    self.logs.log("WARN", f"Zone d'exclusion atteinte ! x={x:.1f}, y={y:.1f}")
                    
                    self.degager_du_bord(x, y, excl_x_min, excl_x_max, excl_y_min, excl_y_max)
                    time.sleep(2) 

                time.sleep(0.1)

        # On lance le thread en arrière-plan
        threading.Thread(target=boucle, daemon=True).start()

    def degager_du_bord(self, x, y, x_min, x_max, y_min, y_max):
        x_cible = max(x_min + 10, min(x, x_max - 10))
        y_cible = max(y_min + 10, min(y, y_max - 10))
        
        self.logs.log("INFO", f"Dégagement vers x={x_cible:.1f}, y={y_cible:.1f}")
        self.aller_a_coord(x_cible, y_cible)"""

    # ------------------------------------------------------------------
    # Evitement obstacle avec camera (caisses)

    def evitement_obstacle():
        pass

    # Surveiller obstacle (Lidar + Ultrason Ou TOF Ou Camera)
    # Camera --> A implementer
    # ------------------------------------------------------------------

    # Only lidar
    def _pres_du_bord_de_carte(self, marge=18.0):
        return (
            self.x <= marge
            or self.x >= TERRAIN_WIDTH - marge
            or self.y <= marge
            or self.y >= TERRAIN_HEIGHT - marge
        )

    def _bords_de_carte_proches(self, marge=None):
        if marge is None:
            marge = self.lidar_ignore_margin_cm
        bords = set()
        if self.x <= marge:
            bords.add("left")
        if self.x >= TERRAIN_WIDTH - marge:
            bords.add("right")
        if self.y <= marge:
            bords.add("bottom")
        if self.y >= TERRAIN_HEIGHT - marge:
            bords.add("top")
        return bords

    def _cote_obstacle_lidar(self, angle_deg):
        # Convertit l'angle Lidar vers le repère terrain et le ramène entre 0° et 360°
        angle = (float(angle_deg) + float(self.angle_deg)) % 360.0

        if 45.0 <= angle < 135.0:
            return "top"
        elif 135.0 <= angle < 225.0:
            return "right"
        elif 225.0 <= angle < 315.0:
            return "bottom"
        else:
            return "left"

    def _obstacle_peut_etre_ignored(self, obstacle, bords_proches):
        cote_obstacle = self._cote_obstacle_lidar(obstacle["angle"])
        return cote_obstacle in bords_proches

    def surveiller_lidar(self):
            if not self.lidar:
                return
            def boucle():
                fixer_affinite_cpu(0, logs=self.logs, nom_thread="lidar")
                last_heartbeat = time.time()
                heartbeat_interval_s = 3.0
                clear_consecutive = 0
                required_clear = 3
                while self.lidar:
                    try:
                        obstacles = self.lidar.scan()
                    except Exception as exc:
                        self.logs.log("ERR", f"Lidar scan error: {exc}")
                        time.sleep(0.5)
                        continue
                    if obstacles:
                        self.send_raw("STOP")
                        """
                        while True:
                                self.send_raw("STOP")
                                time.sleep(1)
                                self.logs.log("LIDAR", "Arrêt prioritaire Lidar")
                        """
                        
                        bords_proches = self._bords_de_carte_proches()
                        if bords_proches and all(self._obstacle_peut_etre_ignored(o, bords_proches) for o in obstacles):
                            self.logs.log(
                               "LIDAR",
                                f"Obstacle bord ignoré: x={self.x:.1f}, y={self.y:.1f}, bords={sorted(bords_proches)}",
                            )
                            time.sleep(0.2)
                            continue

                        details = ", ".join(f"{o['angle']}°/{o['distance_cm']}cm" for o in obstacles)
                        #self.logs.log("LIDAR", f"Obstacle détecté ({len(obstacles)} pts): {details}")

                        # Prioritise Lidar: stop robot and mark paused state
                        if not getattr(self, "_paused_by_lidar", False):
                            self._paused_by_lidar = True
                            self.send_raw("STOP")
                            self.logs.log("LIDAR", "Arrêt prioritaire Lidar")

                        clear_consecutive = 0
                       
                    else:
                        # No obstacles seen in this scan
                        if getattr(self, "_paused_by_lidar", False):
                            clear_consecutive += 1
                            if clear_consecutive >= required_clear:
                                clear_consecutive = 0
                                self.logs.log("LIDAR", "Obstacle disparu, tentative de reprise")
                                try:
                                    resumed = False
                                    if hasattr(self, "resume_last_motion"):
                                        resumed = self.resume_last_motion()
                                    if resumed:
                                        self.logs.log("LIDAR", "Reprise mouvement envoyé")
                                    else:
                                        self.logs.log("LIDAR", "Aucun mouvement à reprendre")
                                    self._paused_by_lidar = False
                                except Exception as exc:
                                    self.logs.log("ERR", f"Erreur reprise Lidar: {exc}")
                                    self._paused_by_lidar = False
                                

                    time.sleep(0.1)
            
            threading.Thread(target=boucle, daemon=True).start()
    
    # Lidar & camera 
    def surveiller(self):
        pass

    # Lidar & ultrasson
    """
    def surveiller(self):
            def boucle():
                while True:
                    # 1. Vérification des Ultrason
                    # 
                    # 
                    # 
                    # s (Priorité haute, temps de réponse court)
                    if hasattr(self, 'ultrason_front') and not self.ultrason_front.is_clear():
                        self.logs.log("WARN", "ULTRASON: Obstacle proche, STOP")
                        self.send_raw("STOP")
                        time.sleep(2)
                        continue # On recommence la boucle immédiatement

                    # 2. Vérification du Lidar
                    if self.lidar:
                        try:
                            obstacles = self.lidar.scan()
                            if obstacles:
                                self.logs.log("LIDAR", f"Obstacle ({len(obstacles)} pts), arrêt 10s")
                                self.send_raw("STOP")
                                time.sleep(10)
                                
                                # Nettoyage après l'arrêt
                                try:
                                    self.lidar.lidar.stop()
                                    self.lidar.lidar.clean_input()
                                except: pass
                                
                                self.logs.log("LIDAR", "Reprise")
                                time.sleep(2)
                        except Exception as exc:
                            self.logs.log("ERR", f"Lidar: {exc}")
                            time.sleep(0.5)

                    # Petite pause pour ne pas surcharger le CPU
                    time.sleep(0.05)

            threading.Thread(target=boucle, daemon=True).start()"""
