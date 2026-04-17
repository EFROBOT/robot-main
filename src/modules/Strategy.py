"""
Module de strategie

Utilisé pour la simu & vrai xp

Strategie 1 : 
    Faire dans l'odre les differtentes zones de ramassage / garde manger 
    Au bout de la deuxieme rotation --> curseur thermometre

Strategie 2 :
    Aller dans la zone la plus proche en fonction de la ou est le robot

Strategie 3 : 
"""

import time

class Strategy:
    def __init__(self, carte, robot, sim=False):
        self.carte = carte
        self.robot = robot
        self.sim = sim

    def approche_ramassage(self, zone):
        dist_avant = 16.0

        if zone.height > zone.width:
            if self.robot.y > zone.center.y:
                x_cible = zone.center.x
                y_cible = zone.y_max() + dist_avant
                angle_cible = -90.0
            else:
                x_cible = zone.center.x
                y_cible = zone.y_min() - dist_avant
                angle_cible = 90.0
        else:
            if self.robot.x > zone.center.x:
                x_cible = zone.x_max() + dist_avant
                y_cible = zone.center.y
                angle_cible = 180.0
            else:
                x_cible = zone.x_min() - dist_avant
                y_cible = zone.center.y
                angle_cible = 0.0

        self.robot.aller_a_coord(x_cible, y_cible)
        self.robot.tourner_vers_angle(angle_cible)

    def approche_garde_manger(self, zone):
        dist_arriere = 16.0 
        
        target_x = zone.center.x
        target_y = zone.center.y
        target_angle_deg = 0.0

        dx = self.robot.x - zone.center.x
        dy = self.robot.y - zone.center.y

        if abs(dx) > abs(dy):
            if dx > 0:
                target_x = zone.x_max() + dist_arriere
                target_angle_deg = 0.0
            else:
                target_x = zone.x_min() - dist_arriere
                target_angle_deg = 180.0
        else:
            if dy > 0:
                target_y = zone.y_max() + dist_arriere
                target_angle_deg = 90.0
            else:
                target_y = zone.y_min() - dist_arriere
                target_angle_deg = -90.0

        self.robot.tourner_vers_angle(target_angle_deg) 
        self.robot.aller_a_coord(target_x, target_y)

    def strategy_1(self):
        time.sleep(1)

        zone_ramassage = self.carte.ramassage["R1"]
        self.approche_ramassage(zone_ramassage)
        
        if self.sim and hasattr(self.robot, 'recuperer_caisses'):
            self.robot.recuperer_caisses("R1")

        time.sleep(1)

        zone_garde_manger = self.carte.garde_mangers["G3"]
        self.approche_garde_manger(zone_garde_manger)
        
        if self.sim and hasattr(self.robot, 'lacher_caisses'):
            self.robot.lacher_caisses()

    def strategy_2(self):
        pass

    def strategy_3(self):
        pass