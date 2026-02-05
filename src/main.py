""""""

import cv2

from hardware import Camera
from modules.Aruco import Aruco


def main():
    try:
        cam_id = int(input("Quelle caméra utiliser ? (0, 1, 2) : "))
        if cam_id not in [0, 1, 2]:
            raise ValueError
    except ValueError:
        cam_id = 2

    do_calib = input(f"Calibration caméra {cam_id} ? (o/n) : ").lower() == "o"

    camera = Camera(camera_id=cam_id)

    # Calibration
    if do_calib:
        print(f"--- Calibration Caméra {cam_id} ---")
        camera.capture_images(save_dir=camera.calibration_dir)
        camera.camera_matrix, camera.dist_coeffs = camera.calibrate_charuco(
            image_folder=camera.calibration_dir, output_file=camera.calibration_file
        )
    elif not camera.load_calibration():
        import os

        if (
            os.path.exists(camera.calibration_dir)
            and os.path.isdir(camera.calibration_dir)
            and len(os.listdir(camera.calibration_dir)) > 0
        ):
            print(
                f"Fichier Calibration introuvable, mais '{camera.calibration_dir}' à des images."
            )
            if input("Utiliser ces images ? (o/n) : ").lower() == "o":
                camera.camera_matrix, camera.dist_coeffs = camera.calibrate_charuco(
                    image_folder=camera.calibration_dir,
                    output_file=camera.calibration_file,
                )
            else:
                camera.use_default_calibration()
        else:
            camera.use_default_calibration()

    if not camera.open():
        return

    # Initialisation du détecteur Aruco
    camera_matrix, dist_coeffs = camera.get_calibration()
    aruco_detector = Aruco(marker_size=0.040, camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)

    # Boucle principale de détection
    print("Détection en cours...")
    try:
        while True:
            ret, frame = camera.read()
            if not ret or frame is None:
                break

            markers = aruco_detector.detect_markers(frame)
            aruco_detector.draw_marker(frame, markers)

            cv2.imshow("", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
