"""Module de détection de marqueurs Aruco."""

import math
from dataclasses import dataclass

import cv2
import cv2.aruco as aruco
import numpy as np


@dataclass
class Marker:
    id: int
    vect_trans: np.ndarray
    vect_rot: np.ndarray

    distance: float
    x_pos: float
    y_pos: float
    z_pos: float
    angle: float


class Aruco:
    def __init__(
        self,
        marker_size: float = 0.040,
        dist_coeffs=None,
        camera_matrix=None,
        dictionary=aruco.DICT_4X4_50,
    ):
        """ """
        self.marker_size = marker_size
        self.dist_coeffs = dist_coeffs if dist_coeffs is not None else np.zeros((4, 1))
        self.camera_matrix = camera_matrix

        self.dictionary = cv2.aruco.getPredefinedDictionary(dictionary)
        self.parameters = cv2.aruco.DetectorParameters()

        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)

        half = marker_size / 2.0
        self.obj_points = np.array(
            [[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]],
            dtype=np.float32,
        )

    def detect_markers(self, image):
        """Détecte les marqueurs Aruco dans l'image et estime leur pose."""
        if image is None:
            return []

        if self.camera_matrix is None:
            raise ValueError("camera_matrix miss")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = self.detector.detectMarkers(gray)

        list_markers = []
        if ids is not None:
            for i in range(len(ids)):
                image_points = np.array(corners[i], dtype=np.float32).reshape(-1, 2)

                retval, rvec, tvec = cv2.solvePnP(
                    self.obj_points,
                    image_points,
                    self.camera_matrix,
                    self.dist_coeffs,
                    flags=cv2.SOLVEPNP_IPPE_SQUARE,
                )

                if retval:
                    x = float(tvec[0][0])
                    y = float(tvec[1][0])
                    z = float(tvec[2][0])

                    marker_aruco = Marker(
                        id=int(ids[i][0]),
                        vect_trans=tvec,
                        vect_rot=rvec,
                        distance=np.sqrt(x**2 + z**2),
                        x_pos=x,
                        y_pos=y,
                        z_pos=z,
                        angle=float(rvec[1][0]),
                    )
                    list_markers.append(marker_aruco)

        return list_markers

    def draw_marker(self, image, list_markers):
        """Dessine les axes et les infos sur l'image"""
        if not list_markers:
            return

        if self.camera_matrix is None:
            raise ValueError("camera_matrix")

        for obs in list_markers:
            # Dessiner le repère
            cv2.drawFrameAxes(
                image,
                self.camera_matrix,
                self.dist_coeffs,
                obs.vect_rot,
                obs.vect_trans,
                length=self.marker_size * 0.5,
            )

            distance = math.sqrt(obs.x_pos**2 + obs.z_pos**2)

            text = f"ID:{obs.id} X: {obs.x_pos * 100:.1f} cm | Z: {obs.z_pos * 100:.1f} cm"

            # Projection du point 3D en 2D pour placer le texte
            imgpts, _ = cv2.projectPoints(
                np.array([[0.0, 0.0, 0.0]], dtype=np.float32),
                obs.vect_rot,
                obs.vect_trans,
                self.camera_matrix,
                self.dist_coeffs,
            )

            center = (int(imgpts[0][0][0]), int(imgpts[0][0][1]))

            cv2.putText(
                image,
                text,
                (center[0] + 10, center[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 0, 0),
                2,
            )
            cv2.putText(
                image,
                f"Dist: {distance * 100:.1f} cm",
                (center[0] + 10, center[1] + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 0, 0),
                2,
            )
