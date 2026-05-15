import threading
import time
import math
import base64
import glob
import os
from flask import Flask, jsonify, render_template, request, send_file

import cv2

from core.camera import Camera
from core.robot import Robot


class AffichageWeb:
    def __init__(
        self,
        robot,
        strategy,
        camera_indices=None,
        port=5000,
        image_path=None,
        aruco_detection=False,
        camera_refresh_hz=20,
    ):
        """
        camera_indices : liste d'indices V4L2 retournée par init_devices()["cameras"]
                         ex: [0, 2]
                         Les VideoCapture sont ouverts UNE SEULE FOIS ici et restent ouverts.
        """
        self.robot           = robot
        self.strategy       = strategy
        self.port            = port
        self.image_path      = image_path
        self.aruco_detection = aruco_detection
        self.camera_refresh_hz = max(1, int(camera_refresh_hz))
        base_dir = os.path.dirname(__file__)
        self.app = Flask(
            __name__,
            template_folder=os.path.join(base_dir, "templates"),
            static_folder=os.path.join(base_dir, "static"),
        )
        self.strategie_en_cours = False

        # ── Ouverture persistante des caméras ──────────────────
        # Une VideoCapture + un Lock par caméra détectée.
        # Plus aucun open/release à chaque requête → fin du "device busy".
        self._caps  = []   # [cv2.VideoCapture, ...]
        self._locks = []   # [threading.Lock(), ...]
        self._camera_ids = []
        self._detectors = []
        self._latest_frame = []
        self._latest_jpeg = []
        self._latest_status = []
        self._calibration_state = []
        self._last_align_log_ms = []
        self._workers = []
        self._running = True

        for idx in (camera_indices or []):
            if isinstance(idx, int):
                cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(idx)
            else:
                cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # latence minimale
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480 )
                cap.set(cv2.CAP_PROP_FPS, 10)
                self._caps.append(cap)
                self._locks.append(threading.Lock())
                self._camera_ids.append(idx)
                self._detectors.append(self._build_detector(idx))
                self._latest_frame.append(None)
                self._latest_jpeg.append(None)
                self._latest_status.append("init")
                self._calibration_state.append({
                    "count": self._count_calibration_images(idx),
                    "running": False,
                    "last_error": None,
                    "last_result": None,
                })
                self._last_align_log_ms.append(0.0)
                self.robot.logs.log("RPi", f"Caméra {idx} ouverte → slot {len(self._caps)-1}")
            else:
                cap.release()
                self.robot.logs.log("ERR", f"Impossible d'ouvrir la caméra {idx}")

        for slot in range(len(self._caps)):
            worker = threading.Thread(target=self._camera_worker, args=(slot,), daemon=True)
            worker.start()
            self._workers.append(worker)

        self._setup_routes()

    def _build_detector(self, camera_id):
        if not self.aruco_detection:
            return None
        if not self.robot.camera.load_calibration():
            self.robot.camera.use_default_calibration()
        return self.robot.camera.aruco

    def _calibration_paths(self, camera_id):
        cam = self.robot.camera
        if not os.path.exists(cam.calibration_dir):
            os.makedirs(cam.calibration_dir)
        return cam.calibration_dir, cam.calibration_file

    def _count_calibration_images(self, camera_id):
        calib_dir, _ = self._calibration_paths(camera_id)
        return len(glob.glob(os.path.join(calib_dir, "*.png")))

    def _encode_frame(self, frame):
        h, w = frame.shape[:2]
        target_width = 640
        if w > target_width:
            frame = cv2.resize(frame, (target_width, int(h * target_width / w)))

        ok, buf = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 50],
        )
        if not ok:
            return None
        return buf.tobytes()

    def _camera_worker(self, slot):
        cap = self._caps[slot]
        lock = self._locks[slot]
        detector = self._detectors[slot]
        first_frame_logged = False
        while self._running:
            frame = None
            try:
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

                if not first_frame_logged:
                    self.robot.logs.log("RPi", f"Caméra slot {slot} -> première frame reçue")
                    first_frame_logged = True

                raw_frame = frame.copy()

                if detector is not None:
                    try:
                        liste_caisses = detector.detect_markers(frame)
                        detector.draw_marker(frame, liste_caisses)

                        zone = detector.detect_zone_ramassage(frame)
                        self.robot.zone_ramassage = zone
                        detector.draw_zone_ramassage(frame, zone)
                        """
                        robots = detector.detect_robots(frame)
                        detector.draw_robots(frame, robots)
                        print(f"robots: {len(robots)}", robots[:1])
                        """
                        if liste_caisses and hasattr(self.robot, "align_controller"):
                            now_ms = time.time() * 1000
                            interval_ms = getattr(self.robot, "align_interval_ms", 100)
                            if now_ms - self._last_align_log_ms[slot] >= interval_ms:
                                self._last_align_log_ms[slot] = now_ms
                                self.robot.align_to_marker(liste_caisses[0])
                    except Exception as e:
                        self.robot.logs.log("ERR", f"Aruco caméra {slot} : {e}")

                self._latest_frame[slot] = raw_frame

                jpeg = self._encode_frame(frame)
                if jpeg is not None:
                    self._latest_jpeg[slot] = jpeg
                    self._latest_status[slot] = "live"
            except Exception as e:
                self._latest_status[slot] = "error"
                self.robot.logs.log("ERR", f"Flux caméra {slot} : {e}")

            time.sleep(0.01)

    def _z2d(self, z):
        return {
            "name":     z.name,
            "center_x": z.center.x,
            "center_y": z.center.y,
            "width":    z.width,
            "height":   z.height,
            "x_min":    z.x_min(),
            "y_max":    z.y_max(),
        }

    def get_frame(self, slot=0):
        """Retourne la dernière frame capturée par le worker, ou None."""
        if slot >= len(self._latest_frame):
            return None
        return self._latest_frame[slot]

    def _setup_routes(self):

        @self.app.route("/")
        def index():
            return render_template("dashboard.html")

        @self.app.route("/bg_image")
        def bg_image():
            dossier_racine = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            chemin_image = os.path.join(dossier_racine, 'img', 'table_FINALE_1.0-1.png')
            if os.path.exists(chemin_image):
                return send_file(chemin_image)
            self.robot.logs.log("ERR", f"Image introuvable : {chemin_image}")
            return "", 404

        # ── Snapshot caméra ────────────────────────────────────
        @self.app.route("/camera/<int:slot>")
        def camera_snapshot(slot):
            """Retourne un snapshot JPEG ponctuel pour compatibilité."""
            if slot >= len(self._caps):
                return "", 404

            jpeg = self._latest_jpeg[slot]
            if jpeg is None:
                return "", 503

            from flask import Response
            return Response(jpeg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})

        @self.app.route("/camera_stream/<int:slot>")
        def camera_stream(slot):
            """Flux MJPEG continu basé sur l'image la plus récente du worker caméra."""
            if slot >= len(self._caps):
                return "", 404

            def generate():
                last_sent = None
                while self._running:
                    jpeg = self._latest_jpeg[slot]
                    if jpeg is None or jpeg == last_sent:
                        time.sleep(0.05)
                        continue

                    last_sent = jpeg
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                    )

            from flask import Response
            return Response(
                generate(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
                headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
            )

        @self.app.route("/calibration/status")
        def calibration_status():
            data = []
            for slot, camera_id in enumerate(self._camera_ids):
                state = self._calibration_state[slot]
                data.append({
                    "slot": slot,
                    "camera_id": camera_id,
                    "count": state["count"],
                    "running": state["running"],
                    "last_error": state["last_error"],
                    "last_result": state["last_result"],
                })
            return jsonify({"calibrations": data})

        @self.app.route("/calibration/reset", methods=["POST"])
        def calibration_reset():
            payload = request.get_json(silent=True) or {}
            try:
                slot = int(payload.get("slot", 0))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "slot invalide"}), 400

            if slot < 0 or slot >= len(self._camera_ids):
                return jsonify({"ok": False, "error": "slot hors plage"}), 404

            camera_id = self._camera_ids[slot]
            calib_dir, _ = self._calibration_paths(camera_id)
            for fname in glob.glob(os.path.join(calib_dir, "*.png")):
                try:
                    os.remove(fname)
                except OSError:
                    pass

            state = self._calibration_state[slot]
            state["count"] = 0
            state["last_error"] = None
            state["last_result"] = None
            self.robot.logs.log("RPi", f"Calibration caméra {camera_id} -> reset photos")
            return jsonify({"ok": True, "count": 0})

        @self.app.route("/calibration/capture", methods=["POST"])
        def calibration_capture():
            payload = request.get_json(silent=True) or {}
            try:
                slot = int(payload.get("slot", 0))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "slot invalide"}), 400

            if slot < 0 or slot >= len(self._camera_ids):
                return jsonify({"ok": False, "error": "slot hors plage"}), 404

            frame = self._latest_frame[slot]
            if frame is None:
                return jsonify({"ok": False, "error": "aucune frame"}), 503

            camera_id = self._camera_ids[slot]
            calib_dir, _ = self._calibration_paths(camera_id)
            state = self._calibration_state[slot]
            filename = os.path.join(calib_dir, f"calib_{state['count']:03d}.png")
            if not cv2.imwrite(filename, frame):
                return jsonify({"ok": False, "error": "echec ecriture"}), 500

            state["count"] += 1
            state["last_error"] = None
            msg = f"Photo enregistrée {os.path.basename(filename)}"
            self.robot.logs.log("RPi", f"Calibration caméra {camera_id} -> {msg}")
            return jsonify({"ok": True, "count": state["count"], "message": msg})

        @self.app.route("/calibration/run", methods=["POST"])
        def calibration_run():
            payload = request.get_json(silent=True) or {}
            try:
                slot = int(payload.get("slot", 0))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "slot invalide"}), 400

            if slot < 0 or slot >= len(self._camera_ids):
                return jsonify({"ok": False, "error": "slot hors plage"}), 404

            state = self._calibration_state[slot]
            if state["running"]:
                return jsonify({"ok": False, "error": "calibration deja en cours"}), 409

            camera_id = self._camera_ids[slot]
            calib_dir, calib_file = self._calibration_paths(camera_id)
            if state["count"] < 3:
                return jsonify({"ok": False, "error": "pas assez de photos"}), 400

            state["running"] = True
            state["last_error"] = None
            state["last_result"] = None

            def run_calibration():
                try:
                    cam = Camera(camera_id=camera_id)
                    result = cam.calibrate_charuco(
                        image_folder=calib_dir,
                        output_file=calib_file,
                    )
                    if result[0] is None:
                        info = getattr(cam, "last_calibration_info", None) or {}
                        if info:
                            reason = info.get("reason") or "calibration echouee"
                            valid = info.get("valid")
                            images = info.get("images")
                            if valid is not None and images is not None:
                                state["last_error"] = f"{reason} ({valid}/{images})"
                            else:
                                state["last_error"] = reason
                        else:
                            state["last_error"] = "calibration echouee"
                    else:
                        state["last_result"] = os.path.basename(calib_file)
                        self._detectors[slot] = self._build_detector(camera_id)
                        self.robot.logs.log("RPi", f"Calibration caméra {camera_id} -> OK")
                except Exception as exc:
                    state["last_error"] = str(exc)
                    self.robot.logs.log("ERR", f"Calibration caméra {camera_id} : {exc}")
                finally:
                    state["count"] = self._count_calibration_images(camera_id)
                    state["running"] = False

            threading.Thread(target=run_calibration, daemon=True).start()
            return jsonify({"ok": True, "message": "Calibration lancée"})

        @self.app.route("/etat")
        def etat():
            state = self.robot.get_state()
            state["nb_cameras"] = len(self._caps)
            state["strategie_en_cours"] = self.strategie_en_cours
            return jsonify(state)

        @self.app.route("/logs")
        def logs():
            return jsonify({"logs": self.robot.get_logs()})

        @self.app.route("/set_team", methods=["POST"])
        def set_team():
            payload = request.get_json(silent=True) or {}
            team = payload.get("team", "yellow")
            if team not in ("yellow", "blue"):
                self.robot.logs.log("ERR", f"Équipe invalide reçue: {team!r}, retour à yellow")
                team = "yellow"

            self.robot.set_team(team)
            self.robot.logs.log("RPi", f"Équipe {team} → robot positionné à ({self.robot.x}, {self.robot.y}) angle={self.robot.angle_deg}°")
            return jsonify({"ok": True, "robot": {
                "x": self.robot.x, "y": self.robot.y, "angle_deg": self.robot.angle_deg
            }})


        @self.app.route("/strategie", methods=["POST"])
        def strategie():
            payload = request.get_json(silent=True) or {}
            try:
                numero = int(payload.get("numero", 1))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "erreur": "numéro de stratégie invalide"}), 400

            if numero not in (1, 2, 3, 4, 5):
                return jsonify({"ok": False, "erreur": "stratégie inconnue"}), 400

            if self.strategie_en_cours:
                return jsonify({"ok": False, "erreur": "stratégie déjà en cours"}), 409

            def run():
                self.strategie_en_cours = True
                try:
                    if numero == 1:
                        self.strategy.aligner_sur_aruco(frame_provider=lambda: self.get_frame(slot=0))
                    elif numero == 2:
                        self.strategy.prendre_set_caisse(frame_provider=lambda: self.get_frame(slot=0))
                    elif numero == 3:
                        self.strategy.aligner_sur_zone_de_ramassage(frame_provider=lambda: self.get_frame(slot=0))
                    elif numero == 4:
                        self.strategy.depot_set_caisse(frame_provider=lambda: self.get_frame(slot=0))
                    elif numero == 5:
                        self.strategy.strategie_homologation(frame_provider=lambda: self.get_frame(slot=0))
                    elif numero == 6:
                        self.strategy.homologation()


                except Exception as exc:
                    self.robot.logs.log("ERR", f"Stratégie {numero} : {exc}")
                finally:
                    self.strategie_en_cours = False

            threading.Thread(target=run, daemon=True).start()
            return jsonify({"ok": True, "message": f"Stratégie {numero} lancée"})

        @self.app.route("/commande", methods=["POST"])
        def commande():
            data = request.get_json(silent=True) or {}
            action = str(data.get("action", ""))
            option_val = int(data.get("option", 0))
            
            try:
                distance = float(data.get("distance", 10))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "erreur": "distance invalide"}), 400

            self.robot.logs.log("RPi", f"Commande : {action} {distance}cm (opt: {option_val})")

            actions = {
                "avancer"           : lambda: self.robot.avancer(distance),
                "reculer"           : lambda: self.robot.reculer(distance),
                "gauche"            : lambda: self.robot.gauche(distance),
                "droite"            : lambda: self.robot.droite(distance),
                "diag_gauche"       : lambda: self.robot.diagonale_gauche(distance),
                "diag_droite"       : lambda: self.robot.diagonale_droite(distance),
                "rot_gauche"        : lambda: self.robot.rotation_gauche(distance),
                "rot_droite"        : lambda: self.robot.rotation_droite(distance),
                "pince_open"        : lambda: self.robot.recuperer_caisses(option_val),
                "Pince Navigation"  : lambda: self.robot.pince_navigation(),
                "pince_homologation": lambda: self.robot.pince_homologation(),
                "stockage"          : lambda: self.robot.securiser_caisses(),
                "lacher_caisse"     : lambda: self.robot.lacher_caisses(),
                "stop"              : lambda: self.robot.stop(),
            }
            
            if action in actions:
                actions[action]()
                return jsonify({"ok": True})
            return jsonify({"ok": False}), 400

        @self.app.route("/nav_coord", methods=["POST"])
        def nav_coord():
            data = request.get_json(silent=True) or {}
            try:
                x = float(data.get("x", 0))
                y = float(data.get("y", 0))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "erreur": "coordonnées invalides"}), 400

            self.robot.logs.log("RPi", f"Aller à ({x}, {y})")
            threading.Thread(
                target=lambda: self.robot.aller_a_coord(x, y),
                daemon=True
            ).start()
            return jsonify({"ok": True})

        @self.app.route("/nav_angle", methods=["POST"])
        def nav_angle():
            data = request.get_json(silent=True) or {}
            try:
                angle = float(data.get("angle", 0))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "erreur": "angle invalide"}), 400

            self.robot.logs.log("RPi", f"Tourner vers {angle}°")
            threading.Thread(
                target=lambda: self.robot.tourner_vers_angle(angle),
                daemon=True
            ).start()
            return jsonify({"ok": True})

    def run(self):
        self.robot.logs.log("RPi", f"Dashboard : http://localhost:{self.port}")
        self.app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)

    def __del__(self):
        """Libère les VideoCapture proprement à la destruction."""
        self._running = False
        for cap in self._caps:
            try:
                cap.release()
            except Exception:
                pass