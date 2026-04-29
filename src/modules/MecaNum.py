"""Module de contrôle du robot Mecanum."""

import math
import serial

class MecaNum:
    def __init__(self):
        try:
            self.serial_port = serial.Serial("COM5", baudrate=115200, timeout=1)
        except:
            self.serial_port = None


    def move(self, vx: float, vy: float, omega: float):
        """Envoi par usb au stm32 les info de position et de rotation"""
        if self.serial_port and self.serial_port.is_open:
            try:
                cmd = f"{vx:.2f},{vy:.2f},{omega:.2f}\n"
                self.serial_port.write(cmd.encode())
                
                while self.serial_port.in_waiting > 0:
                    response = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if response:
                        print(f"[STM32] {response}")
            except Exception as e:
                print(f"Erreur Série: {e}")
        
        # print(f"vx: {vx:.2f}, vy: {vy:.2f}, omega: {omega:.2f}")

    def align_to_marker(self, marker):
        """Aligne le robot sur un marqueur + aligner par rapport à sa longueur"""


    def __del__(self):
        if self.serial_port:
            self.serial_port.close()
