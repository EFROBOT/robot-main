import threading
import math
import base64
import os
from collections import deque
from flask import Flask, jsonify, render_template_string, request, send_file
from .Map import Map

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
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        .top {
            display: flex;
            gap: 16px;
            padding: 16px;
            flex: 1;
            overflow: hidden;
        }
        .panneau {
            background: #16213e;
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        h2 {
            font-size: 13px;
            color: #a0a8c0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 10px;
            margin-bottom: 4px;
        }
        h2:first-child { margin-top: 0; }
        .valeur { font-size: 24px; font-weight: bold; color: #e94560; }
        .label  { font-size: 11px; color: #555; margin-bottom: 4px; }
        #status { font-size: 11px; color: #444; margin-top: 6px; }

        /* Carte canvas */
        .carte-wrap {
            flex: 1;
            background: #16213e;
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        #carte {
            /* On laisse la résolution interne à 1200x800, mais on force l'affichage à garder le ratio */
            width: 100%;
            height: 100%;
            max-height: 100%;
            object-fit: contain; 
            border-radius: 8px;
            display: block;
        }

        /* Team */
        .team-row { display: flex; gap: 8px; margin-bottom: 4px; }
        .team-btn {
            flex: 1;
            padding: 8px 0;
            border-radius: 8px;
            border: 2px solid transparent;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.15s;
        }
        .team-btn.jaune { background: #2a2200; color: #f5c518; border-color: #f5c518; }
        .team-btn.jaune.actif { background: #f5c518; color: #111; }
        .team-btn.bleu  { background: #001233; color: #4fc3f7; border-color: #4fc3f7; }
        .team-btn.bleu.actif  { background: #4fc3f7; color: #111; }

        /* Manette */
        .manette {
            display: grid;
            grid-template-columns: repeat(3, 52px);
            grid-template-rows:    repeat(3, 52px);
            gap: 5px;
            margin: 4px 0;
        }
        .btn {
            width: 52px; height: 52px;
            border-radius: 8px;
            border: none;
            background: #0f3460;
            color: #eee;
            font-size: 18px;
            cursor: pointer;
            user-select: none;
            transition: background 0.1s;
        }
        .btn:active { background: #e94560; }
        .btn.vide { background: transparent; cursor: default; pointer-events: none; }
        .btn.wide { width: auto; padding: 0 12px; }

        .distance-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 4px 0;
        }
        .distance-row input {
            width: 60px; padding: 5px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #0f3460;
            color: #eee;
            font-size: 13px;
        }
        .distance-row label { font-size: 11px; color: #666; }

        /* Stratégie */
        .strat-btn {
            width: 100%;
            padding: 9px;
            border-radius: 8px;
            border: none;
            background: #1b4332;
            color: #a5d6a7;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 6px;
            transition: background 0.15s;
        }
        .strat-btn:hover  { background: #2d6a4f; }
        .strat-btn:active { background: #e94560; color: #fff; }
        .strat-btn.running { background: #e94560; color: #fff; }

        /* Terminal */
        .terminal-wrap {
            height: 180px;
            background: #16213e;
            border-radius: 12px;
            padding: 12px 16px;
            margin: 0 16px 16px;
            display: flex;
            flex-direction: column;
        }
        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .filtre-btn {
            padding: 3px 10px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #0f3460;
            color: #aaa;
            font-size: 11px;
            cursor: pointer;
        }
        .filtre-btn.actif { background: #e94560; color: #fff; border-color: #e94560; }
        #terminal-box {
            background: #0a0a1a;
            border-radius: 6px;
            padding: 8px 10px;
            flex: 1;
            overflow-y: auto;
            font-family: monospace;
            font-size: 11px;
            line-height: 1.6;
        }
        .log-stm  { color: #4fc3f7; }
        .log-rpi  { color: #a5d6a7; }
        .log-err  { color: #e94560; }
        .log-info { color: #aaa; }

        .btn.stop { 
        background: #e94560; 
        font-weight: bold; 
        font-size: 14px; 
        }

        .btn.stop:hover { background: #ff2e63; }
    </style>
</head>
<body>

<div class="top">
    <div class="panneau" style="width:180px; min-width:180px;">
        <h2>Équipe</h2>
        <div class="team-row">
            <button class="team-btn jaune actif" id="btn-jaune" onclick="setTeam('yellow')">🟡 Jaune</button>
            <button class="team-btn bleu"         id="btn-bleu"  onclick="setTeam('blue')">🔵 Bleu</button>
        </div>

        <h2>Position</h2>
        <div class="valeur" id="val-x">--</div><div class="label">X (cm)</div>
        <div class="valeur" id="val-y">--</div><div class="label">Y (cm)</div>
        <div class="valeur" id="val-angle">--</div><div class="label">Angle (°)</div>

        <h2>Inventaire</h2>
        <div class="valeur" id="val-caisses">--</div><div class="label">caisses</div>
        <div id="status">en attente...</div>

        <h2>Stratégie</h2>
        <button class="strat-btn" id="btn-strat1" onclick="lancerStrategie(1)">▶ Stratégie 1</button>
        <button class="strat-btn" id="btn-strat2" onclick="lancerStrategie(2)">▶ Stratégie 2</button>
        <button class="strat-btn" id="btn-strat3" onclick="lancerStrategie(3)">▶ Stratégie 3</button>
    </div>

    <div class="carte-wrap">
        <canvas id="carte"></canvas>
    </div>

    <div class="panneau" style="width:200px; min-width:200px;">
        <h2>Télécommande</h2>
        <div class="distance-row">
            <label>Distance (cm)</label>
            <input type="number" id="distance" value="10" min="1" max="200"/>
        </div>
        <div class="manette">
            <button class="btn" id="btn-diag-gauche">↖</button>
            <button class="btn" id="btn-avant">↑</button>
            <button class="btn" id="btn-diag-droite">↗</button>

            <button class="btn" id="btn-gauche">←</button>
            <button class="btn stop" id="btn-stop">STOP</button>
            <button class="btn" id="btn-droite">→</button>

            <button class="btn" id="btn-rot-gauche">↺</button>
            <button class="btn" id="btn-arriere">↓</button>
            <button class="btn" id="btn-rot-droite">↻</button>
        </div>

        <h2>Pince</h2>
        <div style="display:flex; gap:6px;">
            <button class="btn wide" id="btn-pince-open">Ouvrir</button>
            <button class="btn wide" id="btn-pince-close">Fermer</button>
        </div>
    </div>
</div>

<div class="terminal-wrap">
    <div class="terminal-header">
        <h2 style="margin:0">Terminal</h2>
        <div style="display:flex; gap:6px;">
            <button class="filtre-btn actif" id="f-all"  onclick="setFiltre('all')">Tout</button>
            <button class="filtre-btn"       id="f-stm"  onclick="setFiltre('STM32')">STM32</button>
            <button class="filtre-btn"       id="f-rpi"  onclick="setFiltre('RPi')">RPi</button>
            <button class="filtre-btn"       id="f-err"  onclick="setFiltre('ERR')">Erreurs</button>
            <button class="filtre-btn"       onclick="viderTerminal()">🗑</button>
        </div>
    </div>
    <div id="terminal-box"></div>
</div>

<script>
// Dimensions physiques (en cm)
const TERRAIN_W = 300;
const TERRAIN_H = 200;

// Dimensions de l'image (en pixels)
const CANVAS_W = 1200;
const CANVAS_H = 800;

let bgImage = null;
let filtre_actif = "all";
let toutes_les_lignes = [];
let dernier_etat = null;

// Charge l'image de fond
const img = new Image();
img.onload = () => { bgImage = img; };
img.src = "/bg_image";

// ── Dessin carte ─────────────────────────────────────────────
function dessiner(data) {
    const canvas = document.getElementById("carte");
    
    // On verrouille la résolution interne (indépendamment de la taille sur l'écran)
    canvas.width  = CANVAS_W;
    canvas.height = CANVAS_H;

    const ctx = canvas.getContext("2d");
    
    // Échelle : 1200px / 300cm = 4 pixels par cm
    const scaleX = CANVAS_W / TERRAIN_W;
    const scaleY = CANVAS_H / TERRAIN_H;

    // Fond image ou couleur
    if (bgImage) {
        ctx.drawImage(bgImage, 0, 0, CANVAS_W, CANVAS_H);
    } else {
        ctx.fillStyle = "#0f3460";
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
    }

    // Le repère (0,0) est en bas à gauche de l'écran.
    function toPx(x, y) {
        return [x * scaleX, CANVAS_H - (y * scaleY)];
    }

    function drawZone(zone, couleur, alpha=0.55) {
        const [px, py] = toPx(zone.x_min, zone.y_max);
        const w = zone.width  * scaleX;
        const h = zone.height * scaleY;
        
        ctx.globalAlpha = alpha;
        ctx.fillStyle = couleur;
        ctx.fillRect(px, py, w, h);
        
        ctx.globalAlpha = 1.0;
        ctx.strokeStyle = "rgba(0,0,0,0.6)";
        ctx.lineWidth = 2;
        ctx.strokeRect(px, py, w, h);
        
        // Texte
        const [cx, cy] = toPx(zone.center_x, zone.center_y);
        ctx.fillStyle = "#111";
        ctx.font = `bold 16px Arial`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(zone.name, cx, cy);
    }

    function drawCercle(zone, marge, couleur) {
        const [cx, cy] = toPx(zone.center_x, zone.center_y);
        const rayon_cm = Math.sqrt((zone.width/2)**2 + (zone.height/2)**2) + marge;
        const rayon_px = rayon_cm * scaleX; // (X et Y ont la même échelle de 4)
        
        ctx.beginPath();
        ctx.arc(cx, cy, rayon_px, 0, 2 * Math.PI);
        ctx.strokeStyle = couleur;
        ctx.lineWidth = 3;
        ctx.globalAlpha = 0.8;
        ctx.stroke();
        ctx.globalAlpha = 1.0;
    }

    function drawRobot(robot) {
        const angle = robot.angle_rad;
        const [cx, cy] = toPx(robot.x, robot.y);
        const w2 = (robot.width  / 2) * scaleX;
        const h2 = (robot.height / 2) * scaleY;

        const coins = [[w2,h2],[-w2,h2],[-w2,-h2],[w2,-h2]];
        
        ctx.beginPath();
        coins.forEach(([lx, ly], i) => {
            const rx = lx * Math.cos(angle) - ly * Math.sin(angle);
            const ry = lx * Math.sin(angle) + ly * Math.cos(angle);
            // Ry est soustrait car l'axe Y canvas va vers le bas
            i === 0 ? ctx.moveTo(cx+rx, cy-ry) : ctx.lineTo(cx+rx, cy-ry);
        });
        ctx.closePath();
        
        ctx.fillStyle = "rgba(70,70,70,0.9)";
        ctx.fill();
        ctx.strokeStyle = "#222";
        ctx.lineWidth = 3;
        ctx.stroke();

        // Trait rouge = avant
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + w2 * Math.cos(angle), cy - w2 * Math.sin(angle));
        ctx.strokeStyle = "#e94560";
        ctx.lineWidth = 5;
        ctx.stroke();
    }

    // Dessin des zones
    data.ramassage.forEach(z     => drawCercle(z, 7,  "deepskyblue"));
    data.exclusion.forEach(z     => drawZone(z, "#aaaaaa"));
    data.nids.forEach(z          => {
        const c = z.name.startsWith("NJ") ? "#f5c518" : "#4fc3f7";
        drawZone(z, c);
    });
    data.garde_mangers.forEach(z => {
        drawCercle(z, 5, "#4fc3f7");
        drawZone(z, "#4caf50");
    });
    data.caisses.forEach(z       => drawZone(z, "#f5c518", 0.9));
    
    // Dessin du robot
    drawRobot(data.robot);
}

// ── Fetch état ───────────────────────────────────────────────
async function fetchEtat() {
    try {
        const resp = await fetch("/etat");
        dernier_etat = await resp.json();
        const d = dernier_etat;

        document.getElementById("val-x").textContent      = d.robot.x.toFixed(1);
        document.getElementById("val-y").textContent      = d.robot.y.toFixed(1);
        document.getElementById("val-angle").textContent  = d.robot.angle_deg.toFixed(1);
        document.getElementById("val-caisses").textContent = d.robot.nb_caisses;
        document.getElementById("status").textContent     = "màj " + new Date().toLocaleTimeString();

        if (!d.strategie_en_cours) {
            [1,2,3].forEach(n => {
                const b = document.getElementById("btn-strat" + n);
                b.classList.remove("running");
                b.textContent = "▶ Stratégie " + n;
            });
        }

        dessiner(d);
    } catch(e) {
        document.getElementById("status").textContent = "erreur connexion";
    }
}

// ── Fetch logs ───────────────────────────────────────────────
async function fetchLogs() {
    try {
        const resp = await fetch("/logs");
        toutes_les_lignes = (await resp.json()).logs;
        afficherLignes();
    } catch(e) {}
}

setInterval(fetchEtat, 100);
setInterval(fetchLogs, 300);

// ── Terminal ─────────────────────────────────────────────────
function classeLog(l) {
    if (l.includes("[STM32]")) return "log-stm";
    if (l.includes("[RPi]"))   return "log-rpi";
    if (l.includes("[ERR]"))   return "log-err";
    return "log-info";
}
function setFiltre(f) {
    filtre_actif = f;
    document.querySelectorAll(".filtre-btn").forEach(b => b.classList.remove("actif"));
    const ids = {all:"f-all", STM32:"f-stm", RPi:"f-rpi", ERR:"f-err"};
    document.getElementById(ids[f] || "f-all").classList.add("actif");
    afficherLignes();
}
function afficherLignes() {
    const box = document.getElementById("terminal-box");
    const lignes = filtre_actif === "all"
        ? toutes_les_lignes
        : toutes_les_lignes.filter(l => l.includes("[" + filtre_actif + "]"));
    box.innerHTML = lignes.map(l => `<div class="${classeLog(l)}">${l}</div>`).join("");
    box.scrollTop = box.scrollHeight;
}
function viderTerminal() { toutes_les_lignes = []; afficherLignes(); }

// ── Team ─────────────────────────────────────────────────────
async function setTeam(team) {
    document.getElementById("btn-jaune").classList.toggle("actif", team === "yellow");
    document.getElementById("btn-bleu").classList.toggle("actif",  team === "blue");
    await fetch("/set_team", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({team})
    });
}

// ── Stratégie ────────────────────────────────────────────────
async function lancerStrategie(num) {
    const btn = document.getElementById("btn-strat" + num);
    btn.classList.add("running");
    btn.textContent = "⏳ En cours...";
    await fetch("/strategie", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({numero: num})
    });
}

// ── Commandes ────────────────────────────────────────────────
async function envoyerCommande(action) {
    const dist = parseFloat(document.getElementById("distance").value) || 10;
    await fetch("/commande", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({action, distance: dist})
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
    "btn-stop" : "stop",
};
Object.entries(boutons).forEach(([id, action]) => {
    document.getElementById(id).addEventListener("click", () => envoyerCommande(action));
});

const touches = {
    ArrowUp:"avancer", ArrowDown:"reculer",
    ArrowLeft:"gauche", ArrowRight:"droite",
    a:"rot_gauche", e:"rot_droite"
};
document.addEventListener("keydown", ev => {
    if (touches[ev.key] && ev.target.tagName !== 'INPUT') envoyerCommande(touches[ev.key]);
});
</script>
</body>
</html>
"""


class AffichageWeb:
    def __init__(self, carte, robot, strategy_class, port=5000, image_path=None):
        self.carte           = carte
        self.robot           = robot
        self.strategy_class  = strategy_class
        self.port            = port
        self.image_path      = image_path
        self.app             = Flask(__name__)
        self.strategie_en_cours = False
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

        @self.app.route("/bg_image")
        def bg_image():
            # On remonte de 2 dossiers depuis AffichageWeb.py (modules -> src -> robot-main)
            dossier_racine = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            chemin_image = os.path.join(dossier_racine, 'img', 'table_FINALE_1.0-1.png')
            
            if os.path.exists(chemin_image):
                return send_file(chemin_image)
            
            log("ERR", f"Image introuvable au chemin absolu : {chemin_image}")
            return "", 404

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
                "ramassage":     [self._z2d(z) for z in self.carte.ramassage.values()],
                "caisses":       [self._z2d(z) for z in self.carte.caisses.values()],
                "strategie_en_cours": self.strategie_en_cours,
            })

        @self.app.route("/logs")
        def logs():
            return jsonify({"logs": list(log_buffer)})

        @self.app.route("/set_team", methods=["POST"])
        def set_team():
            team = request.get_json().get("team", "yellow")
            
            from Map import Map
            self.carte = Map(team)
            
            log("RPi", f"Équipe changée : {team}")
            return jsonify({"ok": True})

        @self.app.route("/strategie", methods=["POST"])
        def strategie():
            numero = request.get_json().get("numero", 1)
            if self.strategie_en_cours:
                return jsonify({"ok": False, "erreur": "déjà en cours"})

            def lancer():
                self.strategie_en_cours = True
                log("RPi", f"Stratégie {numero} lancée")
                try:
                    cerveau = self.strategy_class(carte=self.carte, robot=self.robot, sim=False)
                    {1: cerveau.strategy_1, 2: cerveau.strategy_2, 3: cerveau.strategy_3}[numero]()
                except Exception as e:
                    log("ERR", str(e))
                finally:
                    self.strategie_en_cours = False
                    log("RPi", f"Stratégie {numero} terminée")

            threading.Thread(target=lancer, daemon=True).start()
            return jsonify({"ok": True})

        @self.app.route("/commande", methods=["POST"])
        def commande():
            data     = request.get_json()
            action   = data.get("action", "")
            distance = float(data.get("distance", 10))
            log("RPi", f"Commande : {action} {distance}cm")

            actions = {
                "avancer"    : lambda: self.robot.avancer(distance),
                "reculer"    : lambda: self.robot.reculer(distance),
                "gauche"     : lambda: self.robot.gauche(distance),
                "droite"     : lambda: self.robot.droite(distance),
                "diag_gauche": lambda: self.robot.diagonale_gauche(distance),
                "diag_droite": lambda: self.robot.diagonale_droite(distance),
                "rot_gauche" : lambda: self.robot.rotation_gauche(distance),
                "rot_droite" : lambda: self.robot.rotation_droite(distance),
                "pince_open" : lambda: self.robot.ouvrir_pince(),
                "pince_close": lambda: self.robot.fermer_pince(),
                "stop"       : lambda: self.robot.stop(),
            }
            if action in actions:
                actions[action]()
                return jsonify({"ok": True})
            return jsonify({"ok": False}), 400

    def run(self):
        log("RPi", f"Dashboard : http://localhost:{self.port}")
        self.app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)