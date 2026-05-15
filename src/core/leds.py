import board
import neopixel


class BandeauLED:
    def __init__(self, num_pixels=10, brightness=0.5, logs=None):
        """
        Initialise le bandeau LED.
        :param num_pixels: Le nombre de LEDs physiques sur ton bandeau.
        :param brightness: Luminosite globale (0.0 a 1.0).
        :param logs: Instance optionnelle de Logs pour tracer dans le dashboard.
        """
        self.num_pixels = num_pixels
        self.logs = logs
        self.team_actuelle = None

        # GPIO 21 (board.D21) pour ne pas interferer avec le servomoteur (GPIO 18)
        self.pin = board.D21

        try:
            self.pixels = neopixel.NeoPixel(
                self.pin,
                self.num_pixels,
                brightness=brightness,
                auto_write=False,
            )
            self.eteindre()
        except Exception as e:
            self.pixels = None
            self._log("ERR", f"Erreur initialisation LEDs: {e}")

    def _log(self, niveau, msg):
        if self.logs is not None:
            self.logs.log(niveau, msg)
        else:
            print(f"[{niveau}] {msg}")

    def set_team_color(self, team):
        """Change la couleur du bandeau si l'equipe a change."""
        if not self.pixels:
            return
        if team == self.team_actuelle:
            return  # pas de changement, on ne refresh pas inutilement

        if team == "yellow":
            self.allumer_couleur((255, 255, 0))
            self._log("RPi", "LEDs -> JAUNE")
        elif team == "blue":
            self.allumer_couleur((0, 0, 255))
            self._log("RPi", "LEDs -> BLEU")
        else:
            self.eteindre()
            self._log("RPi", "LEDs -> eteintes")

        self.team_actuelle = team

    def allumer_couleur(self, couleur_rgb):
        """Allume le bandeau avec un tuple (R, G, B)."""
        if self.pixels:
            self.pixels.fill(couleur_rgb)
            self.pixels.show()

    def eteindre(self):
        """Eteint toutes les LEDs."""
        if self.pixels:
            self.pixels.fill((0, 0, 0))
            self.pixels.show()