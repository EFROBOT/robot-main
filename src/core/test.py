from gpiozero import Button
from signal import pause

# GPIO 17, pull-up activé par défaut
interrupteur = Button(17, pull_up=True, bounce_time=0.05)

def fonction_switch_ferme():
    print("Interrupteur FERMÉ")
    # Ta logique ici (allumer LED, lancer moteur, etc.)

def fonction_switch_ouvert():
    print("Interrupteur OUVERT")
    # Ta logique ici

interrupteur.when_pressed = fonction_switch_ferme
interrupteur.when_released = fonction_switch_ouvert

print("En attente... (Ctrl+C pour quitter)")
pause()