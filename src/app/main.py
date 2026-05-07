""""""

import time

from app.options import Options
from core.robot import Robot
from core.strategy import Strategy
from world.map import Map

from web.dashboard import AffichageWeb


def main():
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

    activer_web = Options.demander_oui_non("Activer le serveur web ?", defaut=True)

    robot = Robot(
        port=devices["stm32"] if connecter_robot else None,
        port_lidar=devices["lidar"],
        baudrate=115200,
        camera_id=camera_ids[0] if camera_ids else 0,
        x_init=150,
        y_init=100,
        angle_init_deg=0,
        team="yellow",
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


if __name__ == "__main__":
    main()

