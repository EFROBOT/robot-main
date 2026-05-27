"""
Gestionnaire de caméras pour le serveur API.

Ouvre les caméras via OpenCV, lance des threads de capture en continu
et stocke la dernière frame brute + JPEG encodé pour chaque slot.
"""

import threading
import time

import cv2

from core.affinite_cpu import fixer_affinite_cpu


class CameraHandler:
    """Gère l'ouverture, la capture et l'encodage des caméras."""

    def __init__(self, camera_indices, robot, aruco_detection=False):
        # Références vers le robot et ses logs
        self._robot = robot
        self._aruco_detection = aruco_detection

        # Listes parallèles indexées par slot
        self._caps = []            # cv2.VideoCapture
        self._locks = []           # threading.Lock
        self._camera_ids = []      # identifiant V4L2 original
        self._detectors = []       # détecteur ArUco ou None
        self._latest_frame = []    # dernière frame brute (numpy)
        self._latest_jpeg = []     # dernière frame encodée JPEG (bytes)
        self._latest_status = []   # état du slot ("init", "live", "error")
        self._workers = []         # threads de capture
        self._running = True

        # Ouverture persistante de chaque caméra détectée
        for idx in (camera_indices or []):
            cap = self._ouvrir_capture(idx)
            if cap is not None and cap.isOpened():
                self._configurer_capture(cap)
                slot = len(self._caps)
                self._caps.append(cap)
                self._locks.append(threading.Lock())
                self._camera_ids.append(idx)
                self._detectors.append(self._creer_detecteur())
                self._latest_frame.append(None)
                self._latest_jpeg.append(None)
                self._latest_status.append("init")
                robot.logs.log("RPi", f"Caméra {idx} ouverte → slot {slot}")
            else:
                if cap is not None:
                    cap.release()
                robot.logs.log("ERR", f"Impossible d'ouvrir la caméra {idx}")

        # Lancement des threads de capture
        for slot in range(len(self._caps)):
            worker = threading.Thread(
                target=self._boucle_capture, args=(slot,), daemon=True
            )
            worker.start()
            self._workers.append(worker)

    # ── Propriétés publiques ───────────────────────────────────
    @property
    def nb_cameras(self) -> int:
        """Nombre de caméras ouvertes avec succès."""
        return len(self._caps)

    # ── Ouverture et configuration d'une caméra ────────────────
    @staticmethod
    def _ouvrir_capture(idx):
        """Essaie d'ouvrir une VideoCapture, d'abord avec V4L2."""
        if isinstance(idx, int):
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(idx)
        else:
            cap = cv2.VideoCapture(idx)
        return cap

    @staticmethod
    def _configurer_capture(cap):
        """Applique les réglages de latence minimale et résolution."""
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 10)

    def _creer_detecteur(self):
        """Construit le détecteur ArUco si la détection est activée."""
        if not self._aruco_detection:
            return None
        if not self._robot.camera.load_calibration():
            self._robot.camera.use_default_calibration()
        return self._robot.camera.aruco

    # ── Encodage JPEG ──────────────────────────────────────────
    @staticmethod
    def _encoder_jpeg(frame, target_width=640, qualite=50):
        """Redimensionne si nécessaire et encode la frame en JPEG."""
        h, w = frame.shape[:2]
        if w > target_width:
            frame = cv2.resize(frame, (target_width, int(h * target_width / w)))
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, qualite])
        if not ok:
            return None
        return buf.tobytes()

    # ── Boucle de capture (thread par slot) ────────────────────
    def _boucle_capture(self, slot):
        """Thread de capture continu pour un slot de caméra."""
        if slot == 0:
            fixer_affinite_cpu(1, logs=self._robot.logs, nom_thread="camera_slot_0")

        cap = self._caps[slot]
        lock = self._locks[slot]
        detector = self._detectors[slot]
        premiere_frame = False

        while self._running:
            try:
                # Lecture avec vidage du buffer interne
                with lock:
                    for _ in range(2):
                        try:
                            cap.grab()
                        except Exception:
                            break
                    ret, frame = cap.retrieve()
                    if not ret:
                        ret, frame = cap.read()

                if frame is None:
                    self._latest_status[slot] = "error"
                    time.sleep(0.01)
                    continue

                if not premiere_frame:
                    self._robot.logs.log("RPi", f"Caméra slot {slot} -> première frame reçue")
                    premiere_frame = True

                # Sauvegarde de la frame brute
                raw_frame = frame.copy()
                self._latest_frame[slot] = raw_frame

                # Détection ArUco si activée
                if detector is not None:
                    try:
                        liste_caisses = detector.detect_markers(frame)
                        detector.draw_marker(frame, liste_caisses)
                        if liste_caisses and hasattr(self._robot, "align_controller"):
                            self._robot.align_to_marker(liste_caisses[0])
                    except Exception as e:
                        self._robot.logs.log("ERR", f"Aruco caméra {slot} : {e}")

                # Encodage JPEG
                jpeg = self._encoder_jpeg(frame)
                if jpeg is not None:
                    self._latest_jpeg[slot] = jpeg
                    self._latest_status[slot] = "live"

            except Exception as e:
                self._latest_status[slot] = "error"
                self._robot.logs.log("ERR", f"Flux caméra {slot} : {e}")

            time.sleep(0.01)

    # ── Accès publics aux frames ───────────────────────────────
    def get_frame(self, slot=0):
        """Retourne la dernière frame brute capturée, ou None."""
        if slot >= len(self._latest_frame):
            return None
        return self._latest_frame[slot]

    def get_jpeg(self, slot=0):
        """Retourne le dernier JPEG encodé, ou None."""
        if slot >= len(self._latest_jpeg):
            return None
        return self._latest_jpeg[slot]

    # ── Nettoyage ──────────────────────────────────────────────
    def arreter(self):
        """Arrête les threads et libère les caméras."""
        self._running = False
        for cap in self._caps:
            try:
                cap.release()
            except Exception:
                pass

    def __del__(self):
        self.arreter()
