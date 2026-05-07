"""
Module de strategie

Strategy == Top level

Strategie 1 :
    Faire dans l'ordre les différentes zones de ramassage / garde_manger
    Au bout de la deuxième rotation --> curseur thermometre

Strategie 2 :
    Aller dans la zone la plus proche en fonction de la position du robot

Strategie 3 :
    (à définir)
"""

import time
import math
from core.camera import Camera
from core.robot import Robot

class Strategy:
    def __init__(self, carte, robot):
        self.carte = carte
        self.robot = robot

    # ------------------------------------------------------------------
    # Approche odométrique

    def approche_ramassage(self, zone):
        """Navigation odométrique vers le point d'approche de la zone de ramassage."""
        dist_avant = 15.0

        if zone.height > zone.width:
            if self.robot.y > zone.center.y:
                x_cible = zone.center.x
                y_cible = zone.y_max() + dist_avant
                angle_cible = 270.0
            else:
                x_cible = zone.center.x
                y_cible = zone.y_min() - dist_avant
                angle_cible = 90.0
        else:
            if self.robot.x > zone.center.x:
                x_cible = zone.x_max() + dist_avant
                y_cible = zone.center.y
                angle_cible = 180.0
            else:
                x_cible = zone.x_min() - dist_avant
                y_cible = zone.center.y
                angle_cible = 0.0

        self.robot.logs.log("INFO", f"Approche → ({x_cible}, {y_cible}) angle={angle_cible}°")
        self.robot.aller_a_coord(x_cible, y_cible)
        self.robot.tourner_vers_angle(angle_cible)


    def approche_garde_manger(self, zone):
        """Navigation odométrique vers le point de dépôt du garde-manger."""
        dist_arriere = 15.0

        dx = self.robot.x - zone.center.x
        dy = self.robot.y - zone.center.y

        if abs(dx) > abs(dy):
            if dx > 0:
                target_x, target_y, angle = zone.x_max() + dist_arriere, zone.center.y, 0.0
            else:
                target_x, target_y, angle = zone.x_min() - dist_arriere, zone.center.y, 180.0
        else:
            if dy > 0:
                target_x, target_y, angle = zone.center.x, zone.y_max() + dist_arriere, 90.0
            else:
                target_x, target_y, angle = zone.center.x, zone.y_min() - dist_arriere, -90.0

        self.robot.tourner_vers_angle(angle)
        self.robot.aller_a_coord(target_x, target_y)

    # ------------------------------------------------------------------
    # Calibration fine ArUco

    def aligner_sur_aruco(self, timeout_s=10.0, frame_provider=None):
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            if frame_provider is not None:
                frame = frame_provider()
            else:
                ret, frame = self.robot.camera.read()
                if not ret:
                    frame = self.robot.camera.get_latest_frame()
                    if not frame:
                        frame = None

            if frame is None:
                self.robot.logs.log("WARN", "aligner_sur_aruco: pas de frame, attente...")
                time.sleep(0.05)
                continue

            try:
                caisses = self.robot.camera.aruco.detect_markers(frame)
            except Exception as e:
                self.robot.logs.log("ERR", f"detect_markers: {e}")
                time.sleep(0.05)
                continue

            if not caisses:
                self.robot.logs.log("WARN", "aligner_sur_aruco: aucune caisse détectée.")
                time.sleep(0.05)
                continue

            caisse   = caisses[0]
            bearing = caisse.angle_longueur
            distance = caisse.distance
            lateral  = caisse.decalage_x

            self.robot.logs.log(
                "INFO",
                f"ArUco → dist={distance:.1f}cm lateral={lateral:+.1f}cm angle={caisse.angle_longueur:+.1f}°"
            )

            if distance > 45.0:
                avance_cmd = 15 
                self.robot.avancer(avance_cmd)
                time.sleep(0.5)
                continue

            if abs(bearing) > 5.0:
                angle_cmd = round(abs(bearing)) - 90
                if angle_cmd > 5:
                    if bearing > 0:
                        self.robot.mecanum.rotation_droite(angle_cmd)
                    else:
                        self.robot.mecanum.rotation_gauche(angle_cmd)
                time.sleep(0.3)
                continue

            if abs(lateral) > 5.0:
                dist_cmd = round(abs(lateral)) * 0.6 # Seulement de l'erreur calcule 
                if dist_cmd > 5: 
                    if lateral > 0:
                        self.robot.droite(dist_cmd)
                    else:
                        self.robot.gauche(dist_cmd)
                time.sleep(0.3)
                continue

            hyp = distance - 10
            if hyp > 29:
                x = math.sqrt((hyp * hyp) - (29 * 29))
                self.robot.logs.log("INFO", f"Le robot doit avancer de {x:.1f} cm")
                
                if x > 2.0: 
                    self.robot.avancer(round(x))
                    time.sleep(0.5)
                    continue

            self.robot.logs.log("INFO", "ArUco → ALIGNÉ ✓")
            return True

        self.robot.logs.log("WARN", "aligner_sur_aruco: timeout.")
        return False


    def test_alignement(self, frame_provider):

        self.robot.logs.log("INFO", "Test alignement ArUco démarré...")
        result = self.aligner_sur_aruco(timeout_s=15.0, frame_provider=frame_provider)
        self.robot.logs.log("INFO", f"Test alignement ArUco terminé → {'OK ✓' if result else 'TIMEOUT ✗'}")
        return result


    # ------------------------------------------------------------------
    # Stratégies de haut niveau

    def strategy_1(self):
        """
        Ordre fixe : R1 → G3.
        Approche odométrique puis calibration ArUco sur chaque zone.
        """
        time.sleep(1)

        # --- Ramassage R1 ---
        zone_r = self.carte.ramassage["R1"]
        self.approche_ramassage(zone_r)
        aligned = self.aligner_sur_aruco()
        self.robot.logs.log("INFO", f"R1 aligné={aligned}")

        time.sleep(1)

        # --- Dépôt G3 ---
        zone_g = self.carte.garde_mangers["G3"]
        self.approche_garde_manger(zone_g)


    def strategy_2(self):
        """Aller dans la zone la plus proche."""
        pass

    def strategy_3(self):
        pass
