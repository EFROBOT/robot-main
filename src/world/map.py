"""
Module de la carte 

Unité : 
    Distance --> cm 
    Angle --> Degrés

Terrain de 300 * 200 

(0,0) --> en bas à gauche (comme sur l'annexe)

WIDTH --> axe x 
HEIGHT --> axe y 

3 class 
    --> Robot position
    --> Zone (Nids + garde manger + ramassage)
    --> Map eurobot (team init)
"""

import math

TERRAIN_WIDTH  = 300.0
TERRAIN_HEIGHT = 200.0


class Position:
    def __init__(self, x ,y, angle=None):
        self.x = x
        self.y = y
        self.angle = angle

    def distance_entre_deux_points(self, point):
        return math.sqrt((self.x - point.x)**2 + (self.y - point.y)**2)
    
    def diff_entre_deux_angles(self, angle):
        diff = self.angle - angle
        if diff < 0:
            diff = diff + 2 * math.pi
        return diff


class Zone:
    def __init__(self, name, center, width, height):
        self.name = name
        self.center = center
        self.width = width
        self.height = height
        
    def x_min(self):
        return self.center.x - self.width / 2
 
    def x_max(self):
        return self.center.x + self.width / 2
 
    def y_min(self):
        return self.center.y - self.height / 2
 
    def y_max(self):
        return self.center.y + self.height / 2

    def in_zone(self, pos):
        return self.x_min() <= pos.x <= self.x_max() and self.y_min() <= pos.y <= self.y_max()
    
    def estime_zone(self, estimation):
        rayon = math.sqrt((self.width / 2)**2 + (self.height / 2)**2)
        return rayon + estimation


class Map:
    def __init__(self, team):
        self.team = team
        self.ramassage = self.init_ramassage()
        self.nids = self.nids()
        self.garde_mangers = self.garde_mangers()
        self.exclusion = self.exclusion()
        self.thermometre = self.thermometre()
        self.curseur = self.curseur()
        self.robot = self.get_robot_position()
        self.caisses = self.caisses()

    def nids(self):
        if self.team == "yellow":
            return{
                "yellow": Zone("NJ", Position(30, 182.5), 60, 55)
            }
        else:
            return{
                "blue": Zone("NB", Position(270, 182.5), 60, 55)
            }

    def init_ramassage(self):
        # 15 * 20 cm --> 4 caisses par zone de ramassage
        # 8 R
        return{
            "R1": Zone("R1", Position(20, 120), 15, 20),
            "R2": Zone("R2", Position(280, 120), 15, 20),

            "R3": Zone("R3", Position(115, 80), 20, 15),
            "R4": Zone("R4", Position(185, 80), 20, 15),

            "R5": Zone("R5", Position(20, 40), 15, 20),
            "R6": Zone("R6", Position(280, 40), 15, 20),

            "R7": Zone("R7", Position(110, 20), 20, 15),
            "R8": Zone("R8", Position(190, 20), 20, 15),
        }
    
    def caisses(self):
        # 4 caisses de 15x5 cm dans chaque zone de ramassage
        caisses = {}
        for key, zone in self.ramassage.items():  
            if zone.width == 15 and zone.height == 20:
                w_caisse, h_caisse = 15, 5
                start_y = zone.y_min() + (h_caisse / 2)
                for i in range(4):
                    nom = f"{key}_{i+1}"
                    cy = start_y + (i * h_caisse)
                    caisses[nom] = Zone(nom, Position(zone.center.x, cy), w_caisse, h_caisse)
            elif zone.width == 20 and zone.height == 15:
                w_caisse, h_caisse = 5, 15
                start_x = zone.x_min() + (w_caisse / 2)
                for i in range(4):
                    nom = f"{key}_{i+1}"
                    cx = start_x + (i * w_caisse)
                    caisses[nom] = Zone(nom, Position(cx, zone.center.y), w_caisse, h_caisse)

        return caisses

    def garde_mangers(self):
        # 20 * 20 cm 
        # 10 G
        return{
            "G1" : Zone("G1", Position(125, 145), 20, 20),
            "G2" : Zone("G2", Position(175, 145), 20, 20),
            "G3" : Zone("G3", Position(10, 80), 20, 20),
            "G4" : Zone("G4", Position(80, 80), 20, 20),
            "G5" : Zone("G5", Position(150, 80), 20, 20),
            "G6" : Zone("G6", Position(220, 80), 20, 20),
            "G7" : Zone("G7", Position(290, 80), 20, 20),
            "G8" : Zone("G8", Position(70, 10), 20, 20),
            "G9" : Zone("G9", Position(150, 10), 20, 20),
            "G10": Zone("G10", Position(230, 10), 20, 20),
        }

    def exclusion(self):
        return{
            "Exclusion": Zone("E", Position(150, 180), 180, 40)
        }
    
    def thermometre(self):
        return{
            "TH": Zone("TH", Position(150, 5), 300, 10)
        }

    def curseur(self):
        if self.team == "yellow":
            return{
                "C": Zone("C", Position(25, 5), 10, 10)
            }
        else:
            return{
                "C": Zone("C", Position(275, 5), 10, 10)
            }
        
    def get_robot_position(self):
        return {
            "Robot": Zone("Robot", Position(14, 184), 32, 28)
            }

    def _z2d(self, z):
        return {
            "name": z.name,
            "center_x": z.center.x,
            "center_y": z.center.y,
            "width": z.width,
            "height": z.height,
            "x_min": z.x_min(),
            "y_max": z.y_max(),
        }
    




if __name__ == "__main__":
    carte = Map(team = "yellow")


