import time
import math
import threading
from core.alignement_tri_caisses import AlignementTriCaisses
from core.recuperation_caisses import RecuperationCaisses

class Strategy:
    def __init__(self, carte, robot):
        self.carte = carte
        self.robot = robot
        self.frame_provider = None  # injecté par AffichageWeb après ouverture caméra
        # Paramètres d'alignement (faciles à ajuster)
        self.seuil_align_distance_cm = 53.0
        self.seuil_align_lateral_cm = 3.0
        self.seuil_align_angle_deg = 4.0

    def strategy_derniere_serie(self, frame_provider):
        #self.debut_match = time.time()
        
        self.robot.securiser_caisses()
        self.robot.logs.log("INFO", f"Lancement de la stratégie de derniere serie")
        
        #Séquence  de déplacement ok 
        self.robot.avancer(30)
        self.aligner_et_recuperer_caisses()
        time.sleep(0.5)
        self.robot.logs.log("INFO", f"ffffffff")
        self.avancer(10)
        self.robot.rotation_gauche(180)
        time.sleep(0.5)
        self.robot.lacher_caisses()
        time.sleep(2)
        self.robot.avancer(60)
        time.sleep(2)

        
        
        """self.robot.rotation_droite(100)
        time.sleep(1)
        self.robot.avancer(25)
        time.sleep(1)
        self.aligner_et_recuperer_caisses()
        time.sleep(1)"""
        # Faire une sequence de plus à chaque fois pour valider entouré de time.sleep() 
        while True: ## evite de relancé le code à lafin
            x= "Coucou"
        #Suite de la séquence à valider 
        """
            #-------------
            #  2S
            #-------------
            self.robot.reculer(20)
            time.sleep(1)
            # fonction de déchargement
            time.sleep(1)
            self.robot.avancer(10)
            time.sleep(1)
            #-------------
            #  3
            #-------------
            self.robot.rotation_gauche(90) # même problème
            time.sleep(1)
            #-------------
            #  4
            #-------------
            self.robot.avancer(25)
            time.sleep(1)
            self.robot.rotation_gauche(90)
            time.sleep(1)
            self.robot.avancer(55)
            time.sleep(1)
            self.robot.droite(15)
            time.sleep(1)
            self.robot.avancer(35)
            time.sleep(1)
            self.robot.rotation_gauche(90)
            time.sleep(1)
            self.robot.avancer(30)
            time.sleep(1)
            current_time = time.time()
            if (current_time - self.debut_match) < 40 :
                #-------------
                #  5
                #-------------
                # fonction alignement & prendre set caisses
                time.sleep(1)
                self.robot.reculer(20) 
                time.sleep(1)
                # fonction de déchargement
                time.sleep(1)
                #-------------
                #  6
                #-------------
                self.robot.avancer(90)
            else :
		#-----------------
                #  skip vers la 6
                #-----------------
                self.robot.avancer(65)
                time.sleep(1)
                self.robot.droite(20)
                time.sleep(1)
                self.robot.avancer(20)
        else:
            #-------------
            #  1
            #-------------
            self.robot.avancer(105)
            time.sleep(1)
            self.robot.rotation_gauche(90) # la fonction fait l'inverse (rotation à droite)
            time.sleep(1)
            self.robot.avancer(50)
            time.sleep(1)
            # fonction alignement & prendre set caisses
            time.sleep(1)
            #-------------
            #  2
            #-------------
            self.robot.reculer(20)
            time.sleep(1)
            # fonction de déchargement
            time.sleep(1)
            self.robot.avancer(10)
            time.sleep(1)
            #-------------
            #  3
            #-------------
            self.robot.rotation_droite(90) # même problème
            time.sleep(1)
            #-------------
            #  4
        """
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

    def aligner_sur_aruco(self, timeout_s=50.0, frame_provider=None):
        deadline = time.time() + timeout_s
        meilleur_ordre_blocs = {}

        while time.time() < deadline:
            if frame_provider is not None:
                frame = frame_provider()
            else:
                frame = self.robot.camera.get_latest_frame()
                if frame is None:
                    ret, frame = self.robot.camera.read()
                    if not ret:
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
            distance_arret = self.seuil_align_distance_cm
            lateral_max = self.seuil_align_lateral_cm
            if distance <= distance_arret and abs(lateral) <= lateral_max:
                self.robot.logs.log("INFO", f"ArUco → Cible atteinte ! Dist: {distance:.1f}cm")
                self.robot.logs.log("INFO", f"ArUco → ALIGNÉ ✓ Ordre des blocs: {meilleur_ordre_blocs}")
                return True, meilleur_ordre_blocs

            angle_cible = -90.0 
            erreur_angle = angle - angle_cible
            erreur_angle = (erreur_angle + 45) % 90 - 45
            
            if abs(erreur_angle) > self.seuil_align_angle_deg:
                if erreur_angle > 0:
                    self.robot.rotation_gauche(int(abs(erreur_angle)) + 3)
                else:
                    self.robot.rotation_droite(int(abs(erreur_angle)) + 3)
                continue

            dist_cmd = round(abs(lateral))
            if dist_cmd > 5: 
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
                frame = self.robot.camera.get_latest_frame()
                if frame is None:
                    ret, frame = self.robot.camera.read()
                    if not ret:
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
        self.robot.logs.log("INFO", "Démarrage")
        self.robot.securiser_caisses()
        
        self.robot.logs.log("INFO", "Ciblage")
        result = self.aligner_sur_aruco(timeout_s=15.0, frame_provider=frame_provider)
        
        if not result:
            self.robot.logs.log("WARN", "Echec")
            return False

        _, ordre_blocs = result
        nb_caisses = len(ordre_blocs)

        self.robot.logs.log("INFO", f"Collecte ordre: {ordre_blocs}")

        for numero_caisse in range(1, nb_caisses + 1):
            if not ordre_blocs:
                self.robot.logs.log("INFO", "Vide")
                break

            couleur_caisse = ordre_blocs.get(1)
            self.robot.logs.log("INFO", f"Prise {numero_caisse} couleur {couleur_caisse}")
            
            if couleur_caisse == team:
                self.robot.recuperer_caisses(1)
            else:
                self.robot.recuperer_caisses(0)


            if numero_caisse == nb_caisses or len(ordre_blocs) <= 1:
                self.robot.logs.log("INFO", "Dernier")
                break

            etat_attendu = {i - 1: ordre_blocs[i] for i in range(2, len(ordre_blocs) + 1) if i in ordre_blocs}
            self.robot.logs.log("INFO", f"Etat attendu: {etat_attendu}")

            self.robot.logs.log("INFO", "Avance")
            self.robot.avancer(7.0)
            
            self.robot.logs.log("INFO", "Ajustement")
            result_lat = self.aligner_sur_aruco_uniquement_lateral(timeout_s=10.0, frame_provider=frame_provider)
            
            if not result_lat:
                self.robot.logs.log("WARN", "Perdu")
                break
                
            _, nouvel_ordre_blocs = result_lat
            self.robot.logs.log("INFO", f"Nouvel ordre vu: {nouvel_ordre_blocs}")

            if nouvel_ordre_blocs == etat_attendu:
                self.robot.logs.log("INFO", "Valide")
            else:
                self.robot.logs.log("WARN", "Desynchro")

            ordre_blocs = nouvel_ordre_blocs

        self.robot.logs.log("INFO", "Termine")
        return True


    def aligner_sur_zone_de_ramassage(self, timeout_s=30.0, frame_provider=None):
        deadline = time.time() + timeout_s
        meilleur_ordre_blocs = {}

        while time.time() < deadline:
            if frame_provider is not None:
                frame = frame_provider()
            else:
                frame = self.robot.camera.get_latest_frame()
                if frame is None:
                    ret, frame = self.robot.camera.read()
                    if not ret:
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


        
    def homologation(self):
        #self.robot.set_position(150, 150, -90)
         
        self.robot.logs.log("INFO", f"Le robot se dirige vers la zone ")

        if self.robot.team=="yellow":
            self.robot.avancer(85)
            time.sleep(5)
            self.robot.reculer(70)
            time.sleep(5)
        else :
            self.robot.avancer(85)
            time.sleep(5)
            self.robot.reculer(70)
            time.sleep(5)
                
        time.sleep(5)

    def aligner_et_recuperer_caisses(self, frame_provider=None, timeout_alignement_s=15.0):
        """Aligne le robot sur les caisses, détecte leur ordre de couleurs, puis les récupère.

        frame_provider : callable retournant une frame BGR, ou None pour ouvrir
                         robot.camera directement (sans dashboard).
        Retourne True si le cycle s'est déroulé sans erreur, False sinon.
        """
        self.robot.logs.log("INFO", "srgreg.")

        if frame_provider is None:
            frame_provider = self.frame_provider

        if frame_provider is None:
            cam = self.robot.camera
            if cam.cap is None or not cam.cap.isOpened():
                if not cam.load_calibration():
                    cam.use_default_calibration()
                cam.open()

            def _lire_camera():
                ret, frame = cam.read()
                return frame if ret else None

            frame_provider = _lire_camera

        _fp_sauvegarde = self.frame_provider
        self.frame_provider = frame_provider
        try:
            aligneur = AlignementTriCaisses(strategy=self, logs=self.robot.logs)
            resultat = aligneur.lancer(timeout_alignement_s=timeout_alignement_s)
        finally:
            self.frame_provider = _fp_sauvegarde

        ordre = resultat.get("ordre_couleurs", [])
        if not ordre:
            self.robot.logs.log("WARN", "aligner_et_recuperer_caisses: pas d'ordre couleurs détecté.")
            return False

        self.robot.logs.log("RPi", f"Ordre couleurs détecté: {ordre}")
        recuperation = RecuperationCaisses(robot=self.robot, logs=self.robot.logs)
        return recuperation.executer_cycle(ordre)

