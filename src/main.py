""""""

from hardware import Camera
from robot import Robot
import serial
import serial.tools.list_ports

import time
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
    

if __name__ == "__main__":
    main()
