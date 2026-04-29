""""""

import glob
import os
from typing import List, Optional, Tuple

import cv2
import numpy as np


class Camera:
    def __init__(self, camera_id: int = 0, calibration_dir: Optional[str] = None):
        """Initialise la caméra"""
        self.camera_id = camera_id
        self.calibration_dir = calibration_dir or f"./data/calibrations/{camera_id}"
        self.calibration_file = f"{self.calibration_dir}/camera_calibration_{camera_id}.npz"

        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: Optional[np.ndarray] = None

        # Defaut
        self.width = 640
        self.height = 480
        self.fps = 30

    def open(self) -> bool:
        """"""
        backends = [
            (cv2.CAP_MSMF, "MSMF"),
            (cv2.CAP_DSHOW, "DSHOW"),
            (cv2.CAP_ANY, "AUTO"),
        ]

        for backend, name in backends:
            self.cap = cv2.VideoCapture(self.camera_id, backend)

            if self.cap.isOpened():
                self._configure()
                return True

            self.cap.release()

        print(f"Erreur caméra {self.camera_id}\n")
        return False

    @staticmethod
    def list_available_cameras(max_index: int = 10) -> List[int]:
        """Retourne la liste des index caméra disponibles."""
        available = []

        for index in range(max_index + 1):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(index)
            cap.release()

        return available

    def _configure(self):
        """Configure les paramètres de la caméra."""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Lit une frame de la caméra."""
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def load_calibration(self) -> bool:
        """
        Charge les paramètres de calibration depuis le fichier.
        """
        if os.path.exists(self.calibration_file):
            print(f"Chargement de la calibration : {self.calibration_file}")
            with np.load(self.calibration_file) as data:
                self.camera_matrix = data["mtx"]
                self.dist_coeffs = data["dist"]
            return True
        return False

    def use_default_calibration(self):
        """Utilise des paramètres de calibration par défault."""
        print("Défault")
        self.camera_matrix = np.array([[640, 0, 320], [0, 640, 240], [0, 0, 1]], dtype=float)
        self.dist_coeffs = np.zeros((4, 1))

    def get_calibration(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Retourne les paramètres de calibration.
        """
        return self.camera_matrix, self.dist_coeffs

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def capture_images(self, save_dir: Optional[str] = None):
        """
        Capture des images pour la calibration
        """
        save_dir = save_dir or self.calibration_dir

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"Erreur: caméra {self.camera_id}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        existing_files = glob.glob(os.path.join(save_dir, "*.png"))
        count = len(existing_files)

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Erreur: caméra")
                break

            cv2.imshow("Capture", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == 13 or key == 10:
                filename = os.path.join(save_dir, f"calib_{count:03d}.png")
                cv2.imwrite(filename, frame)
                print(f"Sauvegardé : {filename}")
                count += 1
            elif key == ord("q"):
                break
        cap.release()
        cv2.destroyAllWindows()

    def calibrate_charuco(
        self, image_folder: Optional[str] = None, output_file: Optional[str] = None
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        image_folder = image_folder or self.calibration_dir
        output_file = output_file or self.calibration_file

        SQUARES_X = 5
        SQUARES_Y = 4

        SQUARE_LENGTH = 0.050  # 5
        MARKER_LENGTH = 0.040  # 4

        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

        board = cv2.aruco.CharucoBoard(
            (SQUARES_X, SQUARES_Y), SQUARE_LENGTH, MARKER_LENGTH, dictionary
        )
        images_path = os.path.join(image_folder, "*.png")
        images = glob.glob(images_path)

        print(f"{len(images)} images trouvées. Début du traitement...")

        all_charuco_corners = []
        all_charuco_ids = []

        charuco_detector = cv2.aruco.CharucoDetector(board)

        image_size = None

        for fname in images:
            img = cv2.imread(fname)
            if img is None:
                print(f"[!!] {fname} -> Impossible de charger l'image")
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            if image_size is None:
                image_size = gray.shape[::-1]
            # Détecter les bords
            charuco_corners, charuco_ids, marker_corners, marker_ids = charuco_detector.detectBoard(
                gray
            )
            if charuco_corners is not None and len(charuco_corners) > 6:
                all_charuco_corners.append(charuco_corners)
                all_charuco_ids.append(charuco_ids)

        if len(all_charuco_corners) > 0 and image_size is not None:
            print("\nCalibration ...")

            all_obj_points = []
            all_img_points = []
            board_corners = board.getChessboardCorners()

            for i in range(len(all_charuco_corners)):
                if all_charuco_ids[i] is not None and len(all_charuco_ids[i]) > 0:
                    all_obj_points.append(board_corners[all_charuco_ids[i].flatten()])
                    all_img_points.append(all_charuco_corners[i])

            camera_matrix = np.eye(3, dtype=np.float32)
            dist_coeffs = np.zeros((5, 1), dtype=np.float32)

            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                all_obj_points, all_img_points, tuple(image_size), camera_matrix, dist_coeffs
            )

            print("\n--- RÉSULTATS ---")
            print(f"Erreur de reprojection (Précision) : {ret:.4f} pixels")

            print("\nMatrice Intrinsèque (Camera Matrix) :")
            print(camera_matrix)

            print("\nDistorsion (k1, k2, p1, p2, k3) :")
            print(dist_coeffs)

            np.savez(output_file, mtx=camera_matrix, dist=dist_coeffs, ret=ret)
            print(f"\nDonnées sauvegardées : '{output_file}'")

            self.camera_matrix = camera_matrix
            self.dist_coeffs = dist_coeffs
            return camera_matrix, dist_coeffs

        print("Erreur : Impossible de calibrer")
        return None, None
