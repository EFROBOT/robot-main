import math
import cv2
import cv2.aruco as aruco
import numpy as np

class CaisseNoisette:
    def __init__(self, equipe, distance_cm, decalage_x_cm, angle_deg, rvec=None, tvec=None, box_corners=None, is_x_long=True):
        self.equipe = equipe          
        self.distance = distance_cm   
        self.decalage_x = decalage_x_cm 
        self.angle_longueur = angle_deg 
        
        self.rvec = rvec
        self.tvec = tvec
        self.box_corners = box_corners
        self.is_x_long = is_x_long 

    def __repr__(self):
        return f"<Caisse {self.equipe.upper()} | Dist: {self.distance:.1f}cm | X: {self.decalage_x:+.1f}cm | Angle: {self.angle_longueur:+.1f}°>"


class Aruco:
    def __init__(self, marker_size=0.040):
        self.marker_size = marker_size
        self.camera_matrix = None
        self.dist_coeffs = None
        
        self.box_width = 0.150  
        self.box_height = 0.050 
        self.box_depth = 0.030 
        
        self.dictionary = cv2.aruco.getPredefinedDictionary(aruco.DICT_4X4_100)
        self.parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)
        
        half = self.marker_size / 2.0
        self.obj_points = np.array([
            [-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]
        ], dtype=np.float32)

    def set_calibration(self, camera_matrix, dist_coeffs):
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs if dist_coeffs is not None else np.zeros((4, 1))

    def detect_markers(self, image):
        if image is None or self.camera_matrix is None:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        corners, ids, _ = self.detector.detectMarkers(gray)

        pieces_valides = []
        if ids is None:
            return pieces_valides

        for i in range(len(ids)):
            marker_id = int(ids[i][0])
            
            if cv2.contourArea(corners[i][0]) < 250: 
                continue

            if marker_id == 36:
                equipe = "bleu"
                lower_hsv = np.array([90, 80, 50])
                upper_hsv = np.array([130, 255, 255])
            elif marker_id == 47:
                equipe = "jaune"
                lower_hsv = np.array([10, 40, 50])
                upper_hsv = np.array([50, 255, 255])            
            else:
                continue 

            mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            marker_center = np.mean(corners[i][0], axis=0)
            best_contour = None

            for contour in contours:
                if cv2.contourArea(contour) < 400:
                    continue
                
                dist_to_edge = cv2.pointPolygonTest(contour, (float(marker_center[0]), float(marker_center[1])), True)
                if dist_to_edge > -40: 
                    best_contour = contour
                    break 

            if best_contour is None:
                continue 

            rect = cv2.minAreaRect(best_contour)
            box_corners = cv2.boxPoints(rect)
            rect_w, rect_h = rect[1]
            rect_angle_deg = float(rect[2])
            if rect_w < rect_h:
                rect_angle_deg += 90.0

            image_points = np.array(corners[i], dtype=np.float32).reshape(-1, 2)
            retval, rvec, tvec = cv2.solvePnP(
                self.obj_points, image_points, self.camera_matrix, self.dist_coeffs, flags=cv2.SOLVEPNP_IPPE_SQUARE
            )

            if not retval:
                continue

            x_m = float(tvec[0][0])
            z_m = float(tvec[2][0])
            distance_cm = math.sqrt(x_m**2 + z_m**2) * 100.0
            decalage_x_cm = x_m * 100.0

            pt_center, _ = cv2.projectPoints(np.array([[0.0, 0.0, 0.0]]), rvec, tvec, self.camera_matrix, self.dist_coeffs)
            pt_x, _ = cv2.projectPoints(np.array([[1.0, 0.0, 0.0]]), rvec, tvec, self.camera_matrix, self.dist_coeffs)
            dx = pt_x[0][0][0] - pt_center[0][0][0]
            dy = pt_x[0][0][1] - pt_center[0][0][1]
            aruco_x_angle_2d = math.degrees(math.atan2(dy, dx))

            diff = abs(rect_angle_deg - aruco_x_angle_2d) % 180
            if diff > 90:
                diff = 180 - diff

            is_x_long = (diff < 45)
            rmat, _ = cv2.Rodrigues(rvec)

            if is_x_long:
                vecteur_longueur = rmat[:, 0] 
            else:
                vecteur_longueur = rmat[:, 1] 

            angle_longueur_rad = math.atan2(vecteur_longueur[0], vecteur_longueur[2])
            angle_longueur_deg = math.degrees(angle_longueur_rad)

            caisse = CaisseNoisette(equipe, distance_cm, decalage_x_cm, angle_longueur_deg, rvec, tvec, box_corners, is_x_long)
            pieces_valides.append(caisse)

        return pieces_valides

    def draw_marker(self, image, liste_caisses):
        if image is None or not liste_caisses:
            return

        for caisse in liste_caisses:
            couleur = (255, 0, 0) if caisse.equipe == "bleu" else (0, 255, 255)

            if caisse.box_corners is not None:
                contour = np.int32(caisse.box_corners).reshape(-1, 1, 2)
                cv2.polylines(image, [contour], True, couleur, 2, cv2.LINE_AA)

            if caisse.rvec is not None and caisse.tvec is not None:
                cv2.drawFrameAxes(
                    image, self.camera_matrix, self.dist_coeffs, 
                    caisse.rvec, caisse.tvec, self.marker_size * 0.8
                )
                
                pt_center, _ = cv2.projectPoints(np.array([[0.0, 0.0, 0.0]]), caisse.rvec, caisse.tvec, self.camera_matrix, self.dist_coeffs)
                tx, ty = int(pt_center[0][0][0]) - 80, int(pt_center[0][0][1]) - 50

                textes = [
                    f"[{caisse.equipe.upper()}] Sens: {'X' if caisse.is_x_long else 'Y'}",
                    f"Z (Dist) : {caisse.distance:.1f} cm",
                    f"X (Centrage) : {caisse.decalage_x:+.1f} cm",
                    f"Angle Robot : {caisse.angle_longueur:+.1f} deg"
                ]

                for i, texte in enumerate(textes):
                    c = couleur if i == 0 else (0, 255, 0)
                    cv2.putText(image, texte, (tx, ty + (i * 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 2)

    def detect_zone_ramassage(self, image):
        if image is None or self.camera_matrix is None:
            return None
    
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
        # Masque blanc tres permissif
        lower_white = np.array([0, 0, 140])
        upper_white = np.array([180, 80, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
    
        kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_big = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_big)
    
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
        # Carre 20x20cm dans le repere monde
        obj_points = np.array([
            [-0.10, 0.10, 0], [0.10, 0.10, 0], [0.10, -0.10, 0], [-0.10, -0.10, 0]
        ], dtype=np.float32)
    
        carres_trouves = []
    
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 400:
                continue
    
            # Approximation polygonale tres tolerante
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.08 * peri, True)
    
            # Si on a plus de 4 points, on garde les 4 coins extremes
            if len(approx) < 4:
                continue
    
            if len(approx) > 4:
                # Reduit a 4 points en augmentant epsilon jusqu'a obtenir 4 points
                for eps in [0.10, 0.12, 0.15, 0.18, 0.20]:
                    approx2 = cv2.approxPolyDP(contour, eps * peri, True)
                    if len(approx2) == 4:
                        approx = approx2
                        break
                else:
                    # Fallback : on prend la boite englobante orientee
                    rect_min = cv2.minAreaRect(contour)
                    approx = cv2.boxPoints(rect_min).reshape(-1, 1, 2).astype(np.int32)
    
            if len(approx) != 4:
                continue
    
            # Verifie que la forme est convexe (un trapezoide reste convexe)
            if not cv2.isContourConvex(approx):
                continue
    
            # Verifie le remplissage : la forme doit remplir sa boite englobante
            rect_min = cv2.minAreaRect(contour)
            (_, _), (rw, rh), _ = rect_min
            if rw == 0 or rh == 0:
                continue
            rect_area = rw * rh
            if area / rect_area < 0.65:
                continue
    
            # Tri des 4 coins : top-left, top-right, bottom-right, bottom-left
            pts = approx.reshape(4, 2).astype(np.float32)
            rect = np.zeros((4, 2), dtype=np.float32)
    
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]   # top-left (x+y min)
            rect[2] = pts[np.argmax(s)]   # bottom-right (x+y max)
    
            d = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(d)]   # top-right (x-y min, donc x grand y petit)
            rect[3] = pts[np.argmax(d)]   # bottom-left (x-y max, donc x petit y grand)
    
            # solvePnP standard (pas IPPE_SQUARE qui exige un vrai carre)
            retval, rvec, tvec = cv2.solvePnP(
                obj_points, rect, self.camera_matrix, self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
    
            if retval:
                x_m = float(tvec[0][0])
                z_m = float(tvec[2][0])
                distance_cm = math.sqrt(x_m**2 + z_m**2) * 100.0
                decalage_x_cm = x_m * 100.0
    
                rmat, _ = cv2.Rodrigues(rvec)
                angle_deg = math.degrees(math.atan2(rmat[0, 0], rmat[2, 0]))
    
                carres_trouves.append({
                    "distance": distance_cm,
                    "decalage_x": decalage_x_cm,
                    "angle": angle_deg,
                    "rvec": rvec,
                    "tvec": tvec,
                    "corners": rect,
                    "area": area,
                })
    
        if carres_trouves:
            # Tri par taille (le plus grand = le plus probable)
            carres_trouves.sort(key=lambda x: -x["area"])
            result = carres_trouves[0]
            result.pop("area", None)
            return result
    
        return None
        
    def draw_zone_ramassage(self, image, zone):
        if image is None or zone is None:
            return
    
        couleur = (0, 255, 0)
    
        if zone.get("corners") is not None:
            contour = np.int32(zone["corners"]).reshape(-1, 1, 2)
            cv2.polylines(image, [contour], True, couleur, 2, cv2.LINE_AA)
    
        if zone.get("rvec") is not None and zone.get("tvec") is not None:
            cv2.drawFrameAxes(
                image, self.camera_matrix, self.dist_coeffs,
                zone["rvec"], zone["tvec"], 0.05
            )
    
            pt_center, _ = cv2.projectPoints(np.array([[0.0, 0.0, 0.0]]), zone["rvec"], zone["tvec"], self.camera_matrix, self.dist_coeffs)
            tx, ty = int(pt_center[0][0][0]) - 80, int(pt_center[0][0][1]) - 50
    
            textes = [
                "[ZONE RAMASSAGE]",
                f"Z (Dist) : {zone['distance']:.1f} cm",
                f"X (Centrage) : {zone['decalage_x']:+.1f} cm",
                f"Angle : {zone['angle']:+.1f} deg"
            ]
    
            for i, texte in enumerate(textes):
                c = couleur if i == 0 else (255, 255, 255)
                cv2.putText(image, texte, (tx, ty + (i * 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 2)