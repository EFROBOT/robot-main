import time
import math
import threading

class Strategy:
    def __init__(self, carte, robot):
        self.carte = carte
        self.robot = robot
        self.frame_provider = None  # injecté par AffichageWeb après ouverture caméra
        
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
    # Tri couleurs

    def tri_couleur(self, frame_provider, stop_event, resultat):
        votes = {}  

        while not stop_event.is_set():
            frame = frame_provider()
            if frame is None:
                time.sleep(0.02)
                continue
            try:
                caisses = self.robot.camera.aruco.detect_markers(frame)
            except Exception:
                time.sleep(0.02)
                continue

            caisses.sort(key=lambda c: getattr(c, "distance", 9999))
            for i, caisse in enumerate(caisses[:4], start=1):
                couleur = str(getattr(caisse, "equipe", "")).strip().lower()
                if couleur in ("bleu", "blue"):
                    couleur = "bleu"
                elif couleur in ("jaune", "yellow"):
                    couleur = "jaune"
                else:
                    continue
                if i not in votes:
                    votes[i] = {"bleu": 0, "jaune": 0}
                votes[i][couleur] += 1

            time.sleep(0.02)

        ordre = []
        for pos in range(1, 5):
            if pos in votes:
                couleur = max(votes[pos], key=votes[pos].get)
                ordre.append(couleur)

        for couleur in ("bleu", "jaune"):
            while ordre.count(couleur) < 2 and len(ordre) < 4:
                ordre.append(couleur)

        resultat["ordre"] = ordre[:4]
        self.robot.logs.log("INFO", f"Tri couleurs terminé: {resultat['ordre']}")

    # ------------------------------------------------------------------
    # Calibration ArUco

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

            # Condition d'arret
            distance_arret = 55
            if distance <= distance_arret and abs(lateral) <= 3:
                self.robot.logs.log("INFO", f"ArUco → Cible atteinte ! Dist: {distance:.1f}cm")
                self.robot.logs.log("INFO", f"ArUco → ALIGNÉ ✓ Ordre des blocs: {meilleur_ordre_blocs}")
                return True, meilleur_ordre_blocs

            # Correct angle
            angle_cible = -90.0 
            erreur_angle = angle - angle_cible
            erreur_angle = (erreur_angle + 45) % 90 - 45
            if abs(erreur_angle) > 3:
                if erreur_angle > 0:
                    self.robot.rotation_droite(int(abs(erreur_angle)) + 3)
                else:
                    self.robot.rotation_gauche(int(abs(erreur_angle)) + 3)
                continue

            # Correct lateral
            dist_cmd = round(abs(lateral))
            if dist_cmd > 5: 
                if lateral > 0:
                    self.robot.droite(float(dist_cmd * 0.6))
                else:
                    self.robot.gauche(float(dist_cmd * 0.6))
                #time.sleep(0.5) 
                continue 
            
            # Correct distance
            hyp = distance - 10
            if hyp > 2: 
                if hyp > 29:
                    x = float(round(math.sqrt((hyp * hyp) - (29 * 29))))
                else:
                    x = float(round(hyp))
                step = min(x, 10.0)
                self.robot.logs.log("INFO", f"Avance par palier: {step}")
                self.robot.avancer(step)
                #time.sleep(0.5)
                continue

            self.robot.logs.log("INFO", "ArUco → ALIGNÉ ✓")
            return True, meilleur_ordre_blocs

        self.robot.logs.log("WARN", "aligner_sur_aruco: timeout.")
        return False
    
    # ------------------------------------------------------------------
    # aligner et recuperer caisses

    def aligner_et_recuperer_caisses(self, frame_provider=None, timeout_alignement_s=15.0):
        self.robot.fermer_porte()
        self.robot.set_distance_lidar(10)

        frame_provider = frame_provider or self.frame_provider

        if frame_provider is None:
            cam = self.robot.camera
            if cam.cap is None or not cam.cap.isOpened():
                if not cam.load_calibration():
                    cam.use_default_calibration()
                cam.open()
            def frame_provider():
                ret, frame = cam.read()
                return frame if ret else None
            
        stop_tri = threading.Event()
        resultat_tri = {"ordre": []}

        thread_tri = threading.Thread(
            target=self.tri_couleur,
            args=(frame_provider, stop_tri, resultat_tri),
            daemon=True,
        )
        thread_tri.start()

        self.aligner_sur_aruco(timeout_s=timeout_alignement_s, frame_provider=frame_provider)
        self.robot.logs.log("INFO", "Aprés fonction")
        
        stop_tri.set()
        thread_tri.join(timeout=1.0)

        ordre = resultat_tri["ordre"]
        if not ordre:
            self.robot.logs.log("WARN", "Pas d'ordre couleurs détecté.")
            return False
        
        if self.robot.team == "yellow":
            equipe = "jaune"
        else:
            equipe = "bleu"
        
        self.robot.logs.log("WARN", f"Odre {len(ordre)}")
        
        for i, couleur_caisse in enumerate(ordre):
            self.robot.logs.log("WARN", "Caisses")
        
            if couleur_caisse == equipe:
                rotation = 1
            else:
                rotation = 0
            self.robot.logs.log("WARN", f"Team : {equipe}")
            self.robot.logs.log("WARN", f"Couleur_caisses : {couleur_caisse}")
            self.robot.logs.log("WARN", f"Rotation : {rotation}")
            ok = self.robot.pince_recuperer_et_stocker(rotation)
            self.robot.logs.log("RPi", f"Pince_RecupererEtStocker rotation={rotation} -> {'OK' if ok else 'ECHEC'}")
            #self.robot.leds.clignoter((0,255,0), vitesse=0.5)
            #self.robot.leds.eteindre()
            if i < len(ordre) -1:
              self.robot.avancer(10) # to check
        
        #ok = self.robot.pince_recuperer_et_stocker(0)
        #self.robot.logs.log("RPi", f"Pince_RecupererEtStocker rotation={rotation} -> {'OK' if ok else 'ECHEC'}")
        self.robot.set_distance_lidar(45)

    # ------------------------------------------------------------------
    # Top level

    # validé
    def homologation(self):
                 
        self.robot.logs.log("INFO", f"Le robot se dirige vers la zone ")

        if self.robot.team=="yellow":
            self.robot.avancer(85)
            time.sleep(5)
            self.robot.reculer(85)
            time.sleep(5)
        else :
            self.robot.avancer(85)
            time.sleep(5)
            self.robot.reculer(85)
            time.sleep(5)
                
        time.sleep(5)

    # validé
    def serie_1(self):
        self.debut_match = time.time()
        
        self.robot.logs.log("INFO", f"Lancement de la stratégie de derniere serie")

        if self.robot.team == "yellow":
            self.robot.avancer(85)
            self.robot.gauche(35)
            self.robot.diagonale_gauche(55)
            self.robot.rotation_gauche(70)
            self.aligner_et_recuperer_caisses()
            self.robot.reculer(10)
            time.sleep(0.5)
            self.robot.ouvrir_porte()
            time.sleep(1)
            self.robot.gauche(45)
            time.sleep(1)
            self.robot.reculer(90)
            time.sleep(1)
            self.robot.gauche(70)
        else:
            self.robot.avancer(85)
            self.robot.droite(35)
            self.robot.diagonale_droite(55)
            self.robot.rotation_droite(70)
            self.aligner_et_recuperer_caisses()
            self.robot.reculer(10)
            time.sleep(0.5)
            self.robot.ouvrir_porte()
            time.sleep(1)
            self.robot.droite(45)
            time.sleep(1)
            self.robot.reculer(90)
            time.sleep(1)
            self.robot.droite(70)

            
    def serie(self):
        self.debut_match = time.time()
        
        self.robot.logs.log("INFO", f"Lancement de la stratégie de derniere serie")

        if self.robot.team == "yellow":
            #  1
            self.robot.avancer(85)
            self.robot.gauche(25)
            self.robot.diagonale_gauche(70)
            self.robot.rotation_gauche(70)
            self.aligner_et_recuperer_caisses()
            self.robot.reculer(10)
            time.sleep(0.5)
            self.robot.ouvrir_porte()
            time.sleep(1)
            self.robot.gauche(45)
            time.sleep(1)
            self.robot.reculer(90)
            time.sleep(1)
            self.robot.gauche(70)

    def serie_mael(self):
        self.debut_match = time.time()
        
        self.robot.logs.log("INFO", f"Lancement de la stratégie de derniere serie")

        if self.robot.team == "yellow":
            #  1
            self.robot.avancer(20)
            self.robot.diagonale_gauche(130)
            self.robot.rotation_gauche(70)
            self.aligner_et_recuperer_caisses()
