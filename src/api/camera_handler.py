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
        self._camera = robot.camera

        # Listes parallèles indexées par slot
        self._caps = []            # caméra déjà ouverte par Robot
        self._locks = []           # threading.Lock
        self._detectors = []       # détecteur ArUco ou None
        self._latest_frame = []    # dernière frame brute (numpy)
        self._latest_jpeg = []     # dernière frame encodée JPEG (bytes)
        self._latest_status = []   # état du slot ("init", "live", "error")
        self._workers = []         # threads de capture
        self._running = True

        camera_id = self._camera.camera_id
        camera_ouverte = self._camera.cap is not None and self._camera.cap.isOpened()
        if camera_ouverte and (not camera_indices or camera_id in camera_indices):
            self._caps.append(self._camera)
            self._locks.append(threading.Lock())
            self._detectors.append(self._creer_detecteur())
            self._latest_frame.append(None)
            self._latest_jpeg.append(None)
            self._latest_status.append("init")
            robot.logs.log("RPi", f"Caméra robot {camera_id} utilisée par le handler → slot 0")
        elif camera_indices:
            robot.logs.log("WARN", f"Caméra robot {camera_id} non sélectionnée par la config: {camera_indices}")

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
                if hasattr(cap, "_latest_frame"):
                    cap._latest_frame = raw_frame

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
