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
let cameras_initialized = false;

// Charge l'image de fond
const img = new Image();
img.onload = () => { bgImage = img; };
img.src = "/bg_image";

// ── Dessin carte ─────────────────────────────────────────────
function dessiner(data) {
    const canvas = document.getElementById("carte");
    canvas.width  = CANVAS_W;
    canvas.height = CANVAS_H;

    const ctx = canvas.getContext("2d");
    const scaleX = CANVAS_W / TERRAIN_W;
    const scaleY = CANVAS_H / TERRAIN_H;

    if (bgImage) {
        ctx.drawImage(bgImage, 0, 0, CANVAS_W, CANVAS_H);
    } else {
        ctx.fillStyle = "#0f3460";
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
    }

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
        const [cx, cy] = toPx(zone.center_x, zone.center_y);
        ctx.fillStyle = "#111";
        ctx.font = "bold 16px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(zone.name, cx, cy);
    }

    function drawCercle(zone, marge, couleur) {
        const [cx, cy] = toPx(zone.center_x, zone.center_y);
        const rayon_cm = Math.sqrt((zone.width/2)**2 + (zone.height/2)**2) + marge;
        const rayon_px = rayon_cm * scaleX;
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
            i === 0 ? ctx.moveTo(cx+rx, cy-ry) : ctx.lineTo(cx+rx, cy-ry);
        });
        ctx.closePath();
        ctx.fillStyle = "rgba(70,70,70,0.9)";
        ctx.fill();
        ctx.strokeStyle = "#222";
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + w2 * Math.cos(angle), cy - w2 * Math.sin(angle));
        ctx.strokeStyle = "#e94560";
        ctx.lineWidth = 5;
        ctx.stroke();
    }

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
    drawRobot(data.robot);
}

// ── Fetch état ───────────────────────────────────────────────
async function fetchEtat() {
    try {
        const resp = await fetch("/etat");
        dernier_etat = await resp.json();
        const d = dernier_etat;

        if (!cameras_initialized) {
            initCameras(d.nb_cameras || 0);
            cameras_initialized = true;
        }

        document.getElementById("val-x").textContent      = d.robot.x.toFixed(1);
        document.getElementById("val-y").textContent      = d.robot.y.toFixed(1);
        document.getElementById("val-angle").textContent  = d.robot.angle_deg.toFixed(1);
        document.getElementById("status").textContent     = "màj " + new Date().toLocaleTimeString();

        if (!d.strategie_en_cours) {
            [1,2,3].forEach(n => {
                const b = document.getElementById("btn-strat" + n);
                b.classList.remove("running");
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

function initCameras(count) {
    const activeCount = Math.max(0, Math.min(count || 0, 3));

    for (let i = 0; i < 3; i++) {
        const bloc = document.getElementById(`cam-bloc-${i}`);
        const feed = document.getElementById(`cam-feed-${i}`);
        const img         = document.getElementById(`cam-img-${i}`);
        const placeholder = document.getElementById(`cam-placeholder-${i}`);
        const status      = document.getElementById(`cam-status-${i}`);

        if (i >= activeCount) {
            if (bloc) bloc.style.display = "none";
            continue;
        }

        const toggleExpand = (event) => {
            event.stopPropagation();
            setExpandedCamera(i);
        };

        bloc.addEventListener("click", toggleExpand);
        feed.addEventListener("click", toggleExpand);

        img.onload = () => {
            img.style.display = "block";
            placeholder.style.display = "none";
            status.className = "cam-status live";
        };
        img.onerror = () => {
            img.style.display = "none";
            placeholder.style.display = "flex";
            status.className = "cam-status err";
        };
        img.src = `/camera_stream/${i}`;
    }

    const select = document.getElementById("calib-camera");
    if (select) {
        select.innerHTML = "";
        for (let i = 0; i < activeCount; i++) {
            const opt = document.createElement("option");
            opt.value = String(i);
            opt.textContent = "Caméra " + (i + 1);
            select.appendChild(opt);
        }
        select.disabled = activeCount === 0;
    }
}

function getCalibSlot() {
    const select = document.getElementById("calib-camera");
    if (!select || select.disabled) return null;
    const slot = parseInt(select.value, 10);
    return Number.isNaN(slot) ? null : slot;
}

async function fetchCalibrationStatus() {
    const slot = getCalibSlot();
    const statusEl = document.getElementById("calib-status");
    if (slot === null || !statusEl) {
        if (statusEl) statusEl.textContent = "Aucune caméra";
        return;
    }

    try {
        const resp = await fetch("/calibration/status");
        const data = await resp.json();
        const entry = (data.calibrations || []).find(c => c.slot === slot);
        if (!entry) {
            statusEl.textContent = "Caméra indisponible";
            return;
        }

        const running = entry.running ? " (en cours)" : "";
        const error = entry.last_error ? ` | ${entry.last_error}` : "";
        const result = entry.last_result ? ` | ${entry.last_result}` : "";
        statusEl.textContent = `Photos: ${entry.count}${running}${error}${result}`;
    } catch (e) {
        statusEl.textContent = "Statut calibration indisponible";
    }
}

async function calibReset() {
    const slot = getCalibSlot();
    if (slot === null) return;
    await fetch("/calibration/reset", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({slot})
    });
    fetchCalibrationStatus();
}

async function calibCapture() {
    const slot = getCalibSlot();
    if (slot === null) return;
    const resp = await fetch("/calibration/capture", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({slot})
    });
    if (resp.ok) {
        const data = await resp.json();
        if (data.ok) log_local("RPi", data.message || "Photo calibration enregistrée");
        else log_local("ERR", data.error || "Capture calibration échouée");
    }
    fetchCalibrationStatus();
}

async function calibRun() {
    const slot = getCalibSlot();
    if (slot === null) return;
    const resp = await fetch("/calibration/run", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({slot})
    });
    if (resp.ok) {
        const data = await resp.json();
        if (data.ok) log_local("RPi", data.message || "Calibration lancée");
        else log_local("ERR", data.error || "Calibration échouée");
    }
    fetchCalibrationStatus();
}

let cameraExpandedIndex = null;

function setExpandedCamera(index) {
    const body = document.body;
    const blocs = [0, 1, 2].map(i => document.getElementById(`cam-bloc-${i}`));

    cameraExpandedIndex = (cameraExpandedIndex === index) ? null : index;
    body.classList.toggle("camera-expanded", cameraExpandedIndex !== null);

    blocs.forEach((bloc, i) => {
        if (!bloc) return;
        bloc.classList.toggle("expanded", cameraExpandedIndex === i);
    });
}

function closeExpandedCamera() {
    const body = document.body;
    const blocs = [0, 1, 2].map(i => document.getElementById(`cam-bloc-${i}`));

    cameraExpandedIndex = null;
    body.classList.remove("camera-expanded");
    blocs.forEach(bloc => {
        if (bloc) bloc.classList.remove("expanded");
    });
}

window.addEventListener("keydown", ev => {
    if (ev.key === "Escape") {
        closeExpandedCamera();
    }
});

setInterval(fetchEtat,    150);
setInterval(fetchLogs,    400);
setInterval(fetchCalibrationStatus, 800);
window.addEventListener("load", fetchEtat);

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
const POSES_DEPART = {
    yellow: { x: 16,   y: 184, angle: 270   },
    blue:   { x: 284, y: 184, angle: 270  },
};

async function setTeam(team) {
    document.getElementById("btn-jaune").classList.toggle("actif", team === "yellow");
    document.getElementById("btn-bleu").classList.toggle("actif",  team === "blue");
    const resp = await fetch("/set_team", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({team})
    });
    const data = await resp.json();
    if (data.ok) {
        const p = POSES_DEPART[team];
        log_local("RPi", `Équipe ${team} → robot nid (${p.x}, ${p.y}) angle=${p.angle}°`);
    }
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

// ── Navigation coordonnées / angle ───────────────────────────
async function allerACoord() {
    const x = parseFloat(document.getElementById("nav-x").value);
    const y = parseFloat(document.getElementById("nav-y").value);
    if (isNaN(x) || isNaN(y)) return;
    await fetch("/nav_coord", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({x, y})
    });
    log_local("RPi", `Aller à (${x}, ${y})`);
}

async function tournerVersAngle() {
    const angle = parseFloat(document.getElementById("nav-angle").value);
    if (isNaN(angle)) return;
    await fetch("/nav_angle", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({angle})
    });
    log_local("RPi", `Tourner vers ${angle}°`);
}

