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
    Set position : SP x y angle ? 

Pour recevoir position 
    POS x y angle 
"""

import serial
import threading
import time
import re

from core.affinite_cpu import fixer_affinite_cpu

class Mecanum:
    def __init__(self, logs, port=None, baudrate=115200, x_init=0.0, y_init=0.0, angle_init_deg=0.0):
        self.logs = logs
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        self._serial_lock = threading.Lock()
        self._stop_event = threading.Event()
        self.mouvement_termine = threading.Event()
        self.mouvement_pince_termine = threading.Event()

        self._thread = None
        self.running = False

        self.x = float(x_init)
        self.y = float(y_init)
        self.angle_deg = float(angle_init_deg)
        # Last motion command (used to resume after Lidar stop)
        self._last_motion_cmd = None  # e.g. ("AC", x, y)
        self._paused_by_lidar = False
        self._resume_lock = threading.Lock()

    def connecter(self, port=None):
        if port is not None:
            self.port = port

        if not self.port:
            self.logs.log("ERR", "Aucun port série fourni pour le Mecanum.")
            return False

        self.fermer()

        try:
            self.serial_port = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0.2,
                write_timeout=1,
            )
        except Exception as exc:
            self.serial_port = None
            self.logs.log("ERR", f"Impossible d'ouvrir le port série {self.port} : {exc}")
            return False

        self._stop_event.clear()
        self.running = True
        self._thread = threading.Thread(target=self.lire_en_continu, daemon=True)
        self._thread.start()
        self.logs.log("STM32", f"CONNECT port={self.port} baudrate={self.baudrate}")
        return True


    def lire_en_continu(self):
        fixer_affinite_cpu(0, logs=self.logs, nom_thread="serial_stm32")
        while self.running and not self._stop_event.is_set():
            try:
                serial_port = self.serial_port
                if not serial_port or not serial_port.is_open:
                    time.sleep(0.05)
                    continue

                raw = serial_port.readline()
                if not raw:
                    time.sleep(0.01)
                    continue

                try:
                    line = raw.decode("utf-8", errors="ignore").strip()
                except Exception:
                    line = ""

                if line:
                    self.logs.log("STM32", line)
                    normalized = self._normaliser_ligne_uart(line)

                    if normalized.startswith("pos"):
                        self.traiter_position(line)
                    elif "mouv" in normalized and "ok" in normalized and "pince" not in normalized:
                        self.mouvement_termine.set()
                        self.logs.log("STM32", "Mouv Ok reconnu")
                    elif "mouv" in normalized and "pince" in normalized and "ok" in normalized:
                        self.mouvement_pince_termine.set()
                        self.logs.log("STM32", "Mouv Pince Ok reconnu")
                    elif normalized == "prochaine caisse":
                        self.prochaine_caisse = True
                    elif normalized.startswith("mouv"):
                        self.logs.log("WARN", f"Réponse Mouv non reconnue: {line!r}")

            except Exception as exc:
                self.logs.log("ERR", f"Lecture série : {exc}")
                time.sleep(0.01)


    def traiter_position(self, ligne):
        try:
            _, x, y, angle = ligne.split()
            self.x = float(x)
            self.y = float(y)
            self.angle_deg = float(angle) - 90
        except Exception as e:
            self.logs.log("ERR", f"Parse position : {e}")

    @staticmethod
    def _normaliser_ligne_uart(line):
        cleaned = re.sub(r"[^0-9A-Za-zÀ-ÿ]+", " ", line)
        return " ".join(cleaned.split()).casefold()

    def send_raw(self, line):
        serial_port = self.serial_port
        if not serial_port or not serial_port.is_open:
            return False
        data = (line + "\n").encode("utf-8")
        with self._serial_lock:
            serial_port.write(data)
        return True

    def avancer(self, distance):
        self.mouvement_termine.clear()
        try: 
            self._last_motion_cmd = ("A", float(distance))
        except Exception:
            self._last_motion_cmd = ("A", distance)

        self._paused_by_lidar = False
        self.send_raw(f"A {distance}")

    
    def reculer(self, distance):
        self.mouvement_termine.clear()
        self._paused_by_lidar = False
        self.send_raw(f"R {distance}")

    def droite(self, distance):
        self.mouvement_termine.clear()
        self._paused_by_lidar = False
        self.send_raw(f"G {distance}")

    def gauche(self, distance):
        self.mouvement_termine.clear()
        self._paused_by_lidar = False
        self.send_raw(f"D {distance}")

    def diagonale_gauche(self, distance):
        self.mouvement_termine.clear()
        self._paused_by_lidar = False
        self.send_raw(f"DG {distance}")

    def diagonale_droite(self, distance):
        self.mouvement_termine.clear()
        self._paused_by_lidar = False
        self.send_raw(f"DD {distance}")

    def rotation_gauche(self, angle):
        self.mouvement_termine.clear()
        self._paused_by_lidar = False
        self.send_raw(f"RH {angle}")

    def rotation_droite(self, angle):
        self.mouvement_termine.clear()
        self._paused_by_lidar = False
        self.send_raw(f"RAH {angle}")

    def aller_a_coord(self, x, y, attendre=True, timeout=20):
        self.mouvement_termine.clear()
        # Remember last motion command so we can resume after obstacle
        try:
            self._last_motion_cmd = ("AC", float(x), float(y))
        except Exception:
            self._last_motion_cmd = ("AC", x, y)

        self.logs.log("STM32", f"AC x={x} y={y}")
        self.send_raw(f"AC {x} {y}")


    def resume_last_motion(self):
        """Attempt to resume the last stored motion command.
        Supports all movement types: AC, A, R, G, D, DG, DD, RH, RAH, TVA
        Returns True if a resume command was sent, False otherwise.
        """
        with self._resume_lock:
            if not self._last_motion_cmd:
                return False
            
            cmd = self._last_motion_cmd
            cmd_type = cmd[0]
            sent = False
            
            try:
                if cmd_type == "AC" and len(cmd) == 3:
                    # Aller à coordonnée
                    x, y = cmd[1], cmd[2]
                    self.mouvement_termine.clear()
                    self.logs.log("STM32", f"RESUME AC x={x} y={y}")
                    sent = self.send_raw(f"AC {x} {y}")
                
                elif cmd_type in ["A", "R", "G", "D", "DG", "DD"] and len(cmd) == 2:
                    # Mouvement de distance (avancer, reculer, latéral, diagonal)
                    distance = cmd[1]
                    self.logs.log("STM32", f"RESUME {cmd_type} {distance}")
                    sent = self.send_raw(f"{cmd_type} {distance}")
                
                elif cmd_type in ["RH", "RAH", "TVA"] and len(cmd) == 2:
                    # Mouvement de rotation/angle
                    angle = cmd[1]
                    self.mouvement_termine.clear()
                    self.logs.log("STM32", f"RESUME {cmd_type} {angle}")
                    sent = self.send_raw(f"{cmd_type} {angle}")
            
            except Exception as exc:
                self.logs.log("ERR", f"Erreur resume_last_motion: {exc}")
                sent = False
            
            if sent:
                self._paused_by_lidar = False
            return sent

    def tourner_vers_angle(self, angle, attendre=True, timeout=10):
        self.mouvement_termine.clear()
        try:
            self._last_motion_cmd = ("TVA", float(angle))
        except Exception:
            self._last_motion_cmd = ("TVA", angle)
        self._paused_by_lidar = False
        self.logs.log("STM32", f"TVA angle={angle}")
        self.send_raw(f"TVA {angle}")
        if attendre:
            ok = self.mouvement_termine.wait(timeout=timeout)
            if not ok:
                self.logs.log("ERR", f"Timeout rotation TVA ({angle})")
            return ok
        return True

    def aller_a_coord_angle(self, x, y, angle):
        self.aller_a_coord(x, y)
        self.tourner_vers_angle(angle)

    def stop(self):
        self.send_raw("STOP")

    def set_position(self, x ,y ,angle):
        self.send_raw(f"SP {x} {y} {angle}")
        self.logs.log(f"INFO", "Nouvelle position : {x} {y} {angle}")

    def fermer(self):
        self.running = False
        self._stop_event.set()
        
        # Attendre la fin du thread de lecture
        if self._thread:
            try:
                self._thread.join(timeout=2.0)
            except Exception:
                pass
            self._thread = None
        
        # Fermeture du port série
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception as exc:
                self.logs.log("ERR", f"Erreur fermeture port série: {exc}")
            finally:
                self.serial_port = None
        
        self.logs.log("STM32", "Mecanum fermé")
