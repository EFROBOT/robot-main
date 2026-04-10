import time
import math
from raspbot import Robot, MotorId

# robot
L      = 0.0115   # distance centre - axe
LAMBDA = 0.0115   # largeur centre - axe
R      = 0.024    # rayon des roues

# Nema 14
STEPS_PER_REV    = 200
MICROSTEPPING    = 16     # A4988
NB_PAS_PAR_METRE = (STEPS_PER_REV * MICROSTEPPING) / (2 * math.pi * R)

# Position initiale
x_robot     = 0.0
y_robot     = 0.0
angle_robot = 0.0

# Vitesse moteur par défaut (0-100)
SPEED = 80


def calcul_steps(distance: float) -> int:
    steps = distance * NB_PAS_PAR_METRE
    return int(steps)


def _duree_pour_steps(steps: int) -> float:
    """Convertit un nombre de pas en durée (secondes) à la vitesse SPEED."""
    # à SPEED=80 on estime ~1600 pas/s (à calibrer selon ton robot)
    STEPS_PER_SECOND = 1600 * (SPEED / 100)
    return abs(steps) / STEPS_PER_SECOND


def sync_4_driver(bot: Robot, steps1: int, steps2: int, steps3: int, steps4: int):
    """
    Function move :
    Fait tourner les 4 moteurs le nombre de pas demandé, puis stoppe.
    Le signe du steps détermine le sens (+= avant, -= arrière pour chaque roue).
    """
    duree = _duree_pour_steps(max(abs(steps1), abs(steps2), abs(steps3), abs(steps4)))

    # haut gauche  → L1
    bot.motors.drive(MotorId.L1, int(math.copysign(SPEED, steps1)) if steps1 != 0 else 0)
    # haut droite  → R1
    bot.motors.drive(MotorId.R1, int(math.copysign(SPEED, steps2)) if steps2 != 0 else 0)
    # bas gauche   → L2
    bot.motors.drive(MotorId.L2, int(math.copysign(SPEED, steps3)) if steps3 != 0 else 0)
    # bas droite   → R2
    bot.motors.drive(MotorId.R2, int(math.copysign(SPEED, steps4)) if steps4 != 0 else 0)

    time.sleep(duree)

    # Stop
    bot.motors.drive(MotorId.L1, 0)
    bot.motors.drive(MotorId.R1, 0)
    bot.motors.drive(MotorId.L2, 0)
    bot.motors.drive(MotorId.R2, 0)


def avancer(bot: Robot, distance: float):
    global x_robot, y_robot
    steps = calcul_steps(distance)
    sync_4_driver(bot, steps, steps, steps, steps)
    x_robot += distance * math.cos(angle_robot)
    y_robot += distance * math.sin(angle_robot)


def reculer(bot: Robot, distance: float):
    global x_robot, y_robot
    steps = calcul_steps(distance)
    sync_4_driver(bot, -steps, -steps, -steps, -steps)
    x_robot -= distance * math.cos(angle_robot)
    y_robot -= distance * math.sin(angle_robot)


def gauche(bot: Robot, distance: float):
    global x_robot, y_robot
    steps = calcul_steps(distance)
    sync_4_driver(bot, -steps, steps, steps, -steps)
    x_robot -= distance * math.sin(angle_robot)
    y_robot += distance * math.cos(angle_robot)


def droite(bot: Robot, distance: float):
    global x_robot, y_robot
    steps = calcul_steps(distance)
    sync_4_driver(bot, steps, -steps, -steps, steps)
    x_robot += distance * math.sin(angle_robot)
    y_robot -= distance * math.cos(angle_robot)

# diagonale
def diagonale_gauche(bot: Robot, distance: float):
    steps = calcul_steps(distance)
    sync_4_driver(bot, 0, steps, steps, 0)

def diagonale_droite(bot:Robot, distance:float):
    steps = calcul_steps(distance)
    sync_4_driver(bot, steps, 0, 0, steps)

# rotation
def rotation_droite(bot: Robot, angle_deg: float):
    global angle_robot
    arc   = (angle_deg / 360.0) * 2 * math.pi * R
    steps = calcul_steps(arc)
    sync_4_driver(bot, steps, -steps, -steps, steps)
    angle_robot += math.radians(angle_deg)

def rotation_gauche(bot: Robot, angle_deg: float):
    global angle_robot
    arc   = (angle_deg / 360.0) * 2 * math.pi * R
    steps = calcul_steps(arc)
    sync_4_driver(bot, -steps, steps, steps, -steps)
    angle_robot -= math.radians(angle_deg)


def go_to_coord(bot: Robot, x: float, y: float):
    global x_robot, y_robot, angle_robot

    # difference
    dx           = x - x_robot
    dy           = y - y_robot
    angle_cible  = math.atan2(dy, dx)
    dangle       = angle_cible - angle_robot

    # turn to the cible
    arc               = (dangle / 360.0) * 2 * math.pi * R
    steps_for_rotate  = calcul_steps(arc)
    if dangle > 0.01:
        sync_4_driver(bot, -steps_for_rotate, -steps_for_rotate,
                           -steps_for_rotate, -steps_for_rotate)
    elif dangle < -0.01:
        sync_4_driver(bot,  steps_for_rotate,  steps_for_rotate,
                            steps_for_rotate,  steps_for_rotate)

    # move to cible
    distance      = math.sqrt(dx * dx + dy * dy)
    steps_for_move = calcul_steps(distance)
    sync_4_driver(bot, steps_for_move, -steps_for_move,
                       steps_for_move, -steps_for_move)

    # update robot coord
    x_robot     = x
    y_robot     = y
    angle_robot = angle_cible


def go_to_cam_object(bot: Robot, distance: float, angle_deg: float):
    global x_robot, y_robot, angle_robot

    if angle_deg > 0.5:
        rotation_droite(bot, angle_deg)
    elif angle_deg < -0.5:
        rotation_gauche(bot, abs(angle_deg))

    avancer(bot, distance)

    angle_robot += math.radians(angle_deg)
    x_robot += distance * math.cos(angle_robot)
    y_robot += distance * math.sin(angle_robot)

# Boucle principale

with Robot() as bot:
    """avancer(bot, 0.1)
    time.sleep(0.6)

    reculer(bot, 0.1)
    time.sleep(0.6)

    gauche(bot, 0.05)
    time.sleep(0.6)

    droite(bot, 0.05)
    time.sleep(0.6)
    """

    diagonale_gauche(bot, 0.1)
    time.sleep(0.6)

    diagonale_droite(bot, 0.1)
    time.sleep(0.6)

    rotation_gauche(bot, 0.1)
    time.sleep(0.6)

    rotation_droite(bot, 0.1)
    time.sleep(0.6)

