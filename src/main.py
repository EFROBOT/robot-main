""""""

#from hardware import Camera
#from robot import Robot
from modules import Aruco, Marker, AffichageWeb, Map, Robot, Strategy
import serial
import serial.tools.list_ports
import cv2

import time
"""
def main():

    try:
        cam_id = int(input("Quelle caméra utiliser ? (0, 1, 2) : "))
        if cam_id not in [0, 1, 2]:
            raise ValueError
    except ValueError:
        cam_id = 2

    do_calib = input(f"Calibration caméra {cam_id} ? (o/n) : ").lower() == "o"
    
    if do_calib:

        temp_camera = Camera(camera_id=cam_id)
        print(f"--- Calibration Caméra {cam_id} ---")
        temp_camera.capture_images(save_dir=temp_camera.calibration_dir)
        temp_camera.calibrate_charuco(
            image_folder=temp_camera.calibration_dir, 
            output_file=temp_camera.calibration_file
        )
        temp_camera.release()
        print("Calibration terminée.")

    robot = Robot(camera_id=cam_id)
    
    try:
        robot.setup()
        robot.run()
    except Exception as e:
        print(f"Erreur lors de l'exécution du robot : {e}")
    finally:
        if robot.running:
            del robot
"""

def init_devices(vid_stm32=0x0483, vid_lidar=0x10c4):
    devices = {
        "stm32": None,
        "lidar": None,
        "cameras": []
    }

    for port in serial.tools.list_ports.comports():
        if port.vid == vid_stm32:
            devices["stm32"] = port.device
        elif port.vid == vid_lidar:
            devices["lidar"] = port.device

    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            devices["cameras"].append(i)
            cap.release()
            if len(devices["cameras"]) == 2:
                break

    return devices


if __name__ == "__main__":
    devices = init_devices()
    
    if not devices["stm32"]:
        print("Erreur : STM32 non détectée")
        exit()

    carte = Map(team="yellow")
    
    robot = Robot(
        port=devices["stm32"], 
        baudrate=115200, 
        x_init=150, 
        y_init=100, 
        angle_init_deg=0
        )

    robot.connecter()    
    web = AffichageWeb(
        carte          = carte,
        robot          = robot,
        strategy_class = Strategy,
        port           = 5000,
        camera_indices=devices["cameras"],
    )

    web.run()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        robot.fermer()
        print("\nArrêt du programme")

