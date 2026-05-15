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
        return self.detect_markers_v2(image)
        
        """if image is None or self.camera_matrix is None:
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

        return pieces_valides"""
    
    def detect_markers_v2(self, image):
        """Détecte les marqueurs ArUco et détermine l'orientation de la boîte
        uniquement à partir de l'axe rouge (X) du marqueur, sans détection de couleur.
        """

        if image is None or self.camera_matrix is None:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
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
            elif marker_id == 47:
                equipe = "jaune"            
            else:
                continue 

            image_points = np.array(corners[i], dtype=np.float32).reshape(-1, 2)
            retval, rvec, tvec = cv2.solvePnP(
                self.obj_points, image_points, self.camera_matrix, self.dist_coeffs, 
                flags=cv2.SOLVEPNP_IPPE_SQUARE
            )

            if not retval:
                continue

            x_m = float(tvec[0][0])
            z_m = float(tvec[2][0])
            distance_cm = math.sqrt(x_m**2 + z_m**2) * 100.0
            decalage_x_cm = x_m * 100.0

            # Projeter le centre et un point sur l'axe X pour obtenir l'angle 2D de l'axe X
            pt_center, _ = cv2.projectPoints(np.array([[0.0, 0.0, 0.0]]), rvec, tvec, self.camera_matrix, self.dist_coeffs)
            pt_x, _ = cv2.projectPoints(np.array([[1.0, 0.0, 0.0]]), rvec, tvec, self.camera_matrix, self.dist_coeffs)
            dx = pt_x[0][0][0] - pt_center[0][0][0]
            dy = pt_x[0][0][1] - pt_center[0][0][1]
            aruco_x_angle_2d = math.degrees(math.atan2(dy, dx))

            angle_norm = abs(aruco_x_angle_2d) % 180
            if angle_norm > 90:
                angle_norm = 180 - angle_norm
            is_x_long = (angle_norm < 45)

            # Obtenir le vecteur de longueur de la boîte
            rmat, _ = cv2.Rodrigues(rvec)
            if is_x_long:
                vecteur_longueur = rmat[:, 0]  # Axe X
            else:
                vecteur_longueur = rmat[:, 1]  # Axe Y

            angle_longueur_rad = math.atan2(vecteur_longueur[0], vecteur_longueur[2])
            angle_longueur_deg = math.degrees(angle_longueur_rad)

            # Utiliser les coins du marqueur ArUco directement
            box_corners = corners[i][0].reshape(-1, 2)

            caisse = CaisseNoisette(
                equipe, distance_cm, decalage_x_cm, angle_longueur_deg, 
                rvec, tvec, box_corners, is_x_long
            )
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
        """
        if image is None or self.camera_matrix is None:
            return None
    
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
        # Masque blanc permissif (ton code actuel)
        lower_white = np.array([0, 0, 140])
        upper_white = np.array([180, 80, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        # --- NOUVEAU : Masque pour la bordure verte ---
        # Valeurs à ajuster légèrement selon l'éclairage de ta caméra
        lower_green = np.array([35, 80, 40]) 
        upper_green = np.array([85, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_big = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_big)
    
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
        # Carre 20x20cm dans le repere monde (0.10m du centre vers les bords)
        obj_points = np.array([
            [-0.10, 0.10, 0], [0.10, 0.10, 0], [0.10, -0.10, 0], [-0.10, -0.10, 0]
        ], dtype=np.float32)
    
        # Tolerance sur la taille reelle : entre 15 et 30 cm de cote
        TAILLE_MIN_CM = 15.0
        TAILLE_MAX_CM = 30.0
        # Tolerance sur le ratio largeur/hauteur en cm reels
        RATIO_MAX = 1.4
    
        carres_trouves = []
    
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 400:
                continue
    
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.08 * peri, True)
    
            if len(approx) < 4:
                continue
    
            if len(approx) > 4:
                for eps in [0.10, 0.12, 0.15, 0.18, 0.20]:
                    approx2 = cv2.approxPolyDP(contour, eps * peri, True)
                    if len(approx2) == 4:
                        approx = approx2
                        break
                else:
                    rect_min = cv2.minAreaRect(contour)
                    approx = cv2.boxPoints(rect_min).reshape(-1, 1, 2).astype(np.int32)
    
            if len(approx) != 4:
                continue
    
            if not cv2.isContourConvex(approx):
                continue

            mask_carre = np.zeros(image.shape[:2], dtype=np.uint8)
            
            # 2. On dessine notre carré blanc potentiel en plein (rempli)
            cv2.drawContours(mask_carre, [approx], -1, 255, thickness=cv2.FILLED)
            
            # 3. On "dilate" ce carré pour qu'il déborde sur l'extérieur (ex: de 15 pixels)
            # La taille du noyau (15,15) dépend de la résolution de ta caméra. 
            # A augmenter si tu es en 1080p, à baisser si tu es en 480p.
            kernel_dilate = np.ones((15, 15), np.uint8)
            mask_dilated = cv2.dilate(mask_carre, kernel_dilate)
            
            # 4. En soustrayant le carré d'origine au carré grossi, on obtient un "anneau"
            mask_anneau = cv2.bitwise_xor(mask_dilated, mask_carre)
            
            # 5. On compte combien de pixels de cet anneau sont verts
            pixels_total_anneau = cv2.countNonZero(mask_anneau)
            if pixels_total_anneau > 0:
                anneau_vert = cv2.bitwise_and(mask_green, mask_green, mask=mask_anneau)
                pixels_verts = cv2.countNonZero(anneau_vert)
                
                ratio_vert = pixels_verts / pixels_total_anneau
                
                # Si moins de 15% ou 20% du tour est vert, c'est probablement un tag ArUco ou une ligne !
                if ratio_vert < 0.15:
                    continue  # On rejette ce contour, on passe au suivant
            # =================================================================

            # Ton code normal reprend ici :
            rect_min = cv2.minAreaRect(contour)
        
            (_, _), (rw, rh), _ = rect_min
            if rw == 0 or rh == 0:
                continue
            rect_area = rw * rh
            if area / rect_area < 0.65:
                continue
    
            # Tri des coins
            pts = approx.reshape(4, 2).astype(np.float32)
            rect = np.zeros((4, 2), dtype=np.float32)
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]
            rect[2] = pts[np.argmax(s)]
            d = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(d)]
            rect[3] = pts[np.argmax(d)]
    
            retval, rvec, tvec = cv2.solvePnP(
                obj_points, rect, self.camera_matrix, self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
            if not retval:
                continue
    
            # Verification de la TAILLE REELLE de la forme
            # On reprojette les 4 coins du modele 3D et on compare aux coins detectes
            # pour estimer la taille reelle visible
            # Methode : on calcule la distance reelle entre coins en utilisant solvePnP
    
            # On fait un 2eme solvePnP avec un objet "unite" pour mesurer la taille
            # Plus simple : on mesure la taille pixel et on convertit grace a la distance
            x_m = float(tvec[0][0])
            z_m = float(tvec[2][0])
            distance_m = math.sqrt(x_m**2 + z_m**2)
            if distance_m < 0.05:
                continue
    
            # Taille en pixels du quadrilatere
            largeur_px = np.linalg.norm(rect[1] - rect[0])
            hauteur_px = np.linalg.norm(rect[3] - rect[0])
            if largeur_px == 0 or hauteur_px == 0:
                continue
    
            # Conversion pixels -> cm grace a la focale et la distance
            fx = self.camera_matrix[0, 0]
            fy = self.camera_matrix[1, 1]
            largeur_cm = (largeur_px * distance_m / fx) * 100.0
            hauteur_cm = (hauteur_px * distance_m / fy) * 100.0
    
            # Filtre taille reelle
            if largeur_cm < TAILLE_MIN_CM or largeur_cm > TAILLE_MAX_CM:
                continue
            if hauteur_cm < TAILLE_MIN_CM or hauteur_cm > TAILLE_MAX_CM:
                continue
    
            # Filtre ratio reel (ni trop allonge dans un sens ni dans l'autre)
            ratio = max(largeur_cm, hauteur_cm) / min(largeur_cm, hauteur_cm)
            if ratio > RATIO_MAX:
                continue
    
            distance_cm = distance_m * 100.0
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
                "largeur_cm": largeur_cm,
                "hauteur_cm": hauteur_cm,
            })
    
        if carres_trouves:
            carres_trouves.sort(key=lambda x: -x["area"])
            result = carres_trouves[0]
            result.pop("area", None)
            result.pop("largeur_cm", None)
            result.pop("hauteur_cm", None)
            return result
         """
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

    def detect_robots(
        self,
        image,
        caisses_couleurs=None,
        robot_size_m=0.30,
        min_area_px=2500,
        min_side_mm=60.0,
        max_perimeter_mm=700.0,
    ):
        """
        Détecte les autres robots (grosses caisses rectangulaires/carrées)
        indépendamment de leur couleur et avec une grande tolérance au mouvement.
        """
        if image is None or self.camera_matrix is None:
            return []

        # 1. Traitement de l'image (Indépendant de la couleur)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0) # Réduit le bruit et le flou de mouvement
        edges = cv2.Canny(blurred, 40, 120)         # Détection des bords
        
        # Fermeture morphologique pour relier les bords discontinus (très utile si le robot bouge)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_side_m = float(min_side_mm) / 1000.0
        max_perimeter_m = float(max_perimeter_mm) / 1000.0
        max_side_m = max_perimeter_m / 4.0
        nominal_side_m = min(max(robot_size_m, min_side_m), max_side_m)
        half = nominal_side_m / 2.0

        # Taille nominale pour la pose (le filtre taille se fait ensuite).
        obj_points = np.array([
            [-half,  half, 0],
            [ half,  half, 0],
            [ half, -half, 0],
            [-half, -half, 0]
        ], dtype=np.float32)

        robots_trouves = []

        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 2. Ignorer les petites caisses
            # On fixe un seuil très haut pour ne garder que les GROS objets (les robots).
            # (Vos petites caisses font environ 400px, ici on vise > 5000)
            if area < 5000:
                continue

            # 3. Tolérance pour la forme rectangulaire (Boîte englobante)
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            
            (_, _), (rw, rh), _ = rect
            if rw == 0 or rh == 0:
                continue
                
            box_area = rw * rh
            extent = area / box_area # Ratio de remplissage

            # Si la forme remplit moins de 60% de son rectangle englobant, ce n'est pas une caisse
            if extent < 0.60:
                continue

            # Tri des 4 coins pour le calcul de distance (Top-Left, Top-Right, Bottom-Right, Bottom-Left)
            pts = box.astype(np.float32)
            rect_sorted = np.zeros((4, 2), dtype=np.float32)
            
            s = pts.sum(axis=1)
            rect_sorted[0] = pts[np.argmin(s)]
            rect_sorted[2] = pts[np.argmax(s)]
            
            d = np.diff(pts, axis=1)
            rect_sorted[1] = pts[np.argmin(d)]
            rect_sorted[3] = pts[np.argmax(d)]

            # 4. Calcul de la distance du robot détecté
            retval, rvec, tvec = cv2.solvePnP(
                obj_points, rect_sorted, self.camera_matrix, self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if retval:
                x_m = float(tvec[0][0])
                z_m = float(tvec[2][0])
                distance_cm = math.sqrt(x_m**2 + z_m**2) * 100.0
                decalage_x_cm = x_m * 100.0

                fx = float(self.camera_matrix[0, 0])
                fy = float(self.camera_matrix[1, 1])
                if fx > 0.0 and fy > 0.0 and z_m > 0.0:
                    size_x_m = (rw * z_m) / fx
                    size_y_m = (rh * z_m) / fy
                    min_side_est = min(size_x_m, size_y_m)
                    perimeter_est = 2.0 * (size_x_m + size_y_m)

                    if min_side_est < min_side_m or perimeter_est > max_perimeter_m:
                        continue

                robots_trouves.append({
                    "distance": distance_cm,
                    "decalage_x": decalage_x_cm,
                    "rvec": rvec,
                    "tvec": tvec,
                    "box_corners": box,
                    "area": area
                })

        # Trier par taille pour avoir le robot le plus proche/gros en premier
        robots_trouves.sort(key=lambda x: -x["area"])
        return robots_trouves

    def draw_robots(self, image, liste_robots):
        """
        Dessine les robots adverses détectés sur l'image (en rouge).
        """
        if image is None or not liste_robots:
            return

        couleur = (0, 0, 255) # Rouge pour alerter d'un robot

        for robot in liste_robots:
            if robot.get("box_corners") is not None:
                contour = np.int32(robot["box_corners"]).reshape(-1, 1, 2)
                cv2.polylines(image, [contour], True, couleur, 3, cv2.LINE_AA)

            if robot.get("rvec") is not None and robot.get("tvec") is not None:
                # Dessiner le centre
                pt_center, _ = cv2.projectPoints(np.array([[0.0, 0.0, 0.0]]), robot["rvec"], robot["tvec"], self.camera_matrix, self.dist_coeffs)
                tx, ty = int(pt_center[0][0][0]) - 80, int(pt_center[0][0][1]) - 30

                textes = [
                    "[ROBOT ADVERSE]",
                    f"Dist : {robot['distance']:.1f} cm",
                    f"Decalage X : {robot['decalage_x']:+.1f} cm"
                ]

                for i, texte in enumerate(textes):
                    cv2.putText(image, texte, (tx, ty + (i * 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, couleur, 2)