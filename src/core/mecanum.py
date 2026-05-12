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
                    if line.startswith("POS"):
                        self.traiter_position(line)
                    elif line == "Mouv Ok":
                        self.mouvement_termine.set()
                    elif line == "Mouv Pince Ok":
                        self.mouvement_pince_termine.set()

            except Exception as exc:
                self.logs.log("ERR", f"Lecture série : {exc}")
                time.sleep(0.01)


    def traiter_position(self, ligne):
        try:
            _, x, y, angle = ligne.split()
            self.x = float(x)
            self.y = float(y)
            self.angle_deg = float(angle)
        except Exception as e:
            self.logs.log("ERR", f"Parse position : {e}")

    def send_raw(self, line):
        serial_port = self.serial_port
        if not serial_port or not serial_port.is_open:
            return False
        data = (line + "\n").encode("utf-8")
        with self._serial_lock:
            serial_port.write(data)
        return True


    def avancer(self, distance):
        self.send_raw(f"A {distance}")

    def reculer(self, distance):
        self.send_raw(f"R {distance}")

    def droite(self, distance):
        self.send_raw(f"G {distance}")

    def gauche(self, distance):
        self.send_raw(f"D {distance}")

    def diagonale_gauche(self, distance):
        self.send_raw(f"DG {distance}")

    def diagonale_droite(self, distance):
        self.send_raw(f"DD {distance}")

    def rotation_gauche(self, angle):
        self.send_raw(f"RH {angle}")

    def rotation_droite(self, angle):
        self.send_raw(f"RAH {angle}")

    def aller_a_coord(self, x, y, attendre=True, timeout=20):
        self.mouvement_termine.clear()
        self.logs.log("STM32", f"AC x={x} y={y}")
        self.send_raw(f"AC {x} {y}")
        if attendre:
            ok = self.mouvement_termine.wait(timeout=timeout)
            if not ok:
                self.logs.log("ERR", f"Timeout mouvement AC ({x},{y})")
            return ok
        return True

    def tourner_vers_angle(self, angle, attendre=True, timeout=10):
        self.mouvement_termine.clear()
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
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None
