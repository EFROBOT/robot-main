import os
import glob
import cv2
import numpy as np

from core.aruco import Aruco


class Camera:
    def __init__(self, camera_id=0, logs=None, calibration_dir=None):
        self.camera_id = camera_id
        self.logs = logs
        camera_key = str(camera_id)
        self.calibration_dir = calibration_dir or f"./data/calibrations/{camera_key}"
        self.calibration_file = f"{self.calibration_dir}/camera_calibration_{camera_key}.npz"

        self.cap = None
        self.camera_matrix = None
        self.dist_coeffs = None
        self.last_calibration_info = None

        self.width = 720
        self.height = 480
        self.fps = 30

        self.aruco = Aruco(marker_size=0.040)

    def open(self):
        backends = [
            (cv2.CAP_V4L2, "V4L2"),
            (cv2.CAP_ANY, "AUTO"),
        ]

        for backend, _ in backends:
            self.cap = cv2.VideoCapture(self.camera_id, backend)
            if self.cap.isOpened():
                self._configure()
                return True
            self.cap.release()

        if self.logs:
            self.logs.log("ERR", f"Erreur caméra {self.camera_id}")
        return False

    def _configure(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def load_calibration(self):
        if os.path.exists(self.calibration_file):
            with np.load(self.calibration_file) as data:
                self.camera_matrix = data["mtx"]
                self.dist_coeffs = data["dist"]
            self.aruco.set_calibration(self.camera_matrix, self.dist_coeffs)
            return True
        return False

    def use_default_calibration(self):
        self.camera_matrix = np.array([[640, 0, 320], [0, 640, 240], [0, 0, 1]], dtype=float)
        self.dist_coeffs = np.zeros((4, 1))
        self.aruco.set_calibration(self.camera_matrix, self.dist_coeffs)

    def get_calibration(self):
        return self.camera_matrix, self.dist_coeffs

    def calibrate_charuco(self, image_folder=None, output_file=None):
        image_folder = image_folder or self.calibration_dir
        output_file = output_file or self.calibration_file

        squares_x = 5
        squares_y = 4
        square_length = 0.050
        marker_length = 0.040

        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        board = cv2.aruco.CharucoBoard(
            (squares_x, squares_y), square_length, marker_length, dictionary
        )

        images_path = os.path.join(image_folder, "*.png")
        images = glob.glob(images_path)

        self.last_calibration_info = {
            "images": len(images),
            "valid": 0,
            "reason": None,
        }

        all_charuco_corners = []
        all_charuco_ids = []
        charuco_detector = cv2.aruco.CharucoDetector(board)
        image_size = None

        for fname in images:
            img = cv2.imread(fname)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            if image_size is None:
                image_size = gray.shape[::-1]

            charuco_corners, charuco_ids, _, _ = charuco_detector.detectBoard(gray)
            if charuco_corners is not None and len(charuco_corners) > 6:
                all_charuco_corners.append(charuco_corners)
                all_charuco_ids.append(charuco_ids)
                self.last_calibration_info["valid"] += 1

        if len(all_charuco_corners) > 0 and image_size is not None:
            all_obj_points = []
            all_img_points = []
            board_corners = board.getChessboardCorners()

            for i in range(len(all_charuco_corners)):
                if all_charuco_ids[i] is not None and len(all_charuco_ids[i]) > 0:
                    all_obj_points.append(board_corners[all_charuco_ids[i].flatten()])
                    all_img_points.append(all_charuco_corners[i])

            camera_matrix = np.eye(3, dtype=np.float32)
            dist_coeffs = np.zeros((5, 1), dtype=np.float32)

            ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
                all_obj_points, all_img_points, tuple(image_size), camera_matrix, dist_coeffs
            )

            np.savez(output_file, mtx=camera_matrix, dist=dist_coeffs, ret=ret)

            self.camera_matrix = camera_matrix
            self.dist_coeffs = dist_coeffs
            self.aruco.set_calibration(camera_matrix, dist_coeffs)
            return camera_matrix, dist_coeffs

        if self.last_calibration_info["images"] == 0:
            self.last_calibration_info["reason"] = "no_images"
        else:
            self.last_calibration_info["reason"] = "no_charuco_detected"
        return None, None
