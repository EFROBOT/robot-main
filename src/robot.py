"""Module principal de gestion du robot."""

import cv2
import numpy as np

from hardware.camera import Camera
from modules.Aruco import Aruco
from modules.MecaNum import MecaNum


class Robot:
    def __init__(self, camera_id: int = 0):
        """Robot.py"""
        self.camera = Camera(camera_id=camera_id)
        self.mecanum = MecaNum()
        self.aruco_detector = None
        self.running = False

    def setup(self):
        """ Setup la caméra et Aruco"""
        if not self.camera.load_calibration():
            print("Aucune calibration trouvée, Paramètres par défaut.")
            self.camera.use_default_calibration()
        
        if not self.camera.open():
            raise RuntimeError(f"Impossible d'ouvrir la caméra {self.camera.camera_id}")

        camera_matrix, dist_coeffs = self.camera.get_calibration()
        self.aruco_detector = Aruco(
            marker_size=0.040, 
            camera_matrix=camera_matrix, 
            dist_coeffs=dist_coeffs
        )

    def run(self):
        """ Main loop """
        self.running = True

        try:
            while self.running:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    print("Erreur de lecture caméra.")
                    break

                markers = []
                if self.aruco_detector is not None:
                    markers = self.aruco_detector.detect_markers(frame)
                    self.aruco_detector.draw_marker(frame, markers)

                if markers:
                    target_marker = markers[0]
                    self.mecanum.align_to_marker(target_marker)
                else:
                    self.mecanum.move(0, 0, 0)

                cv2.imshow("Robot", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.running = False

        finally:
            self.stop()
    
    def stop(self):
        """ Stop the robot """
        self.running = False
        self.mecanum.move(0, 0, 0)
        del self.mecanum
        self.camera.release()
        cv2.destroyAllWindows()
    
    def __del__(self):
        self.stop()
