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

import math
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
        # Last motion command (used to resume after Lidar stop)
        self._last_motion_cmd = None  # e.g. ("AC", x, y)
        self._last_motion_resumable = False
        self._motion_start_pose = None
        self._motion_total_distance = None
        self._motion_direction_offset_deg = None
        self._motion_target = None
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
                    elif line == "Prochaine caisse":
                        self.prochaine_caisse = True

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

    def send_raw(self, line):
        serial_port = self.serial_port
        if not serial_port or not serial_port.is_open:
            return False
        data = (line + "\n").encode("utf-8")
        with self._serial_lock:
            serial_port.write(data)
        return True

    def _start_motion_tracking(self, cmd_type, value, resumable, direction_offset_deg=None, target=None):
        self._motion_start_pose = (self.x, self.y, self.angle_deg)
        self._motion_total_distance = float(value) if value is not None else None
        self._motion_direction_offset_deg = direction_offset_deg
        self._motion_target = target
        self._last_motion_cmd = (cmd_type, value) if target is None else (cmd_type, target[0], target[1])
        self._last_motion_resumable = resumable

    def _estimate_remaining_linear_distance(self):
        if self._motion_start_pose is None or self._last_motion_cmd is None or self._motion_total_distance is None:
            return None

        start_x, start_y, start_angle_deg = self._motion_start_pose
        current_dx = self.x - start_x
        current_dy = self.y - start_y

        if self._motion_direction_offset_deg is None:
            return None

        move_angle_deg = start_angle_deg + float(self._motion_direction_offset_deg)

        move_angle_rad = math.radians(move_angle_deg)
        axis_x = math.cos(move_angle_rad)
        axis_y = math.sin(move_angle_rad)
        progress = (current_dx * axis_x) + (current_dy * axis_y)
        remaining = self._motion_total_distance - progress
        if remaining <= 0.0:
            return 0.0
        return remaining


    def avancer(self, distance):
        self.mouvement_termine.clear()
        try:
            distance_value = float(distance)
        except Exception:
            distance_value = distance
        self._start_motion_tracking("A", distance_value, True, direction_offset_deg=0.0)
        self._paused_by_lidar = False
        self.send_raw(f"A {distance}")

    def reculer(self, distance):
        self.mouvement_termine.clear()
        try:
            distance_value = float(distance)
        except Exception:
            distance_value = distance
        self._start_motion_tracking("R", distance_value, True, direction_offset_deg=180.0)
        self._paused_by_lidar = False
        self.send_raw(f"R {distance}")

    def droite(self, distance):
        self.mouvement_termine.clear()
        try:
            distance_value = float(distance)
        except Exception:
            distance_value = distance
        self._start_motion_tracking("G", distance_value, True, direction_offset_deg=-90.0)
        self._paused_by_lidar = False
        self.send_raw(f"G {distance}")

    def gauche(self, distance):
        self.mouvement_termine.clear()
        try:
            distance_value = float(distance)
        except Exception:
            distance_value = distance
        self._start_motion_tracking("D", distance_value, True, direction_offset_deg=90.0)
        self._paused_by_lidar = False
        self.send_raw(f"D {distance}")

    def diagonale_gauche(self, distance):
        self.mouvement_termine.clear()
        try:
            distance_value = float(distance)
        except Exception:
            distance_value = distance
        self._start_motion_tracking("DG", distance_value, True, direction_offset_deg=45.0)
        self._paused_by_lidar = False
        self.send_raw(f"DG {distance}")

    def diagonale_droite(self, distance):
        self.mouvement_termine.clear()
        try:
            distance_value = float(distance)
        except Exception:
            distance_value = distance
        self._start_motion_tracking("DD", distance_value, True, direction_offset_deg=-45.0)
        self._paused_by_lidar = False
        self.send_raw(f"DD {distance}")

    def rotation_gauche(self, angle):
        self.mouvement_termine.clear()
        try:
            self._last_motion_cmd = ("RH", float(angle))
        except Exception:
            self._last_motion_cmd = ("RH", angle)
        self._motion_start_pose = (self.x, self.y, self.angle_deg)
        self._motion_total_distance = None
        self._motion_direction_offset_deg = None
        self._motion_target = None
        self._last_motion_resumable = True
        self._paused_by_lidar = False
        self.send_raw(f"RH {angle}")

    def rotation_droite(self, angle):
        self.mouvement_termine.clear()
        try:
            self._last_motion_cmd = ("RAH", float(angle))
        except Exception:
            self._last_motion_cmd = ("RAH", angle)
        self._motion_start_pose = (self.x, self.y, self.angle_deg)
        self._motion_total_distance = None
        self._motion_direction_offset_deg = None
        self._motion_target = None
        self._last_motion_resumable = True
        self._paused_by_lidar = False
        self.send_raw(f"RAH {angle}")

    def aller_a_coord(self, x, y, attendre=True, timeout=20):
        self.mouvement_termine.clear()
        # Remember last motion command so we can resume after obstacle
        try:
            x_target = float(x)
            y_target = float(y)
        except Exception:
            x_target = x
            y_target = y
        self._start_motion_tracking("AC", None, True, target=(x_target, y_target))
        self._last_motion_resumable = True
        # If we were paused by lidar, mark that we're attempting a new motion
        self._paused_by_lidar = False
        self.logs.log("STM32", f"AC x={x} y={y}")
        self.send_raw(f"AC {x} {y}")
        if attendre:
            ok = self.mouvement_termine.wait(timeout=timeout)
            if not ok:
                self.logs.log("ERR", f"Timeout mouvement AC ({x},{y})")
            return ok
        return True

    def _motion_to_command(self, cmd):
        cmd_type = cmd[0]
        if cmd_type == "AC" and self._motion_target is not None:
            return f"AC {self._motion_target[0]} {self._motion_target[1]}"
        if cmd_type in {"A", "R", "G", "D", "DG", "DD", "RH", "RAH", "TVA"} and len(cmd) == 2:
            return f"{cmd_type} {cmd[1]}"
        return None

    def _motion_remaining_value(self):
        if self._last_motion_cmd is None:
            return None

        cmd_type = self._last_motion_cmd[0]
        if cmd_type == "AC":
            if self._motion_target is None:
                return None
            start_x, start_y, _ = self._motion_start_pose if self._motion_start_pose is not None else (None, None, None)
            if start_x is None or start_y is None:
                return None
            target_x, target_y = self._motion_target
            total_dx = target_x - start_x
            total_dy = target_y - start_y
            total_distance = math.hypot(total_dx, total_dy)
            if total_distance <= 0.0:
                return 0.0
            axis_x = total_dx / total_distance
            axis_y = total_dy / total_distance
            progress = ((self.x - start_x) * axis_x) + ((self.y - start_y) * axis_y)
            remaining = total_distance - progress
            return 0.0 if remaining <= 0.0 else remaining

        if self._motion_total_distance is None or self._motion_start_pose is None:
            return None

        if cmd_type not in {"A", "R", "G", "D", "DG", "DD"}:
            return None

        return self._estimate_remaining_linear_distance()

    def resume_last_motion(self):
        """Attempt to resume the last stored motion command.
        Replays only the remaining distance when the start pose and current POS
        allow a reliable estimate.
        Returns True if a resume command was sent, False otherwise.
        """
        with self._resume_lock:
            if not self._last_motion_cmd or not self._last_motion_resumable:
                return False

            remaining_value = self._motion_remaining_value()
            if remaining_value is None:
                return False

            cmd_type = self._last_motion_cmd[0]
            if cmd_type in {"A", "R", "G", "D", "DG", "DD"}:
                if remaining_value <= 0.5:
                    return False
                command = f"{cmd_type} {round(remaining_value, 1)}"
            else:
                command = self._motion_to_command(self._last_motion_cmd)
                if command is None:
                    return False

            self.mouvement_termine.clear()
            self.logs.log("STM32", f"RESUME {command}")
            try:
                sent = self.send_raw(command)
            except Exception as exc:
                self.logs.log("ERR", f"Erreur resume_last_motion: {exc}")
                return False

            if sent:
                self._paused_by_lidar = False
            return sent

    def tourner_vers_angle(self, angle, attendre=True, timeout=10):
        self.mouvement_termine.clear()
        try:
            self._last_motion_cmd = ("TVA", float(angle))
        except Exception:
            self._last_motion_cmd = ("TVA", angle)
        self._last_motion_resumable = True
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
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None
