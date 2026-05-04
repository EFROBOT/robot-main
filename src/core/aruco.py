import math
import cv2
import cv2.aruco as aruco
import numpy as np


class Marker:
    def __init__(
        self,
        marker_id,
        vect_trans,
        vect_rot,
        distance,
        x_pos,
        y_pos,
        z_pos,
        angle,
        corners=None,
        color_name="unknown",
        rect_corners=None,
        rect_size_px=None,
        rect_angle_deg=None,
    ):
        self.id = marker_id
        self.vect_trans = vect_trans
        self.vect_rot = vect_rot
        self.distance = distance
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.z_pos = z_pos
        self.angle = angle
        self.corners = corners
        self.color_name = color_name
        self.rect_corners = rect_corners
        self.rect_size_px = rect_size_px
        self.rect_angle_deg = rect_angle_deg


class Aruco:
    def __init__(
        self,
        marker_size=0.040,
        box_width=0.150,
        box_height=0.050,
        box_depth=0.030,
        dist_coeffs=None,
        camera_matrix=None,
        dictionary=aruco.DICT_4X4_100,
    ):
        self.marker_size = marker_size
        self.box_width = box_width
        self.box_height = box_height
        self.box_depth = box_depth
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

    def set_calibration(self, camera_matrix, dist_coeffs):
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs

    def get_box_properties(self, marker_id):
        if marker_id == 36:
            return "blue", (140, 91, 0)
        if marker_id == 47:
            return "yellow", (0, 181, 247)
        return "unknown", (0, 255, 0)

    def _detect_box_by_color(self, image, marker_corners, color_name):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        if color_name == "blue":
            lower_hsv = np.array([100, 100, 40])
            upper_hsv = np.array([160, 255, 100])
        elif color_name == "yellow":
            lower_hsv = np.array([20, 100, 150])
            upper_hsv = np.array([60, 255, 255])
        else:
            return None

        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        marker_center = np.mean(marker_corners, axis=0)
        best_contour = None
        best_distance = float("inf")

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:
                continue

            moments = cv2.moments(contour)
            if moments["m00"] == 0:
                continue

            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
            dist = np.sqrt((cx - marker_center[0]) ** 2 + (cy - marker_center[1]) ** 2)
            if dist < best_distance:
                best_distance = dist
                best_contour = contour

        if best_contour is None:
            return None

        rect = cv2.minAreaRect(best_contour)
        box_corners = cv2.boxPoints(rect)
        box_corners = np.float32(box_corners)

        rect_w, rect_h = rect[1]
        long_side = float(max(rect_w, rect_h))
        short_side = float(min(rect_w, rect_h))
        angle_deg = float(rect[2])
        if rect_w < rect_h:
            angle_deg += 90.0

        return box_corners, (long_side, short_side), angle_deg

    def detect_markers(self, image):
        if image is None:
            return []

        if self.camera_matrix is None:
            raise ValueError("camera_matrix manquante")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)

        list_markers = []
        valid_ids = {36, 47}

        if ids is not None:
            for i in range(len(ids)):
                marker_id = int(ids[i][0])
                if marker_id not in valid_ids:
                    continue

                color_name, _ = self.get_box_properties(marker_id)
                rect_result = self._detect_box_by_color(
                    image,
                    np.array(corners[i], dtype=np.float32).reshape(-1, 2),
                    color_name,
                )
                if rect_result is None:
                    continue

                rect_corners, rect_size_px, rect_angle_deg = rect_result
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

                    rmat, _ = cv2.Rodrigues(rvec)
                    yaw = math.atan2(rmat[0][2], rmat[2][2])

                    marker_aruco = Marker(
                        marker_id=marker_id,
                        vect_trans=tvec,
                        vect_rot=rvec,
                        distance=np.sqrt(x ** 2 + z ** 2),
                        x_pos=x,
                        y_pos=y,
                        z_pos=z,
                        angle=yaw,
                        corners=image_points,
                        color_name=color_name,
                        rect_corners=rect_corners,
                        rect_size_px=rect_size_px,
                        rect_angle_deg=rect_angle_deg,
                    )
                    list_markers.append(marker_aruco)

        return list_markers

    def compute_alignment(self, marker, approach_dist_m=0.10):
        x = float(marker.x_pos)
        z = float(marker.z_pos)

        bearing_rad = math.atan2(x, z)
        bearing_deg = math.degrees(bearing_rad)
        bearing_deg = (bearing_deg + 180.0) % 360.0 - 180.0

        rmat, _ = cv2.Rodrigues(marker.vect_rot)
        vec_z = rmat[:, 2]
        approach_point = marker.vect_trans.flatten() + (vec_z * approach_dist_m)

        return {
            "distance_cm": float(marker.distance * 100.0),
            "lateral_cm": float(x * 100.0),
            "depth_cm": float(z * 100.0),
            "bearing_deg": float(bearing_deg),
            "rect_long_axis_deg": float(marker.rect_angle_deg or 0.0),
            "approach_x_cm": float(approach_point[0] * 100.0),
            "approach_z_cm": float(approach_point[2] * 100.0),
        }

    def draw_marker(self, image, list_markers):
        if not list_markers:
            return

        for obs in list_markers:
            _, rect_color = self.get_box_properties(obs.id)

            if obs.corners is not None:
                contour = np.array(obs.corners, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(image, [contour], True, (0, 0, 255), 1, cv2.LINE_AA)

            if obs.rect_corners is not None:
                rect_contour = np.array(obs.rect_corners, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(image, [rect_contour], True, rect_color, 2, cv2.LINE_AA)

            hx = self.box_height / 2.0
            hy = self.box_width / 2.0
            depth = -self.box_depth

            box_points_3d = np.array(
                [
                    [-hx, -hy, 0.0], [hx, -hy, 0.0], [hx, hy, 0.0], [-hx, hy, 0.0],
                    [-hx, -hy, depth], [hx, -hy, depth], [hx, hy, depth], [-hx, hy, depth],
                ],
                dtype=np.float32,
            )

            box_image_points, _ = cv2.projectPoints(
                box_points_3d,
                obs.vect_rot,
                obs.vect_trans,
                self.camera_matrix,
                self.dist_coeffs,
            )
            img_pts = np.round(box_image_points).astype(np.int32).reshape(-1, 2)

            cv2.polylines(image, [img_pts[:4]], True, rect_color, 2, cv2.LINE_AA)
            cv2.polylines(image, [img_pts[4:]], True, (150, 150, 150), 1, cv2.LINE_AA)
            for i in range(4):
                cv2.line(image, tuple(img_pts[i]), tuple(img_pts[i + 4]), rect_color, 2, cv2.LINE_AA)

            box_center = np.mean(img_pts[:4], axis=0).astype(int)
            cv2.circle(image, tuple(box_center), 4, rect_color, -1)
            cv2.drawFrameAxes(
                image,
                self.camera_matrix,
                self.dist_coeffs,
                obs.vect_rot,
                obs.vect_trans,
                self.marker_size * 0.8,
            )

            align = self.compute_alignment(obs)
            dist_x = align["lateral_cm"]
            dist_z = align["depth_cm"]
            bearing = align["bearing_deg"]
            rect_axis = align["rect_long_axis_deg"]

            text_team = f"[{obs.color_name.upper()}] ID: {obs.id}"
            text_x = f"X (Centrage) : {dist_x:+.1f} cm"
            text_z = f"Z (Distance) : {dist_z:.1f} cm"
            text_bearing = f"Bearing (Rotation) : {bearing:+.1f}°"
            text_axis = f"Axe Long (Image) : {rect_axis:+.1f}°"

            tx, ty = int(box_center[0]) - 80, int(box_center[1]) - 50

            cv2.putText(image, text_team, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, rect_color, 2)
            cv2.putText(image, text_x, (tx, ty + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(image, text_z, (tx, ty + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            cv2.putText(image, text_bearing, (tx, ty + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
            cv2.putText(image, text_axis, (tx, ty + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 0), 2)
