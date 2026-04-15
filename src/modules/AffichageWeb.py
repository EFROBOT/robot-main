import threading
import math
from collections import deque
from flask import Flask, jsonify, render_template_string, request
from Map import Map

# Buffer partagé : max 100 lignes
log_buffer = deque(maxlen=100)

def log(source, message):
    ligne = f"[{source}] {message}"
    log_buffer.append(ligne)
    print(ligne)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Eurobot - Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            align-items: flex-start;
        }
        .panneau {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            min-width: 200px;
        }
        h2 {
            margin: 0 0 16px 0;
            font-size: 16px;
            color: #a0a8c0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .valeur { font-size: 28px; font-weight: bold; color: #e94560; margin-bottom: 4px; }
        .label  { font-size: 12px; color: #666; margin-bottom: 16px; }
        canvas  { border-radius: 8px; display: block; background: #0f3460; }
        #status { font-size: 11px; color: #444; margin-top: 12px; }

        .manette {
            display: grid;
            grid-template-columns: repeat(3, 64px);
            grid-template-rows:    repeat(3, 64px);
            gap: 6px;
            margin-top: 12px;
        }
        .btn {
            width: 64px;
            height: 64px;
            border-radius: 10px;
            border: none;
            background: #0f3460;
            color: #eee;
            font-size: 22px;
            cursor: pointer;
            user-select: none;
            transition: background 0.1s;
        }
        .btn:active, .btn.actif { background: #e94560; }
        .btn.vide { background: transparent; cursor: default; pointer-events: none; }

        .distance-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 14px;
        }
        .distance-row input {
            width: 70px;
            padding: 6px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #0f3460;
            color: #eee;
            font-size: 14px;
        }
        .distance-row label { font-size: 12px; color: #666; }

        /* Terminal */
        .terminal {
            width: 100%;
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            box-sizing: border-box;
        }
        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .terminal-header h2 { margin: 0; }
        .filtre-btn {
            padding: 4px 12px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #0f3460;
            color: #aaa;
            font-size: 12px;
            cursor: pointer;
        }
        .filtre-btn.actif { background: #e94560; color: #fff; border-color: #e94560; }

        #terminal-box {
            background: #0a0a1a;
            border-radius: 8px;
            padding: 12px;
            height: 220px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            line-height: 1.6;
        }
        .log-stm  { color: #4fc3f7; }
        .log-rpi  { color: #a5d6a7; }
        .log-err  { color: #e94560; }
        .log-info { color: #aaa; }
    </style>
</head>
<body>

<div class="panneau">
    <h2>Position robot</h2>
    <div class="valeur" id="val-x">--</div><div class="label">X (cm)</div>
    <div class="valeur" id="val-y">--</div><div class="label">Y (cm)</div>
    <div class="valeur" id="val-angle">--</div><div class="label">Angle (°)</div>
    <h2>Inventaire</h2>
    <div class="valeur" id="val-caisses">--</div><div class="label">caisses</div>
    <div id="status">en attente...</div>
</div>

<div class="panneau">
    <h2>Carte</h2>
    <canvas id="carte" width="600" height="400"></canvas>
</div>

<div class="panneau">
    <h2>Télécommande</h2>
    <div class="distance-row">
        <label>Distance (cm)</label>
        <input type="number" id="distance" value="10" min="1" max="200"/>
    </div>
    <div class="manette">
        <button class="btn" id="btn-diag-gauche" title="Diagonale gauche">↖</button>
        <button class="btn" id="btn-avant"        title="Avancer">↑</button>
        <button class="btn" id="btn-diag-droite"  title="Diagonale droite">↗</button>

        <button class="btn" id="btn-gauche"       title="Gauche">←</button>
        <button class="btn vide"></button>
        <button class="btn" id="btn-droite"       title="Droite">→</button>

        <button class="btn" id="btn-rot-gauche"   title="Rotation gauche">↺</button>
        <button class="btn" id="btn-arriere"      title="Reculer">↓</button>
        <button class="btn" id="btn-rot-droite"   title="Rotation droite">↻</button>
    </div>
    <h2 style="margin-top:20px">Pince</h2>
    <div style="display:flex; gap:8px">
        <button class="btn" id="btn-pince-open"  style="width:auto;padding:0 16px">Ouvrir</button>
        <button class="btn" id="btn-pince-close" style="width:auto;padding:0 16px">Fermer</button>
    </div>
</div>

<!-- Terminal pleine largeur en bas -->
<div class="terminal">
    <div class="terminal-header">
        <h2>Terminal</h2>
        <div style="display:flex; gap:8px; align-items:center">
            <button class="filtre-btn actif" id="f-all"  onclick="setFiltre('all')">Tout</button>
            <button class="filtre-btn"       id="f-stm"  onclick="setFiltre('STM32')">STM32</button>
            <button class="filtre-btn"       id="f-rpi"  onclick="setFiltre('RPi')">RPi</button>
            <button class="filtre-btn"       id="f-err"  onclick="setFiltre('ERR')">Erreurs</button>
            <button class="filtre-btn" onclick="viderTerminal()">🗑 Vider</button>
        </div>
    </div>
    <div id="terminal-box"></div>
</div>

<script>
    const SCALE = 2;
    const H = 400;
    let filtre_actif = "all";
    let toutes_les_lignes = [];

    function toPx(x, y) { return [x * SCALE, H - y * SCALE]; }

    function dessinerZone(ctx, zone, couleur, texte) {
        const [px, py] = toPx(zone.x_min, zone.y_max);
        ctx.fillStyle = couleur;
        ctx.fillRect(px, py, zone.width * SCALE, zone.height * SCALE);
        ctx.strokeStyle = "#333";
        ctx.lineWidth = 1;
        ctx.strokeRect(px, py, zone.width * SCALE, zone.height * SCALE);
        if (texte) {
            ctx.fillStyle = "#222";
            ctx.font = "9px Arial";
            const [cx, cy] = toPx(zone.center_x, zone.center_y);
            ctx.fillText(texte, cx - 10, cy + 3);
        }
    }

    function dessinerRobot(ctx, robot) {
        const angle = robot.angle_rad;
        const [cx, cy] = toPx(robot.x, robot.y);
        const w2 = robot.width  / 2 * SCALE;
        const h2 = robot.height / 2 * SCALE;
        const coins = [[w2,h2],[-w2,h2],[-w2,-h2],[w2,-h2]];

        ctx.beginPath();
        coins.forEach(([lx, ly], i) => {
            const rx = lx * Math.cos(angle) - ly * Math.sin(angle);
            const ry = lx * Math.sin(angle) + ly * Math.cos(angle);
            i === 0 ? ctx.moveTo(cx+rx, cy-ry) : ctx.lineTo(cx+rx, cy-ry);
        });
        ctx.closePath();
        ctx.fillStyle = "#555";
        ctx.fill();

        const ax = w2 * Math.cos(angle);
        const ay = w2 * Math.sin(angle);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + ax, cy - ay);
        ctx.strokeStyle = "#e94560";
        ctx.lineWidth = 3;
        ctx.stroke();
    }

    // ── Terminal ─────────────────────────────────────────────────
    function classeLog(ligne) {
        if (ligne.includes("[STM32]")) return "log-stm";
        if (ligne.includes("[RPi]"))   return "log-rpi";
        if (ligne.includes("[ERR]"))   return "log-err";
        return "log-info";
    }

    function setFiltre(f) {
        filtre_actif = f;
        document.querySelectorAll(".filtre-btn").forEach(b => b.classList.remove("actif"));
        document.getElementById("f-" + (f === "all" ? "all" : f === "STM32" ? "stm" : f === "RPi" ? "rpi" : "err"))
                .classList.add("actif");
        afficherLignes();
    }

    function afficherLignes() {
        const box = document.getElementById("terminal-box");
        const lignes = filtre_actif === "all"
            ? toutes_les_lignes
            : toutes_les_lignes.filter(l => l.includes("[" + filtre_actif + "]"));

        box.innerHTML = lignes.map(l =>
            `<div class="${classeLog(l)}">${l}</div>`
        ).join("");
        box.scrollTop = box.scrollHeight;
    }

    function viderTerminal() {
        toutes_les_lignes = [];
        afficherLignes();
    }

    // ── Fetch état ───────────────────────────────────────────────
    async function fetchEtat() {
        try {
            const resp = await fetch("/etat");
            const data = await resp.json();

            document.getElementById("val-x").textContent      = data.robot.x.toFixed(1);
            document.getElementById("val-y").textContent      = data.robot.y.toFixed(1);
            document.getElementById("val-angle").textContent  = data.robot.angle_deg.toFixed(1);
            document.getElementById("val-caisses").textContent= data.robot.nb_caisses;
            document.getElementById("status").textContent     = "màj " + new Date().toLocaleTimeString();

            const canvas = document.getElementById("carte");
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = "#0f3460";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            data.exclusion.forEach(z     => dessinerZone(ctx, z, "#888",    z.name));
            data.nids.forEach(z          => dessinerZone(ctx, z, "#f5c518", z.name));
            data.garde_mangers.forEach(z => dessinerZone(ctx, z, "#4caf50", z.name));
            data.caisses.forEach(z       => dessinerZone(ctx, z, "#f5c518", "C"));
            dessinerRobot(ctx, data.robot);

        } catch(e) {
            document.getElementById("status").textContent = "erreur connexion";
        }
    }

    // ── Fetch logs ───────────────────────────────────────────────
    async function fetchLogs() {
        try {
            const resp = await fetch("/logs");
            const data = await resp.json();
            toutes_les_lignes = data.logs;
            afficherLignes();
        } catch(e) {}
    }

    setInterval(fetchEtat, 200);
    setInterval(fetchLogs, 300);

    // ── Commandes ────────────────────────────────────────────────
    async function envoyerCommande(action) {
        const dist = parseFloat(document.getElementById("distance").value) || 10;
        await fetch("/commande", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: action, distance: dist })
        });
    }

    const boutons = {
        "btn-avant":       "avancer",
        "btn-arriere":     "reculer",
        "btn-gauche":      "gauche",
        "btn-droite":      "droite",
        "btn-diag-gauche": "diag_gauche",
        "btn-diag-droite": "diag_droite",
        "btn-rot-gauche":  "rot_gauche",
        "btn-rot-droite":  "rot_droite",
        "btn-pince-open":  "pince_open",
        "btn-pince-close": "pince_close",
    };

    Object.entries(boutons).forEach(([id, action]) => {
        document.getElementById(id).addEventListener("click", () => envoyerCommande(action));
    });

    const touches = {
        "ArrowUp":    "avancer",
        "ArrowDown":  "reculer",
        "ArrowLeft":  "gauche",
        "ArrowRight": "droite",
        "a":          "rot_gauche",
        "e":          "rot_droite",
    };
    document.addEventListener("keydown", (ev) => {
        if (touches[ev.key]) envoyerCommande(touches[ev.key]);
    });
</script>
</body>
</html>
"""


class AffichageWeb:
    def __init__(self, carte, robot, port=5000):
        self.carte = carte
        self.robot = robot
        self.port  = port
        self.app   = Flask(__name__)
        self._setup_routes()

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

    def _setup_routes(self):

        @self.app.route("/")
        def index():
            return render_template_string(HTML_PAGE)

        @self.app.route("/etat")
        def etat():
            return jsonify({
                "robot": {
                    "x":          self.robot.x,
                    "y":          self.robot.y,
                    "angle_deg":  self.robot.angle_deg,
                    "angle_rad":  math.radians(self.robot.angle_deg),
                    "nb_caisses": self.robot.nb_caisses(),
                    "width":  32,
                    "height": 28,
                },
                "nids":          [self._z2d(z) for z in self.carte.nids.values()],
                "garde_mangers": [self._z2d(z) for z in self.carte.garde_mangers.values()],
                "exclusion":     [self._z2d(z) for z in self.carte.exclusion.values()],
                "caisses":       [self._z2d(z) for z in self.carte.caisses.values()],
            })

        @self.app.route("/logs")
        def logs():
            return jsonify({"logs": list(log_buffer)})

        @self.app.route("/commande", methods=["POST"])
        def commande():
            data     = request.get_json()
            action   = data.get("action", "")
            distance = float(data.get("distance", 10))

            log("RPi", f"Commande reçue : {action} {distance}cm")

            actions = {
                "avancer":     lambda: self.robot.avancer(distance),
                "reculer":     lambda: self.robot.reculer(distance),
                "gauche":      lambda: self.robot.gauche(distance),
                "droite":      lambda: self.robot.droite(distance),
                "diag_gauche": lambda: self.robot.diagonale_gauche(distance),
                "diag_droite": lambda: self.robot.diagonale_droite(distance),
                "rot_gauche":  lambda: self.robot.rotation_gauche(distance),
                "rot_droite":  lambda: self.robot.rotation_droite(distance),
                "pince_open":  lambda: self.robot.ouvrir_pince(),
                "pince_close": lambda: self.robot.fermer_pince(),
            }

            if action in actions:
                actions[action]()
                return jsonify({"ok": True})

            return jsonify({"ok": False, "erreur": "action inconnue"}), 400

    def run(self):
        t = threading.Thread(
            target=lambda: self.app.run(
                host="0.0.0.0", port=self.port,
                debug=False, use_reloader=False
            ),
            daemon=True
        )
        t.start()
        print(f"Dashboard : http://localhost:{self.port}")


