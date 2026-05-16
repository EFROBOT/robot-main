import time
import threading
import RPi.GPIO as GPIO

from app.options import Options
from core.robot import Robot
from core.strategy import Strategy
from world.map import Map

from web.dashboard import AffichageWeb


def ficelle(robot, strategy, web, utiliser_camera):
    x = False
    GPIO.setup(2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def frame_provider_robot():
        ret, frame = robot.camera.read()
        if ret and frame is not None:
            return frame
        frame = robot.camera.get_latest_frame()
        return frame if frame is not None else None
    
    while True:
        # Suivi de l'interrupteur d'équipe (uniquement si changement)
        nouvelle_team = "yellow" if GPIO.input(17) == GPIO.LOW else "blue"
        if nouvelle_team != robot.team:
            robot.set_team(nouvelle_team)
            robot.team = nouvelle_team
            nouvelle_carte = Map(team=nouvelle_team)
            strategy.carte = nouvelle_carte
            robot.map = nouvelle_carte
            robot.logs.log("RPi", f"Équipe changée via interrupteur → {nouvelle_team}")

        # Surveillance de la tirette
        if GPIO.input(2) == GPIO.LOW:
            robot.logs.log("RPi", f"Tirette retirée → stratégie homologation ({robot.team})")
            strategy.strategy_derniere_serie()
            robot.fermer()
            GPIO.cleanup()
            while True:
                x=0

        time.sleep(0.05)


def main():
    devices = Options.init_devices()

    utiliser_camera = bool(devices["cameras"])
    camera_ids = devices["cameras"] if utiliser_camera else []
    activer_aruco = utiliser_camera
    connecter_robot = bool(devices["stm32"])

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Lecture initiale de l'équipe (sera mise à jour à chaud dans ficelle)
    team = "yellow" if GPIO.input(17) == GPIO.LOW else "blue"
    print(f"Team initiale : {team}")

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

    if utiliser_camera:
        robot.setup()

    carte = Map(team=team)
    strategy = Strategy(carte=carte, robot=robot)

    if connecter_robot:
        robot.connecter()

    try:
        web = AffichageWeb(
            robot=robot,
            strategy=strategy,
            port=5000,
            camera_indices=camera_ids,
            aruco_detection=activer_aruco,
        )

        web_thread = threading.Thread(target=web.run, daemon=True)
        web_thread.start()

        x = True
        if x :
            ficelle(robot, strategy, web, utiliser_camera)

    finally:
        robot.fermer()
        GPIO.cleanup()


if __name__ == '__main__':
    main()