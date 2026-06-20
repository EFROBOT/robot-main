
import time
import argparse
import board
import neopixel_spi
import threading

class BandeauLED:
    def __init__(self, num_pixels=60, brightness=0.5, logs=None, pixel_order="GRB"):
        """
        Initialise le bandeau LED via le bus SPI (sans sudo).
        """
        self.num_pixels = num_pixels
        self.logs = logs
        self.team_actuelle = None
        self._thread_clignoter=None
        self._stop_clignoter= threading.Event()


        try:
            # Initialise le bus SPI par défaut (SPI0). 
            # Les données sortiront obligatoirement sur le GPIO 10 (MOSI).
            self.spi = board.SPI()
            
            self.pixels = neopixel_spi.NeoPixel_SPI(
                self.spi,
                self.num_pixels,
                brightness=brightness,
                auto_write=False,
                pixel_order=pixel_order,
            )
            self.eteindre()
        except Exception as e:
            self.pixels = None
            self._log("ERR", f"Erreur initialisation LEDs SPI: {e}")

    def _log(self, niveau, msg):
        if self.logs is not None:
            self.logs.log(niveau, msg)
        else:
            print(f"[{niveau}] {msg}")

    def set_team_color(self, team):
        """Change la couleur du bandeau si l'équipe a changé."""
        if not self.pixels:
            return
        if team == self.team_actuelle:
            return

        if team == "yellow":
            self.allumer_couleur((255, 255, 0))
            self._log("RPi", "LEDs -> JAUNE")
        elif team == "blue":
            self.allumer_couleur((0, 0, 255))
            self._log("RPi", "LEDs -> BLEU")
        else:
            self.eteindre()
            self._log("RPi", "LEDs -> éteintes")

        self.team_actuelle = team

    def allumer_couleur(self, couleur_rgb):
        """Allume le bandeau avec un tuple (R, G, B)."""
        if self.pixels:
            self.pixels.fill(couleur_rgb)
            self.pixels.show()

    def _stop_clignotement(self):
        if self._thread_clignoter and self._thread_clignoter.is_alive():
            self._stop_clignoter.set()
            self._thread_clignoter.join()
        self._stop_clignoter.clear()
        self._log("RPi","Stop CLIOOOOOOOOOOO")

    def clignoter(self, couleur_rgb, vitesse=0.3):
        self._stop_clignotement()
        def _clignoter_loop():
            while not self._stop_clignoter.is_set():
                if self.pixels:
                    self.pixels.fill(couleur_rgb)
                    self.pixels.show()
                if self._stop_clignoter.wait(vitesse):
                    break
                if self.pixels:
                    self.eteindre()
                if self._stop_clignoter.wait(vitesse):
                    break
        self._thread_clignoter = threading.Thread(target=_clignoter_loop, daemon= True)
        self._thread_clignoter.start()

    def clignoter_eteindre(self):
        self._stop_clignotement()

    def allumer_premieres(self, n, couleur_rgb):
        """Allume uniquement les n premieres LEDs avec un tuple (R, G, B)."""
        if not self.pixels:
            return
        n = max(0, min(self.num_pixels, int(n)))
        self.pixels.fill((0, 0, 0))
        for i in range(n):
            self.pixels[i] = couleur_rgb
        self.pixels.show()

    def set_pixel(self, index, couleur_rgb):
        """Allume une LED specifique avec un tuple (R, G, B)."""
        if not self.pixels:
            return
        if index < 0 or index >= self.num_pixels:
            return
        self.pixels[index] = couleur_rgb

    def show(self):
        if self.pixels:
            self.pixels.show()

    def eteindre(self):
        """Éteint toutes les LEDs."""
        if self.pixels:
            self.pixels.fill((0, 0, 0))
            self.pixels.show()

    def stop(self):
        """Arrête proprement le bandeau."""
        if self.pixels:
            self.eteindre()
            try:
                self.pixels.deinit()
            except Exception as exc:
                self._log("ERR", f"Erreur deinit LEDs: {exc}")
            self.pixels = None


def _parse_color(color_text):
    if not color_text:
        return None
    parts = color_text.split(",")
    if len(parts) != 3:
        raise ValueError("color must be R,G,B")
    return tuple(max(0, min(255, int(p.strip()))) for p in parts)


def main():
    parser = argparse.ArgumentParser(description="Test WS2812B strip via SPI")
    parser.add_argument("--num-pixels", type=int, default=10)
    parser.add_argument("--brightness", type=float, default=0.5)
    parser.add_argument("--team", choices=["yellow", "blue", "off"], default=None)
    parser.add_argument("--color", default=None, help="R,G,B")
    parser.add_argument("--first-n", type=int, default=0, help="Allume les N premieres LEDs")
    parser.add_argument("--seconds", type=float, default=0)
    args = parser.parse_args()

    strip = BandeauLED(num_pixels=args.num_pixels, brightness=args.brightness)
    
    try:
        if args.first_n and args.first_n > 0:
            color = _parse_color(args.color) if args.color else (255, 255, 255)
            strip.allumer_premieres(args.first_n, color)
        elif args.team:
            if args.team == "off":
                strip.eteindre()
            else:
                strip.set_team_color(args.team)
        elif args.color:
            color = _parse_color(args.color)
            strip.allumer_couleur(color)
        else:
            strip.allumer_couleur((0, 0, 0))

        if args.seconds and args.seconds > 0:
            time.sleep(args.seconds)
    finally:
        strip.stop()

if __name__ == "__main__":
    main()
