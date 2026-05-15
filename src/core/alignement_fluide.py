import math
import time

from core.affinite_cpu import fixer_affinite_cpu


class AlignementFluide:
    """Alignement ArUco plus fluide, orienté micro-corrections rapides.

    Cette classe ne modifie pas le code existant: elle propose une alternative
    prête à être branchée depuis la stratégie ou le dashboard.
    """

    def __init__(self, robot, logs=None):
        self.robot = robot
        self.logs = logs if logs is not None else getattr(robot, "logs", None)

        # Seuils de validation finale
        self.seuil_distance_cm = 38.0
        self.seuil_lateral_cm = 2.2
        self.seuil_angle_deg = 2.5

        # Pas mini / maxi pour éviter les à-coups
        self.pas_rot_min_deg = 1.5
        self.pas_rot_max_deg = 9.0
        self.pas_lat_min_cm = 0.8
        self.pas_lat_max_cm = 6.0
        self.pas_av_min_cm = 1.0
        self.pas_av_max_cm = 7.0

        # Fréquences d'envoi des commandes (limite sur-sollicitation série)
        self.delai_cmd_rot_s = 0.09
        self.delai_cmd_lat_s = 0.09
        self.delai_cmd_av_s = 0.12

    def _log(self, niveau, message):
        if self.logs is not None:
            self.logs.log(niveau, message)

    @staticmethod
    def _borne(valeur, mini, maxi):
        return max(mini, min(maxi, valeur))

    @staticmethod
    def _normaliser_erreur_angle(angle_deg, angle_cible=-90.0):
        erreur = angle_deg - angle_cible
        return (erreur + 45.0) % 90.0 - 45.0

    @staticmethod
    def _choisir_caisse_repere(caisses):
        """Repère = caisse la plus loin (stratégie actuelle de votre équipe)."""
        if not caisses:
            return None
        triees = sorted(caisses, key=lambda c: float(getattr(c, "distance", 10**9)))
        return triees[-1]

    def _commande_rotation(self, erreur_angle):
        # Loi proportionnelle bornée pour rotation douce
        amplitude = abs(erreur_angle)
        pas = 0.55 * amplitude
        pas = self._borne(pas, self.pas_rot_min_deg, self.pas_rot_max_deg)
        return pas

    def _commande_laterale(self, lateral_cm):
        amplitude = abs(lateral_cm)
        pas = 0.45 * amplitude
        pas = self._borne(pas, self.pas_lat_min_cm, self.pas_lat_max_cm)
        return pas

    def _commande_avance(self, distance_cm, distance_arret_cm):
        avance_restante = distance_cm - distance_arret_cm
        pas = 0.5 * avance_restante
        pas = self._borne(pas, self.pas_av_min_cm, self.pas_av_max_cm)
        return pas

    def aligner_sur_aruco_fluide(self, frame_provider=None, timeout_s=14.0):
        """Version fluide: corrections fréquentes, petites, bornées.

        Retour:
            (True, ordre_blocs) si aligné
            False sinon
        """
        fixer_affinite_cpu(2, logs=self.logs, nom_thread="alignement_fluide")
        deadline = time.time() + timeout_s
        ordre_blocs = {}

        dernier_cmd_rot = 0.0
        dernier_cmd_lat = 0.0
        dernier_cmd_av = 0.0

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
                time.sleep(0.02)
                continue

            try:
                caisses = self.robot.camera.aruco.detect_markers(frame)
            except Exception as exc:
                self._log("ERR", f"alignement_fluide: detect_markers: {exc}")
                time.sleep(0.02)
                continue

            if not caisses:
                self._log("WARN", "alignement_fluide: aucune caisse détectée.")
                time.sleep(0.02)
                continue

            # Sauvegarde ordre observé
            caisses_triees = sorted(caisses, key=lambda c: float(getattr(c, "distance", 10**9)))
            ordre_blocs = {i + 1: c.equipe for i, c in enumerate(caisses_triees)}

            cible = self._choisir_caisse_repere(caisses)
            if cible is None:
                time.sleep(0.02)
                continue

            distance = float(cible.distance)
            lateral = float(cible.decalage_x)
            angle = float(cible.angle_longueur)
            err_angle = self._normaliser_erreur_angle(angle, -90.0)

            ok_distance = distance <= self.seuil_distance_cm
            ok_lateral = abs(lateral) <= self.seuil_lateral_cm
            ok_angle = abs(err_angle) <= self.seuil_angle_deg

            if ok_distance and ok_lateral and ok_angle:
                self._log("INFO", f"alignement_fluide: aligné ✓ ordre={ordre_blocs}")
                return True, ordre_blocs

            now = time.time()

            # 1) Angle d'abord (évite dérives latérales)
            if not ok_angle and (now - dernier_cmd_rot) >= self.delai_cmd_rot_s:
                pas = self._commande_rotation(err_angle)
                if err_angle > 0:
                    self.robot.rotation_gauche(pas)
                else:
                    self.robot.rotation_droite(pas)
                dernier_cmd_rot = now
                continue

            # 2) Latéral ensuite
            if not ok_lateral and (now - dernier_cmd_lat) >= self.delai_cmd_lat_s:
                pas = self._commande_laterale(lateral)
                if lateral > 0:
                    self.robot.droite(pas)
                else:
                    self.robot.gauche(pas)
                dernier_cmd_lat = now
                continue

            # 3) Approche distance en dernier
            if not ok_distance and (now - dernier_cmd_av) >= self.delai_cmd_av_s:
                pas = self._commande_avance(distance, self.seuil_distance_cm)
                self.robot.avancer(pas)
                dernier_cmd_av = now
                continue

            time.sleep(0.01)

        self._log("WARN", "alignement_fluide: timeout")
        return False
