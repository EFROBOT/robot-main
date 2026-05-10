import cv2
from flask import Flask, Response
from core.camera import Camera
import numpy as np

app = Flask(__name__)

# Tes ID corriges : 0 (Nappe), 1 (USB) et 3 (USB)
CAMERA_IDS = [0, 1, 3]
cameras_ouvertes = {}

print("--- Initialisation des cameras ---")
for cid in CAMERA_IDS:
    # Creation de l'objet camera
    cam = Camera(camera_id=cid)
    
    if not cam.load_calibration():
        cam.use_default_calibration()
        
    # ==========================================
    # LOGIQUE ADAPTATIVE SANS TOUCHER AU CORE
    # ==========================================
    if cid == 0:
        # Configuration legere speciale pour la nappe
        cam.width = 640
        cam.height = 480
        cam.fps = 30
    else:
        # Configuration HD pour les cameras USB
        cam.width = 1280
        cam.height = 720
        cam.fps = 30
        
    # On ouvre la camera (la fonction interne va utiliser nos nouvelles dimensions)
    if cam.open():
        # Desactivation du format MJPG pour la camera nappe
        if cid == 0:
            # Mettre le code FOURCC a 0 force OpenCV a utiliser le format brut (RAW/YUYV)
            cam.cap.set(cv2.CAP_PROP_FOURCC, 0)
            
        cameras_ouvertes[cid] = cam
        print(f"[OK] Camera {cid} prete.")
    else:
        print(f"[ERREUR] Impossible d'ouvrir la camera {cid}.")

def generer_flux_video(camera_id):
    """Capture et traite l'image pour une camera specifique"""
    cam = cameras_ouvertes.get(camera_id)
    if not cam:
        return

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            continue

        # --- TRAITEMENT D'IMAGE ---
        # 1. Marqueurs Aruco
        markers = cam.aruco.detect_markers(frame)
        cam.aruco.draw_marker(frame, markers)

        # 2. Zone de ramassage
        zone = cam.aruco.detect_zone_ramassage(frame)
        if zone:
            corners = np.int32(zone["corners"]).reshape(-1, 1, 2)
            cv2.polylines(frame, [corners], True, (0, 255, 0), 3, cv2.LINE_AA)
            tx, ty = int(zone["corners"][0][0]), int(zone["corners"][0][1] - 10)
            cv2.putText(frame, f"Zone: {zone['distance']:.1f}cm", (tx, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        # --------------------------

        # Encodage pour le web
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Page web principale qui affiche toutes les cameras"""
    html = '''
    <html>
        <head>
            <title>Dashboard Robot EF</title>
            <style>
                body { background: #222; color: white; text-align: center; font-family: sans-serif; }
                .grid { display: flex; justify-content: center; flex-wrap: wrap; gap: 20px; padding: 20px; }
                .cam-container { background: #333; padding: 10px; border-radius: 10px; }
                img { border: 2px solid #555; border-radius: 5px; width: 400px; }
            </style>
        </head>
        <body>
            <h1>Vision Robot EF (En Direct)</h1>
            <div class="grid">
    '''
    
    # On ajoute dynamiquement une balise image pour chaque camera
    for cid in cameras_ouvertes.keys():
        html += f'''
                <div class="cam-container">
                    <h2>Camera {cid}</h2>
                    <img src="/video_feed/{cid}">
                </div>
        '''
        
    html += '''
            </div>
        </body>
    </html>
    '''
    return html

@app.route('/video_feed/<int:camera_id>')
def video_feed(camera_id):
    """Route dynamique pour chaque camera"""
    return Response(generer_flux_video(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print(f"--- SERVEUR DEMARRE ---")
    print(f"Ouvrez ce lien sur votre PC : http://192.168.1.16:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)