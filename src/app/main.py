""""""

import time
import RPi.GPIO as GPIO

from app.options import Options
from core.robot import Robot
from core.strategy import Strategy
from world.map import Map

from web.dashboard import AffichageWeb


def main_bis():

    devices = Options.init_devices()

    if devices["cameras"]:
        print(f"Caméras détectées : {devices['cameras']}")
    else:
        print("Aucune caméra détectée automatiquement.")

    utiliser_camera = Options.demander_oui_non("Activer la caméra ?", defaut=bool(devices["cameras"]))
    camera_ids = []
    if utiliser_camera:
        camera_ids = Options.demander_liste_cameras(devices["cameras"])
        if not camera_ids:
            print("Aucune caméra valide sélectionnée, désactivation de la caméra.")
            utiliser_camera = False



    activer_aruco = utiliser_camera and Options.demander_oui_non(
        "Activer la détection ArUco sur le serveur web ?",
        defaut=True,
    )

    connecter_robot = Options.demander_oui_non("Connecter le robot STM32 ?", defaut=bool(devices["stm32"]))
    if connecter_robot and not devices["stm32"]:
        print("STM32 non détectée, connexion robot impossible.")
        connecter_robot = False

    # Interupteur
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    x = 0
    
    try:
        while x < 25:
            if GPIO.input(17) == GPIO.LOW:
                team = "yellow"
            else:
                team = "blue"
            time.sleep(0.05)
            x += 1 

    except KeyboardInterrupt:
        print("\nArrêt du programme")
        GPIO.cleanup()

    print(f"Team = {team}")

    activer_web = Options.demander_oui_non("Activer le serveur web ?", defaut=True)

    robot = Robot(
        port=devices["stm32"] if connecter_robot else None,
        port_lidar=devices["lidar"],
        baudrate=115200,
        camera_id=camera_ids[0] if camera_ids else 0,
        x_init=150,
        y_init=100,
        angle_init_deg=0,
        team=team
    )

    carte = Map(team="yellow")

    strategy = Strategy(
        carte = carte, 
        robot = robot,
    )

    if connecter_robot:
        robot.connecter()

    try:
        web = None
        if activer_web:
            web = AffichageWeb(
                robot=robot,
                strategy=strategy,
                port=5000,
                camera_indices=camera_ids if utiliser_camera else [],
                aruco_detection=activer_aruco,
            )
            web.run()
        elif connecter_robot:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nArrêt du programme")
        else:
            print("Aucun service lancé.")
    finally:
        robot.fermer()

def main():
    devices = Options.init_devices()

    # Configuration automatique
    utiliser_camera = bool(devices["cameras"])
    camera_ids = devices["cameras"] if utiliser_camera else []
    
    # Force l'activation si les périphériques sont présents
    activer_aruco = utiliser_camera
    connecter_robot = bool(devices["stm32"])

    # Lecture de l'interrupteur d'équipe
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    team = "blue"
    try:
        for _ in range(25):
            team = "yellow" if GPIO.input(17) == GPIO.LOW else "blue"
            time.sleep(0.05)
    except KeyboardInterrupt:
        GPIO.cleanup()
        return

    print(f"Team auto-détectée : {team}")

    robot = Robot(
        port=devices["stm32"] if connecter_robot else None,
        port_lidar=devices["lidar"],
        baudrate=115200,
        camera_id=camera_ids[0] if camera_ids else 0,
        x_init=150,
        y_init=100,
        angle_init_deg=0,
        team=team
    )

    carte = Map(team=team)
    strategy = Strategy(carte=carte, robot=robot)

    if connecter_robot:
        robot.connecter()

    try:
        # Lancement automatique du serveur web
        web = AffichageWeb(
            robot=robot,
            strategy=strategy,
            port=5000,
            camera_indices=camera_ids,
            aruco_detection=activer_aruco,
        )
        web.run()
    finally:
        robot.fermer()
        GPIO.cleanup()

# A faire tourner en continue sur la raspy
def ficelle(team):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    while(True):
        if GPIO.input(2) == GPIO.LOW:
            if team == "yellow":
                Strategy.strategy_1_jaune
            elif team == "bleu":
                Strategy.strategy_1_bleu
            else:
                print("Err")

if __name__ == "__main__":
    main_bis()

