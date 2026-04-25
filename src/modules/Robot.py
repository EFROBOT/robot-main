"""
Etat robot 
Instruction de deplacement en fonction de la strategie --> Communication avec le STM32 :
    Aller a une coord precise : AC x y 
    Tourner vers angle : TVA angle 
    Avancer : A distance
    Reculer : R distance
    Gauche : G distance
    Droite : D distance
    Rotation horaire : RH angle
    Rotation anti horaire : RAH angle
    Diagonale gauche : DG distance
    Diagonale droite : DD distance
"""

import serial
import threading
import time
from .AffichageWeb import log

class Robot:
    def __init__(self, port="/dev/ttyACM0", baudrate=115200, x_init=0.0, y_init=0.0, angle_init_deg=0.0):
        self.x = float(x_init)
        self.y = float(y_init)
        self.angle_deg = float(angle_init_deg)
        self.inventaire = []
        
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self._thread = None
        self.running = False

    def connecter(self):
        self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
        self.running = True
        self._thread = threading.Thread(target=self.lire_en_continu, daemon=True)
        self._thread.start()

    def lire_en_continu(self):
        while self.running:
            try:
                if self.serial.in_waiting > 0:
                    ligne = self.serial.readline().decode("utf-8").strip()
                    log("STM32", ligne)
                    if ligne.startswith("POS"):
                        self.traiter_position(ligne)
            except Exception as e:
                log("ERR", f"Lecture série : {e}")
            time.sleep(0.01)

    def traiter_position(self, ligne):
        try:
            _, x, y, angle = ligne.split()
            self.x = float(x)
            self.y = float(y)
            self.angle_deg = float(angle)
        except Exception as e:
            log("ERR", f"Parse position : {e}")

    def envoyer_commande(self, commande):
        if self.serial and self.serial.is_open:
            try:
                self.serial.write(f"{commande}\n".encode("utf-8"))
                log("RPI", f"Envoi : {commande}")
            except Exception as e:
                log("ERR", f"Erreur envoi : {e}")
        else:
            log("ERR", f"Impossible d'envoyer '{commande}', port fermé.")

    #-------------------------------------------------------------------------------------------
    # Etat robot

    def get_position(self):
        return (self.x, self.y, self.angle_deg)

    def nb_caisses(self):
        return len(self.inventaire)

    def ajouter_caisse(self, caisse):
        self.inventaire.append(caisse)

    def retirer_caisse(self):
        if self.inventaire:
            return self.inventaire.pop(0)
        return None
    
    #-------------------------------------------------------------------------------------------
    # Deplacement robot

    def aller_a_coord(self, x, y):
        self.envoyer_commande(f"AC {x} {y}")

    def avancer(self, distance):
        self.envoyer_commande(f"A {distance}")

    def reculer(self, distance):
        self.envoyer_commande(f"R {distance}")

    def gauche(self, distance):
        self.envoyer_commande(f"G {distance}")

    def droite(self, distance):
        self.envoyer_commande(f"D {distance}")

    def diagonale_gauche(self, distance):
        self.envoyer_commande(f"DG {distance}")
    
    def diagonale_droite(self, distance):
        self.envoyer_commande(f"DD {distance}")

    # Angle
    def tourner_vers_angle(self, angle):
        self.envoyer_commande(f"TVA {angle}")

    def rotation_horaire(self, angle):
        self.envoyer_commande(f"RH {angle}")

    def rotation_anti_horaire(self, angle):
        self.envoyer_commande(f"RAH {angle}")

    def stop(self):
        self.envoyer_commande("STOP")

    #-------------------------------------------------------------------------------------------
    # Pince robot

    def ouvrir_pince(self):
        pass

    def fermer_pince(self):
        pass


    def fermer(self):
        self.running = False
        if self._thread:
            self._thread.join()
        if self.serial and self.serial.is_open:
            self.serial.close()


