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


class Mecanum:
    def __init__(self, logs, port=None, baudrate=115200, x_init=0.0, y_init=0.0, angle_init_deg=0.0):
        self.logs = logs
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        self._serial_lock = threading.Lock()
        self._stop_event = threading.Event()
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
                    continue

                try:
                    line = raw.decode("utf-8", errors="ignore").strip()
                except Exception:
                    line = ""

                if line:
                    self.logs.log("STM32", line)
            except Exception as exc:
                self.logs.log("ERR", f"Lecture série : {exc}")
            time.sleep(0.01)

    def send_raw(self, line):
        serial_port = self.serial_port
        if not serial_port or not serial_port.is_open:
            return False
        data = (line + "\n").encode("utf-8")
        with self._serial_lock:
            serial_port.write(data)
        return True

    def move(self, vx, vy, omega):
        serial_port = self.serial_port
        if not serial_port or not serial_port.is_open:
            self.logs.log("STM32", f"CMD wheels vx={vx:.2f} vy={vy:.2f} omega={omega:.2f}")
            return
        self.send_raw(f"{vx:.2f},{vy:.2f},{omega:.2f}")

    def avancer(self, distance):
        self.send_raw(f"A {distance}")

    def reculer(self, distance):
        self.send_raw(f"R {distance}")

    def gauche(self, distance):
        self.send_raw(f"G {distance}")

    def droite(self, distance):
        self.send_raw(f"D {distance}")

    def diagonale_gauche(self, distance):
        self.send_raw(f"DG {distance}")

    def diagonale_droite(self, distance):
        self.send_raw(f"DD {distance}")

    def tourner_vers_angle(self, angle):
        self.send_raw(f"TVA {angle}")

    def rotation_gauche(self, angle):
        self.send_raw(f"RH {angle}")

    def rotation_droite(self, angle):
        self.send_raw(f"RAH {angle}")

    def aller_a_coord(self, x, y):
        self.logs.log("STM32", f"CMD AC x={x} y={y}")
        self.send_raw(f"AC {x} {y}")

    def stop(self):
        self.send_raw("STOP")

    def ouvrir_pince(self):
        self.logs.log("RPi", "Pince ouverte")

    def fermer_pince(self):
        self.logs.log("RPi", "Pince fermée")

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
