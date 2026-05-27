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

        devices["cameras"] = Options.list_available_cameras(max_index=10)[:3]

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


