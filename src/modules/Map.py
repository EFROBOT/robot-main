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

TERRAIN_WIDTH  = 300.0
TERRAIN_HEIGHT = 200.0


class Position:
    def __init__(self, x ,y):
        self.x = x
        self.y = y

 
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
        return self.x_min() <= pos.x <= self.x_max() and self.y_min() <= pos.y <= self.y_max


class Map:
    def __init__(self, team):
        self.team = team

    def nids(self):
        if self.team == "yellow":
            return{
                "yellow": Zone("NY", Position(30, 182.5), 60, 45)
            }
        else:
            return{
                "blue": Zone("NB", Position(270, 182.5), 60, 45)
            }

    def ramassage(self):
        # 15 * 20 cm --> 4 caisses 
        # 8 R
        return{
            "R1": Zone("R1", Position(0, 0), 15, 20),
            "R2": Zone("R2", Position(0, 0), 15, 20),
            "R3": Zone("R3", Position(0, 0), 15, 20),
            "R4": Zone("R4", Position(0, 0), 15, 20),
            "R5": Zone("R5", Position(0, 0), 15, 20),
            "R6": Zone("R6", Position(0, 0), 15, 20),
            "R7": Zone("R7", Position(0, 0), 15, 20),
            "R8": Zone("R8", Position(0, 0), 15, 20),
        }

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
            "Exclusion": Zone("E", Position(150, 1800), 90, 40)
        }
    
    #def thermomètre(self):


    #def curseur(self):



if __name__ == "__main__":
    carte = map(team = "yellow")
    