function log_local(source, msg) {
    toutes_les_lignes.push(`[${source}] ${msg}`);
    afficherLignes();
}

// ── Commandes ────────────────────────────────────────────────
async function envoyerCommande(action) {
    const dist = parseFloat(document.getElementById("distance").value) || 10;
    
    let optVal = 0;
    const checkbox = document.getElementById("opt-recup");
    if (checkbox) {
        optVal = checkbox.checked ? 1 : 0;
    }

    await fetch("/commande", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            action: action, 
            distance: dist,
            option: optVal
        })
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
    "btn-pince-close": "Pince Navigation",
    "btn-pince-homo":  "pince_homologation",
    "btn-stockage":    "stockage",
    "btn-lacher":      "lacher_caisse",
    "btn-stop":        "stop"
};

Object.entries(boutons).forEach(([id, action]) => {
    const btn = document.getElementById(id);
    if (btn) {
        btn.addEventListener("click", () => envoyerCommande(action));
    }
});

// Pince une fois (route dédiée)
async function envoyerPinceOnce() {
    const checkbox = document.getElementById("opt-recup");
    const rotation = checkbox && checkbox.checked ? 1 : 0;
    const resp = await fetch("/pince_once", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({rotation})
    });
    if (resp.ok) {
        log_local("RPi", "Pince une fois lancé");
    } else {
        const data = await resp.json().catch(() => ({}));
        log_local("ERR", `Pince une fois erreur: ${data.error || resp.status}`);
    }
}

const btnPinceOnce = document.getElementById("btn-pince-once");
if (btnPinceOnce) btnPinceOnce.addEventListener("click", envoyerPinceOnce);

const touches = {
    ArrowUp:"avancer", ArrowDown:"reculer",
    ArrowLeft:"gauche", ArrowRight:"droite",
    a:"rot_gauche", e:"rot_droite"
};
document.addEventListener("keydown", ev => {
    if (touches[ev.key] && ev.target.tagName !== 'INPUT') envoyerCommande(touches[ev.key]);
});
