import os
import re

import cv2
import serial
import serial.tools.list_ports


class Options:

    @staticmethod
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

        devices["cameras"] = Options.list_available_cameras(max_index=10)[:2]

        return devices

    @staticmethod
    def list_available_cameras(max_index=10):
        """Retourne la liste des index caméra disponibles."""
        available = []

        by_path_dir = "/dev/v4l/by-path"
        if os.path.isdir(by_path_dir):
            usb_entries = []
            for entry in sorted(os.listdir(by_path_dir)):
                if "video-index0" not in entry or "usb-" not in entry:
                    continue
                full_path = os.path.join(by_path_dir, entry)
                try:
                    target = os.path.realpath(full_path)
                    match = re.search(r"video(\d+)$", target)
                    if match:
                        usb_entries.append(int(match.group(1)))
                except OSError:
                    continue

            if usb_entries:
                return sorted(set(usb_entries))[: max_index + 1]

        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]

        for index in range(max_index + 1):
            for backend in backends:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        available.append(index)
                        cap.release()
                        break
                cap.release()

        return available

    @staticmethod
    def demander_oui_non(message, defaut=False):
        suffixe = "[O/n]" if defaut else "[o/N]"
        while True:
            valeur = input(f"{message} {suffixe} : ").strip().lower()
            if not valeur:
                return defaut
            if valeur in ("o", "oui", "y", "yes"):
                return True
            if valeur in ("n", "non", "no"):
                return False
            print("Réponse attendue : o/oui ou n/non.")


    @staticmethod
    def demander_entier(message, defaut):
        while True:
            valeur = input(f"{message} [{defaut}] : ").strip()
            if not valeur:
                return defaut
            try:
                return int(valeur)
            except ValueError:
                print("Merci d'entrer un nombre entier valide.")


    @staticmethod
    def demander_liste_cameras(cameras_detectees):
        if not cameras_detectees:
            return []

        print("Caméras détectées :")
        for index, camera in enumerate(cameras_detectees, start=1):
            print(f"  {index}. {camera}")

        nb_max = min(2, len(cameras_detectees))
        nb_cameras = Options.demander_entier(f"Combien de caméras utiliser ? (1 à {nb_max})", nb_max)
        nb_cameras = max(1, min(nb_cameras, nb_max))

        selection = []
        for index in range(nb_cameras):
            defaut_slot = index + 1
            slot = Options.demander_entier(f"Caméra {index + 1} (numéro de la liste)", defaut_slot)
            if slot < 1 or slot > len(cameras_detectees):
                print(f"Choix invalide, utilisation de la caméra {defaut_slot}.")
                slot = defaut_slot

            camera_id = cameras_detectees[slot - 1]
            if camera_id not in selection:
                selection.append(camera_id)

        return selection


