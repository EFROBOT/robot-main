"""
Serveur API JSON pour EFROBOT.
Remplace le tableau de bord HTML par une API REST pure.
Nécessite flask-cors : pip install flask-cors
"""
import os
import time
import logging
import threading

from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

from core.affinite_cpu import fixer_affinite_cpu
from api.camera_handler import CameraHandler


class ApiServer:
    """Serveur API JSON pour piloter le robot via requêtes HTTP."""

    def __init__(self, robot, strategy, camera_indices=None,
                 port=5000, aruco_detection=False):
        self.robot = robot
        self.strategy = strategy
        self.port = port
        self.strategie_en_cours = False
        self.dernier_ordre_couleurs = []


        # Gestion des caméras (capture dans des threads séparés)
        self._camera = CameraHandler(
            camera_indices=camera_indices,
            robot=robot,
            aruco_detection=aruco_detection,
        )

        # Fournir le frame_provider à la stratégie si une caméra est ouverte
        if self._camera.nb_cameras > 0:
            self.strategy.frame_provider = lambda: self.get_frame(slot=0)

        # Application Flask (API pure, pas de templates)
        self.app = Flask(__name__)
        CORS(self.app)  # Autoriser les requêtes cross-origin (webview VS Code)
        self._enregistrer_routes()

    def get_frame(self, slot=0):
        """Proxy vers le gestionnaire de caméras."""
        return self._camera.get_frame(slot)

    def _enregistrer_routes(self):
        """Déclare toutes les routes de l'API."""

        @self.app.route("/etat")
        def etat():
            state = self.robot.get_state()
            state["nb_cameras"] = self._camera.nb_cameras
            state["strategie_en_cours"] = self.strategie_en_cours
            return jsonify(state)

        @self.app.route("/logs")
        def logs():
            source = request.args.get("source")
            if source:
                lignes = self.robot.logs.get_lines_by_source(source)
            else:
                lignes = self.robot.get_logs()
            return jsonify({"logs": lignes})

        @self.app.route("/logs/sources")
        def logs_sources():
            return jsonify({"sources": self.robot.logs.get_sources()})

        @self.app.route("/set_team", methods=["POST"])
        def set_team():
            payload = request.get_json(silent=True) or {}
            team = payload.get("team", "yellow")
            if team not in ("yellow", "blue"):
                self.robot.logs.log(
                    "ERR", f"Équipe invalide reçue: {team!r}, retour à yellow"
                )
                team = "yellow"
            self.robot.set_team(team)
            self.robot.logs.log(
                "RPi",
                f"Équipe {team} → robot positionné à "
                f"({self.robot.x}, {self.robot.y}) angle={self.robot.angle_deg}°",
            )
            return jsonify({
                "ok": True,
                "robot": {
                    "x": self.robot.x,
                    "y": self.robot.y,
                    "angle_deg": self.robot.angle_deg,
                },
            })

        @self.app.route("/commande", methods=["POST"])
        def commande():
            data = request.get_json(silent=True) or {}
            action = str(data.get("action", ""))
            option_val = int(data.get("option", 0))
            try:
                distance = float(data.get("distance", 10))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "erreur": "distance invalide"}), 400

            self.robot.logs.log(
                "RPi", f"Commande : {action} {distance}cm (opt: {option_val})"
            )
            # Table de correspondance action → fonction du robot
            actions = {
                "avancer":           lambda: self.robot.avancer(distance),
                "reculer":           lambda: self.robot.reculer(distance),
                "gauche":            lambda: self.robot.gauche(distance),
                "droite":            lambda: self.robot.droite(distance),
                "diag_gauche":       lambda: self.robot.diagonale_gauche(distance),
                "diag_droite":       lambda: self.robot.diagonale_droite(distance),
                "rot_gauche":        lambda: self.robot.rotation_gauche(distance),
                "rot_droite":        lambda: self.robot.rotation_droite(distance),
                "pince_open":        lambda: self.robot.pince_recuperer_et_stocker(option_val),
                "Pince Navigation":  lambda: self.robot.pince_navigation(),
                "pince_homologation": lambda: self.robot.pince_homologation(),
                "stockage":          lambda: self.robot.securiser_caisses(),
                "lacher_caisse":     lambda: self.robot.lacher_caisses(),
                "stop":              lambda: self.robot.stop(),
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

            def _executer():
                fixer_affinite_cpu(3, logs=self.robot.logs, nom_thread="nav_coord")
                self.robot.aller_a_coord(x, y)
            threading.Thread(target=_executer, daemon=True).start()
            return jsonify({"ok": True})

        @self.app.route("/nav_angle", methods=["POST"])
        def nav_angle():
            data = request.get_json(silent=True) or {}
            try:
                angle = float(data.get("angle", 0))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "erreur": "angle invalide"}), 400
            self.robot.logs.log("RPi", f"Tourner vers {angle}°")

            def _executer():
                fixer_affinite_cpu(3, logs=self.robot.logs, nom_thread="nav_angle")
                self.robot.tourner_vers_angle(angle)
            threading.Thread(target=_executer, daemon=True).start()
            return jsonify({"ok": True})

        @self.app.route("/strategie", methods=["POST"])
        def strategie():
            payload = request.get_json(silent=True) or {}
            try:
                numero = int(payload.get("numero", 1))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "erreur": "numéro invalide"}), 400
            if numero not in (1, 2, 3, 6, 7):
                return jsonify({"ok": False, "erreur": "stratégie inconnue"}), 400
            if self.strategie_en_cours:
                return jsonify({"ok": False, "erreur": "stratégie déjà en cours"}), 409

            def _executer():
                fixer_affinite_cpu(3, logs=self.robot.logs, nom_thread="strategie")
                self.strategie_en_cours = True
                try:
                    self._lancer_strategie(numero)
                except Exception as exc:
                    self.robot.logs.log("ERR", f"Stratégie {numero} : {exc}")
                finally:
                    if numero in (6, 7):
                        self.robot.stop()
                        self.robot.logs.log(
                            "RPi", f"Stratégie {numero} terminée: robot STOP"
                        )
                    self.strategie_en_cours = False
            threading.Thread(target=_executer, daemon=True).start()
            return jsonify({"ok": True, "message": f"Stratégie {numero} lancée"})

        @self.app.route("/camera_stream/<int:slot>")
        def camera_stream(slot):
            """Flux MJPEG continu pour un slot caméra."""
            if slot >= self._camera.nb_cameras:
                return "", 404

            def generer_flux():
                dernier = None
                while True:
                    jpeg = self._camera.get_jpeg(slot)
                    if jpeg is None or jpeg is dernier:
                        time.sleep(0.05)
                        continue
                    dernier = jpeg
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                    )
            return Response(
                generer_flux(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
                headers={"Cache-Control": "no-store, no-cache, max-age=0"},
            )

        @self.app.route("/camera/<int:slot>")
        def camera_snapshot(slot):
            """Snapshot JPEG ponctuel pour un slot caméra."""
            if slot >= self._camera.nb_cameras:
                return "", 404
            jpeg = self._camera.get_jpeg(slot)
            if jpeg is None:
                return "", 503
            return Response(
                jpeg, mimetype="image/jpeg",
                headers={"Cache-Control": "no-store"},
            )

        @self.app.route("/bg_image")
        def bg_image():
            """Sert l'image de la table de jeu."""
            racine = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            chemin = os.path.join(racine, "img", "table_FINALE_1.0-1.png")
            if os.path.exists(chemin):
                return send_file(chemin)
            self.robot.logs.log("ERR", f"Image introuvable : {chemin}")
            return "", 404

    # ── Exécution d'une stratégie par numéro ───────────────────
    def _lancer_strategie(self, numero):
        """Dispatch la stratégie demandée vers la bonne méthode."""
        fournir_frame = lambda: self.get_frame(slot=0)
        if numero == 1:
            self.strategy.aligner_sur_aruco(frame_provider=fournir_frame)
        elif numero == 2:
            self.strategy.aligner_et_recuperer_caisses(frame_provider=fournir_frame)
        elif numero == 3:
            pass
        elif numero == 6:
            pass
        elif numero == 7:
            self.strategy.homologation()

    # ── Lancement du serveur ───────────────────────────────────
    def run(self):
        """Démarre le serveur Flask en mode production."""
        fixer_affinite_cpu(3, logs=self.robot.logs, nom_thread="flask_api")
        self.robot.logs.log("RPi", f"API serveur : http://0.0.0.0:{self.port}")
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self.app.logger.setLevel(logging.ERROR)
        self.app.run(
            host="0.0.0.0", port=self.port,
            debug=False, use_reloader=False,
        )

    def __del__(self):
        """Libère les ressources caméra à la destruction."""
        self._camera.arreter()
