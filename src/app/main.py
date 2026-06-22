import time
import threading
import math
try :
    import RPi.GPIO as GPIO
except ImportError:
    class MockGPIO:
        BCM = 'BCM'
        IN = 'IN'
        PUD_UP = 'PUD_UP'
        LOW = 0
        HIGH = 1
        def setmode(self, mode):
            
            print(f"GPIO setmode({mode})")

        def setwarnings(self, enabled):
            print(f"GPIO setwarnings({enabled})")

        def setup(self, pin, mode, pull_up_down=None):
            print(f"GPIO setup(pin={pin}, mode={mode}, pull_up_down={pull_up_down})")

        def input(self, pin):
            print(f"GPIO input({pin}) called")
            return self.LOW  # Simule un état par défaut

        def cleanup(self):
            print("GPIO cleanup() called")

from app.options import Options
from core.robot import Robot
from core.lidar import Lidar
from core.strategy import Strategy
from world.map import Map, TERRAIN_WIDTH, TERRAIN_HEIGHT

from api.server import ApiServer


def ficelle(robot, strategy, utiliser_camera):
    GPIO.setup(2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    while True:
        # Suivi de l'interrupteur d'équipe (uniquement si changement)

        nouvelle_team = "yellow" if GPIO.input(17) == GPIO.LOW else "blue"
        if nouvelle_team != robot.team:
            
            robot.leds.clignoter_eteindre()

            robot.leds.set_team_color(nouvelle_team)

            robot.set_team(nouvelle_team)
            robot.team = nouvelle_team
            nouvelle_carte = Map(team=nouvelle_team)
            strategy.carte = nouvelle_carte
            robot.map = nouvelle_carte
            robot.logs.log("RPi", f"Équipe changée via interrupteur → {nouvelle_team}")


        # Surveillance de la tirette
        if GPIO.input(2) == GPIO.LOW:
            robot.leds.eteindre()
            robot.logs.log("RPi", f"Tirette retirée → stratégie homologation ({robot.team})")
            strategy.homologation()
            robot.fermer()
            GPIO.cleanup()
            break

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

    team = "yellow" if GPIO.input(17) == GPIO.LOW else "blue"
    print(f"Team initiale : {team}")

    robot = Robot(
        port=devices["stm32"] if connecter_robot else None,
        port_lidar=devices["lidar"],
        baudrate=115200,
        camera_id=camera_ids[0] if camera_ids else 0,
        x_init=280,
        y_init=180,
        angle_init_deg=90,
        team=team
    )

    robot.leds.set_team_color(team)

    if utiliser_camera:
        robot.setup()

    carte = Map(team=team)
    strategy = Strategy(carte=carte, robot=robot)

    if connecter_robot:
        robot.connecter()

    try:
        api = ApiServer(
            robot=robot,
            strategy=strategy,
            port=5000,
            camera_indices=camera_ids,
            aruco_detection=activer_aruco,
        )

        api_thread = threading.Thread(target=api.run, daemon=True)
        api_thread.start()

        ficelle(robot, strategy, utiliser_camera)

    finally:
        robot.fermer()
        GPIO.cleanup()


if __name__ == '__main__':
    main()
