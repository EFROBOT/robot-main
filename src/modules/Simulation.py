import math
import time
from Map import Map
from MapGUI import MapGUI
from Strategy import Strategy

class Simulation:
    def __init__(self, carte, gui, x_init=14.0, y_init=184.0, angle_init_deg=0.0):
        self.carte = carte
        self.gui = gui
        
        self.x = float(x_init)
        self.y = float(y_init)
        self.angle = math.radians(angle_init_deg)
        
        # Vitesse de simulation (en cm par "frame" ou en degrés par "frame")
        self.vitesse_cm_par_frame = 0.5 
        self.vitesse_deg_par_frame = 2.0

        self.inventaire = []

        self._sync_map()

    def _sync_map(self):
        if hasattr(self.carte, 'robot') and "Robot" in self.carte.robot:
            self.carte.robot["Robot"].center.x = self.x
            self.carte.robot["Robot"].center.y = self.y
            self.carte.robot["Robot"].center.angle = self.angle

    def attendre(self, secondes):
        frames_a_attendre = int(secondes * 60) # 60 FPS
        for _ in range(frames_a_attendre):
            self.gui.update_display()

    def avancer(self, distance):
        frames = int(abs(distance) / self.vitesse_cm_par_frame)
        signe = 1 if distance >= 0 else -1
        
        for _ in range(frames):
            self.x += (self.vitesse_cm_par_frame * signe) * math.cos(self.angle)
            self.y += (self.vitesse_cm_par_frame * signe) * math.sin(self.angle)
            self._sync_map()
            self.gui.update_display() # Rafraîchit l'écran à chaque petit pas !

    def reculer(self, distance):
        self.avancer(-distance)

    def gauche(self, distance):
        frames = int(abs(distance) / self.vitesse_cm_par_frame)
        signe = 1 if distance >= 0 else -1
        for _ in range(frames):
            self.x -= (self.vitesse_cm_par_frame * signe) * math.sin(self.angle)
            self.y += (self.vitesse_cm_par_frame * signe) * math.cos(self.angle)
            self._sync_map()
            self.gui.update_display()

    def droite(self, distance):
        self.gauche(-distance)

    
    def diagonale_gauche(self, distance):
        frames = int(abs(distance) / self.vitesse_cm_par_frame)
        signe = 1 if distance >= 0 else -1
        for _ in range(frames):
            self.x += (self.vitesse_cm_par_frame * signe) * math.cos(self.angle + math.pi/4)
            self.y += (self.vitesse_cm_par_frame * signe) * math.sin(self.angle + math.pi/4)
            self._sync_map()
            self.gui.update_display()

    def diagonale_droite(self, distance):
        frames = int(abs(distance) / self.vitesse_cm_par_frame)
        signe = 1 if distance >= 0 else -1
        for _ in range(frames):
            self.x += (self.vitesse_cm_par_frame * signe) * math.cos(self.angle - math.pi/4)
            self.y += (self.vitesse_cm_par_frame * signe) * math.sin(self.angle - math.pi/4)
            self._sync_map()
            self.gui.update_display()

    def rotation_droite(self, angle_deg):
        frames = int(abs(angle_deg) / self.vitesse_deg_par_frame)
        for _ in range(frames):
            self.angle -= math.radians(self.vitesse_deg_par_frame) # Sens horaire (inversé en trigo classique)
            self.angle = math.atan2(math.sin(self.angle), math.cos(self.angle)) # Normalisation
            self._sync_map()
            self.gui.update_display()

    def rotation_gauche(self, angle_deg):
        frames = int(abs(angle_deg) / self.vitesse_deg_par_frame)
        for _ in range(frames):
            self.angle += math.radians(self.vitesse_deg_par_frame)
            self.angle = math.atan2(math.sin(self.angle), math.cos(self.angle))
            self._sync_map()
            self.gui.update_display()

    
    def tourner_vers_angle(self, angle_cible_deg):
        angle_actuel_deg = math.degrees(self.angle)

        diff = angle_cible_deg - angle_actuel_deg
        diff = (diff + 180) % 360 - 180

        if diff > 0:
            self.rotation_gauche(diff)
        elif diff < 0:
            self.rotation_droite(abs(diff))


    def go_to_coord(self, x_cible, y_cible):
        dx = x_cible - self.x
        dy = y_cible - self.y
        angle_cible = math.atan2(dy, dx)
        
        diff_angle = angle_cible - self.angle
        diff_angle = math.atan2(math.sin(diff_angle), math.cos(diff_angle)) 
        
        if diff_angle > 0:
            self.rotation_gauche(math.degrees(diff_angle))
        elif diff_angle < 0:
            self.rotation_droite(math.degrees(abs(diff_angle)))
            
        distance = math.sqrt(dx**2 + dy**2)
        self.avancer(distance)

    """
    def go_to_coord(self, x_cible, y_cible):
        dx = x_cible - self.x
        dy = y_cible - self.y
        
        # Décomposition dans le repère LOCAL du robot
        # (en tenant compte de son orientation actuelle)
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        
        # Projection du vecteur cible sur les axes du robot
        local_x = dx * cos_a + dy * sin_a   # composante "avant"
        local_y = -dx * sin_a + dy * cos_a  # composante "gauche"
        
        distance_totale = math.sqrt(dx**2 + dy**2)
        frames = int(distance_totale / self.vitesse_cm_par_frame)
        
        for _ in range(frames):
            # Avance en avant ET latéralement en même temps
            self.x += (self.vitesse_cm_par_frame * local_x / distance_totale) * cos_a \
                    - (self.vitesse_cm_par_frame * local_y / distance_totale) * sin_a
            self.y += (self.vitesse_cm_par_frame * local_x / distance_totale) * sin_a \
                    + (self.vitesse_cm_par_frame * local_y / distance_totale) * cos_a
            self._sync_map()
            self.gui.update_display()
    """
    """
    def go_to_coord(self, x_cible, y_cible):
        dx = x_cible - self.x
        dy = y_cible - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        # Si on est déjà sur place (à moins d'1 millimètre), on ne fait rien
        if distance < 0.1:
            return

        # On calcule le nombre de frames nécessaires
        frames = int(distance / self.vitesse_cm_par_frame)
        if frames == 0:
            frames = 1
            
        # On calcule de combien de cm on doit se décaler en X et en Y à chaque frame
        pas_x = dx / frames
        pas_y = dy / frames
        
        # Le robot se translate vers la cible (remarque : self.angle n'est JAMAIS modifié !)
        for _ in range(frames):
            self.x += pas_x
            self.y += pas_y
            self._sync_map()
            self.gui.update_display()
            
        # Par sécurité, à la toute fin, on force la position exacte
        # pour éviter les micro-erreurs d'arrondi mathématique
        self.x = x_cible
        self.y = y_cible
        self._sync_map()
        self.gui.update_display()
    """

    def recuperer_caisses(self, id_zone):
        caisses_noms = [nom for nom in self.carte.caisses.keys() if id_zone in nom]
        caisses_triees = sorted(caisses_noms, key=lambda nom: math.hypot(self.carte.caisses[nom].center.x - self.x, self.carte.caisses[nom].center.y - self.y))

        for nom_caisse in caisses_triees:
            caisse = self.carte.caisses.get(nom_caisse)
            if not caisse:
                continue

            dist = math.hypot(caisse.center.x - self.x, caisse.center.y - self.y)
            avance_requise = dist - 18.5
            
            if avance_requise > 0.1:
                self.avancer(avance_requise)

            self.attendre(1) 
            caisse_attrapee = self.carte.caisses.pop(nom_caisse)
            self.inventaire.append(caisse_attrapee)
            self.gui.update_display()
            print(f"Caisse {caisse_attrapee.name} attrapée ({len(self.inventaire)})")

    def lacher_caisses(self):
        nb_caisses = len(self.inventaire)
        
        for i in range(nb_caisses):
            self.attendre(0.5) 
            caisse_a_deposer = self.inventaire.pop(0)
            
            angle_arriere = self.angle + math.pi
            distance_recul = 18.0
            
            caisse_a_deposer.center.x = self.x + distance_recul * math.cos(angle_arriere)
            caisse_a_deposer.center.y = self.y + distance_recul * math.sin(angle_arriere)
            
            self.carte.caisses[caisse_a_deposer.name] = caisse_a_deposer
            self.gui.update_display()
            print(f"Caisse {caisse_a_deposer.name} déposée ({len(self.inventaire)})")
            
            if len(self.inventaire) > 0:
                self.avancer(6.0)
                
if __name__ == "__main__":
    carte_jaune = Map(team="yellow")
    
    interface = MapGUI(carte_jaune, image_path="img/table_FINALE_1.0-1.png")
    
    sim = Simulation(carte=carte_jaune, gui=interface, x_init=16.0, y_init=184.0, angle_init_deg=0.0)
    
    cerveau = Strategy(carte=carte_jaune, robot=sim, sim=True)
    cerveau.strategy_1()

    print(f"X : {sim.x} | Y : {sim.y}")
    
    while True:
        interface.update_display()