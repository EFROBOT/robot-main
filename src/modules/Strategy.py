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

    def __init__(self, carte, robot):
        self.carte = carte
        self.robot = robot
      
    def strategy_1(self):
        time.sleep(1)

        zone_ramassage = self.carte.ramassage["R1"]
        print(f" {zone_ramassage.name} (X:{zone_ramassage.center.x}, Y:{zone_ramassage.center.y})")

        self.robot.go_to_coord(zone_ramassage.center.x, zone_ramassage.center.y)
        self.robot.recuperer_caisses("R1")

        time.sleep(1)
        zone_garde_manger = self.carte.garde_mangers["G1"]
        print(f" {zone_garde_manger.name} (X:{zone_garde_manger.center.x}, Y:{zone_garde_manger.center.y})")

        self.robot.go_to_coord(zone_garde_manger.center.x, zone_garde_manger.center.y)
        time.sleep(1)

        self.robot.lacher_caisses()


    
    def strategy_2(self):
        pass

    def strategy_3(self):
        pass