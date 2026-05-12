import time
import math
import threading
from core.camera import Camera
from core.robot import Robot

class Strategy:
    def __init__(self, carte, robot):
        self.carte = carte
        self.robot = robot

    # ------------------------------------------------------------------
    # Temps match
    def verifier_fin_match(self):
        temps_ecoule = time.time() - self.debut_match
        if temps_ecoule >= 80.0: 
            self.robot.logs.log("WARN", "85 seconde atteintes")
            if self.robot.team == "yellow":
                self.retourner_zone_fin(20, 180) 
            elif self.robot.team == "bleu":
                self.retourner_zone_fin(280, 180) 

            return True
        return False

    def retourner_zone_fin(self, x , y):
        self.robot.logs.log("INFO", "Trajet vers la zone de fin")
        self.robot.aller_a_coord(x, y)

    def surveiller_temps(self):
        while True:
            if self.verifier_fin_match():
                break
            time.sleep(1.0)

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
        if not self.robot.aller_a_coord(x_cible, y_cible):
            return False  # timeout ou erreur

        if not self.robot.tourner_vers_angle(angle_cible):
            return False

        return True

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

    def aligner_sur_aruco(self, timeout_s=30.0, frame_provider=None):
        deadline = time.time() + timeout_s
        meilleur_ordre_blocs = {}

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

            caisses.sort(key=lambda x: x.distance)
            
            if len(caisses) >= len(meilleur_ordre_blocs):
                meilleur_ordre_blocs = {}
                for index, bloc in enumerate(caisses):
                    meilleur_ordre_blocs[index + 1] = bloc.equipe

            caisse = caisses[-1] #a verfier avec l'angle de la camera
            distance = caisse.distance
            lateral = caisse.decalage_x
            angle = caisse.angle_longueur

            self.robot.logs.log("INFO", f"Cible :  à dist={distance:.1f}cm lateral={lateral:+.1f}cm angle={caisse.angle_longueur:+.1f}°")
            distance_arret = 41 
            
            if distance <= distance_arret and abs(lateral) <= 3:
                self.robot.logs.log("INFO", f"ArUco → Cible atteinte ! Dist: {distance:.1f}cm")
                self.robot.logs.log("INFO", f"ArUco → ALIGNÉ ✓ Ordre des blocs: {meilleur_ordre_blocs}")
                return True, meilleur_ordre_blocs

            angle_cible = -90.0 
            erreur_angle = angle - angle_cible
            erreur_angle = (erreur_angle + 45) % 90 - 45
            
            if abs(erreur_angle) > 3.0: 
                if erreur_angle > 0:
                    self.robot.rotation_gauche(int(abs(erreur_angle)) + 3)
                else:
                    self.robot.rotation_droite(int(abs(erreur_angle)) + 3)
                continue

            dist_cmd = round(abs(lateral))
            if dist_cmd > 3: 
                if lateral > 0:
                    self.robot.droite(float(dist_cmd * 0.6))
                else:
                    self.robot.gauche(float(dist_cmd * 0.6))
                time.sleep(0.5) 
                continue 

            hyp = distance - 10
            if hyp > 2: 
                if hyp > 29:
                    x = float(round(math.sqrt((hyp * hyp) - (29 * 29))))
                else:
                    x = float(round(hyp))
                step = min(x, 10.0)
                self.robot.logs.log("INFO", f"Avance par palier: {step}")
                self.robot.avancer(step)
                time.sleep(0.5)
                continue

            self.robot.logs.log("INFO", "ArUco → ALIGNÉ ✓")
            return True, meilleur_ordre_blocs

        self.robot.logs.log("WARN", "aligner_sur_aruco: timeout.")
        return False

    def aligner_sur_aruco_uniquement_lateral(self, timeout_s=10.0, frame_provider=None): 
        # petite puissance uniquement pour micro ajustement
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

            caisses.sort(key=lambda x: x.distance)
            caisse = caisses[0]
            lateral = caisse.decalage_x

            self.robot.logs.log("INFO", f"Cible : lateral={lateral:+.1f}")
            
            if abs(lateral) <= 4:
                ordre_blocs = {}
                for index, bloc in enumerate(caisses):
                    ordre_blocs[index + 1] = bloc.equipe

                self.robot.logs.log("INFO", f"ArUco → ALIGNÉ ✓ Ordre des blocs: {ordre_blocs}")
                return True, ordre_blocs

            dist_cmd = round(abs(lateral))
            if dist_cmd > 3: 
                if lateral > 0:
                    self.robot.droite(float(dist_cmd * 0.6))
                else:
                    self.robot.gauche(float(dist_cmd * 0.6))
                time.sleep(0.5) 
                continue

            angle_cible = -90.0 
            erreur_angle = angle - angle_cible
            erreur_angle = (erreur_angle + 45) % 90 - 45
            if abs(erreur_angle) > 3.0: 
                if erreur_angle > 0:
                    self.robot.rotation_gauche(int(abs(erreur_angle)) + 3) # sens inversé
                else:
                    self.robot.rotation_droite(int(abs(erreur_angle)) + 3)
                continue

        return False

    def prendre_set_caisse(self, team, frame_provider=None):
        self.robot.logs.log("INFO", "Début de la séquence de ramassage...")
        self.robot.securiser_caisses()
        result = self.aligner_sur_aruco(timeout_s=15.0, frame_provider=frame_provider)
        if not result:
            self.robot.logs.log("WARN", "prendre_set_caisse: Échec de l'alignement initial.")
            return False

        _, ordre_blocs = result
        numero_caisse = 1

        while ordre_blocs:
            couleur_caisse = ordre_blocs.get(1)
            self.robot.logs.log("INFO", f"Prise de la caisse n°{numero_caisse} ({couleur_caisse}) - Attente 15s")
            if couleur_caisse == team:
                ok = self.robot.recuperer_caisses(1)
            else:
                ok = self.robot.recuperer_caisses(0)

            if not ok:
                self.robot.logs.log("ERR", "Échec récupération caisse")
                break

            if len(ordre_blocs) <= 0:
                break

            etat_attendu = {}
            for i in range(2, len(ordre_blocs) + 1):
                if i in ordre_blocs:
                    etat_attendu[i - 1] = ordre_blocs[i]

            self.robot.avancer(7.0)
            
            result_lat = self.aligner_sur_aruco_uniquement_lateral(timeout_s=10.0, frame_provider=frame_provider)
            if not result_lat:
                self.robot.logs.log("WARN", "Perte du signal ArUco ou timeout latéral.")
                break
                
            _, nouvel_ordre_blocs = result_lat

            if nouvel_ordre_blocs == etat_attendu:
                self.robot.logs.log("INFO", "Vérification OK: L'ordre des caisses correspond à l'état attendu.")
            else:
                self.robot.logs.log("WARN", f"Désynchro détectée ! Attendu: {etat_attendu} | Vu: {nouvel_ordre_blocs}")

            ordre_blocs = nouvel_ordre_blocs
            numero_caisse += 1

        self.robot.logs.log("INFO", "Séquence de ramassage terminée ✓")
        return True

    # ------------------------------------------------------------------
    # Test (temporaire)

    def test_alignement(self, frame_provider=None):
        self.robot.logs.log("INFO", "Test alignement ArUco démarré...")
        result = self.prendre_set_caisse(team="yellow", frame_provider=frame_provider)
        self.robot.logs.log("INFO", f"Test alignement ArUco terminé → {'OK ✓' if result else 'TIMEOUT ✗'}")
        return result

    # ------------------------------------------------------------------
    # Calibration zone de ramassage

    def aligner_sur_zone_de_ramassage(self, timeout_s=30.0, frame_provider=None):
        deadline = time.time() + timeout_s
        meilleur_ordre_blocs = {}

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

            caisses.sort(key=lambda x: x.distance)
            
            if len(caisses) >= len(meilleur_ordre_blocs):
                meilleur_ordre_blocs = {}
                for index, bloc in enumerate(caisses):
                    meilleur_ordre_blocs[index + 1] = bloc.equipe

            caisse = caisses[-1] #a verfier avec l'angle de la camera
            distance = caisse.distance
            lateral = caisse.decalage_x
            angle = caisse.angle_longueur

            self.robot.logs.log("INFO", f"Cible :  à dist={distance:.1f}cm lateral={lateral:+.1f}cm angle={caisse.angle_longueur:+.1f}°")
            distance_arret = 41 
            
            if distance <= distance_arret and abs(lateral) <= 3:
                self.robot.logs.log("INFO", f"ArUco → Cible atteinte ! Dist: {distance:.1f}cm")
                self.robot.logs.log("INFO", f"ArUco → ALIGNÉ ✓ Ordre des blocs: {meilleur_ordre_blocs}")
                return True, meilleur_ordre_blocs

            angle_cible = -90.0 
            erreur_angle = angle - angle_cible
            erreur_angle = (erreur_angle + 45) % 90 - 45
            
            if abs(erreur_angle) > 3.0: 
                if erreur_angle > 0:
                    self.robot.rotation_gauche(int(abs(erreur_angle)) + 3)
                else:
                    self.robot.rotation_droite(int(abs(erreur_angle)) + 3)
                continue

            dist_cmd = round(abs(lateral))
            if dist_cmd > 3: 
                if lateral > 0:
                    self.robot.droite(float(dist_cmd * 0.6))
                else:
                    self.robot.gauche(float(dist_cmd * 0.6))
                time.sleep(0.5) 
                continue 

            hyp = distance - 10
            if hyp > 2: 
                if hyp > 29:
                    x = float(round(math.sqrt((hyp * hyp) - (29 * 29))))
                else:
                    x = float(round(hyp))
                step = min(x, 10.0)
                self.robot.logs.log("INFO", f"Avance par palier: {step}")
                self.robot.avancer(step)
                time.sleep(0.5)
                continue

            self.robot.logs.log("INFO", "ArUco → ALIGNÉ ✓")
            return True, meilleur_ordre_blocs

        self.robot.logs.log("WARN", "aligner_sur_aruco: timeout.")
        return False

    def depot_set_caisse(self, frame_provider=None):
        self.robot.logs.log("INFO", "Début de la séquence de dépot de caisses...")
        
        result = self.aligner_sur_zone_de_ramassage(timeout_s=15.0, frame_provider=frame_provider)
        if not result:
            self.robot.logs.log("WARN", "prendre_set_caisse: Échec de l'alignement initial.")
            return False

        if result: 
            self.robot.logs.log("INFO", "Le robot est aligné sur la zone de dépot")

            def sequence_depot():
                time.sleep(1) # to check 
                self.robot.lacher_caisses()

            thread_action = threading.Thread(target=sequence_depot)
            thread_action.start()

            self.robot.avancer(25)

            self.robot.logs.log("INFO", "Séquence de dépot terminée --> 4 points marqué ?")
            return True


    # ------------------------------------------------------------------
    # Recalibrage de la position du robot a chaque approche de zone de ramassage ou de caisses 
    # Pas le temps de le faire

    def recalibrage_position(self, zone):
        pass

    # ------------------------------------------------------------------
    # Zone a éviter

    def lister_zones_a_eviter(self, zone_cible=None):
        zones = []
        
        zones.append(self.carte.exclusion["Exclusion"])

        for zone in self.carte.ramassage.values():
            if zone.etat == EtatZone.PLEINE:
                if zone_cible is None or zone.name != zone_cible.name:
                    zones.append(zone)

        return zones
    # ------------------------------------------------------------------
    # Stratégies de haut niveau

    # Au début du match, interupteur pour connaitre notre équipe (Jaune Ou Bleu) 

    # Le robot va dans la zone de ramassage la plus proche, puis dans le dépot le plus proche à l'aide des coordonnées
    # Point sotcké en dur (differentes pour chaque équipe)
    # Approche de chaque zone optimisé 

    # A l'approche d'une zone de ramassage, le robot scan les caisses puis s'alignes
    # Puis lancement de la phase de ramassage avec la pince (Coté STM)

    # A chaque zone de ramassage / dépot --> recalibrage de la position du robot (idealement)

    # SI le robot va sur une zone de ramassage, pas de caisse, 
    # ALOS le robot va à la prochaine zone de ramassage

    # SI le robot detecte un obstacle (Lidar / (TOF ou Ultrasson)
    # ALORS Arret complet du robot --> Class robot

    # Au bout de 85s le robot revient dans son nids (Pour eviter les pamis)

    # 4 Phases de stategie :
    # Strategie Jaune
    # R1 -> G4 -> R3 -> G5 -> R7 -> G8 -> R5 -> G3 

    # Strategie Bleu
    # R2 -> G6 -> R4 -> G5 -> R8 -> G10 -> R6 -> G7

    # ------------------------------------------------------------------

    # Jaune 
    def strategy_1_jaune(self, frame_provider):
        self.robot.logs.log("INFO", "Start strategy")
        self.debut_match = time.time()
        # Thread pour le temps 
        monitor_thread = threading.Thread(target=self.surveiller_temps, daemon=True)
        monitor_thread.start()
        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 1
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R1"]
        self.robot.logs.log("INFO", f"Le robot se dirige vers la zone {zone_r} ")
        self.approche_ramassage(zone_r)
        self.robot.match_demarre = True

        caisse = self.prendre_set_caisse(team = "yellow", frame_provider=frame_provider)
        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G4"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R1 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)

        """
        zone = self.carte.ramassage["R1"]
        
        # On vérifie si la zone contient encore des caisses
        if zone.etat == EtatZone.PLEINE:
            self.approche_ramassage(zone)
            caisse = self.prendre_set_caisse()
            
            if caisse:
                self.carte.vider_zone("R1")
                time.sleep(1)
                                
                zone_g3 = self.carte.garde_mangers["G3"]
                self.approche_garde_manger(zone_g3)
                

                self.carte.remplir_garde_manger("G3")
                time.sleep(1)
            else:
                self.robot.logs.log("WARN", "R1 vide ou ArUco introuvable -> Skip vers PHASE 2")
        else:
            self.robot.logs.log("WARN", "Zone R1 déjà enregistrée comme VIDE -> Skip.")

        time.sleep(1)
        """

        # ------------------------------------------------------------------
        # PHASE 2
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R3"]
        self.approche_ramassage(zone_r)
        caisse = self.prendre_set_caisse()

        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G5"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R3 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)     

        # ------------------------------------------------------------------
        # PHASE 3
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R7"]
        self.approche_ramassage(zone_r)
        caisse = self.prendre_set_caisse()

        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G8"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R1 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 4
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R5"]
        self.approche_ramassage(zone_r)
        caisse = self.prendre_set_caisse()

        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G3"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R1 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)

    # ------------------------------------------------------------------

    def strategy_1_bleu(self, frame_provider):
        self.robot.logs.log("INFO", "Start strategy")
        self.debut_match = time.time()
        # Thread pour le temps 
        monitor_thread = threading.Thread(target=self.surveiller_temps, daemon=True)
        monitor_thread.start()
        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 1
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R2"]
        self.robot.logs.log("INFO", f"Le robot se dirige vers la zone {zone_r} ")
        self.approche_ramassage(zone_r)
        self.robot.match_demarre = True

        caisse = self.prendre_set_caisse(team = "yellow", frame_provider=frame_provider)
        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G6"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R2 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 2
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R4"]
        self.approche_ramassage(zone_r)
        caisse = self.prendre_set_caisse()

        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G5"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R4 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 3
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R8"]
        self.approche_ramassage(zone_r)
        caisse = self.prendre_set_caisse()

        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G10"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R8 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 4
        # ------------------------------------------------------------------

        zone_r = self.carte.ramassage["R6"]
        self.approche_ramassage(zone_r)
        caisse = self.prendre_set_caisse()

        if caisse:
            time.sleep(1)
            zone = self.carte.garde_mangers["G7"]
            self.approche_garde_manger(zone)
            self.depot_set_caisse(frame_provider=frame_provider)
            time.sleep(1)
        else:
            self.robot.logs.log("WARN", "R6 vide ou ArUco introuvable -> Skip vers PHASE 2")

        time.sleep(1)

