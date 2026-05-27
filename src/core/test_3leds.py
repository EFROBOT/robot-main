import time
import board
import neopixel_spi

# 1. Initialisation du bus SPI par défaut (données sur GPIO 10 / Pin 19)
spi = board.SPI()

# 2. Déclaration de 3 LEDs
pixels = neopixel_spi.NeoPixel_SPI(
    spi, 
    3, 
    brightness=0.5, 
    auto_write=False, 
    pixel_order="GRB" # Ordre classique pour les WS2812B
)

print("Allumage : LED 1 (Rouge), LED 2 (Vert), LED 3 (Bleu)...")

# 3. Assignation des couleurs (R, G, B)
pixels[0] = (255, 0, 0)
pixels[1] = (0, 255, 0)
pixels[2] = (0, 0, 255)

# 4. Envoi de la commande
pixels.show()

# 5. Maintien pendant 10 secondes
time.sleep(10)

# 6. Extinction propre
pixels.fill((0, 0, 0))
pixels.show()
print("Fin du test.")
