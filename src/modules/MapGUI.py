import pygame
import sys
import math
from Map import Map

TERRAIN_WIDTH  = 300.0
TERRAIN_HEIGHT = 200.0
SCALE = 4 

class MapGUI:
    def __init__(self, carte, image_path=None):
        pygame.init()
        self.carte = carte
        
        self.canvas_width = int(TERRAIN_WIDTH * SCALE)
        self.canvas_height = int(TERRAIN_HEIGHT * SCALE)
        
        self.screen = pygame.display.set_mode((self.canvas_width, self.canvas_height))
        pygame.display.set_caption(f"Carte Eurobot - Team {self.carte.team.capitalize()}")
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 10, bold=True)
        
        self.bg_image = None
        if image_path:
            try:
                raw_image = pygame.image.load(image_path)
                self.bg_image = pygame.transform.scale(raw_image, (self.canvas_width, self.canvas_height))
                print(f"Image '{image_path}' chargée et redimensionnée.")
            except Exception as e:
                print(f"Erreur lors du chargement de l'image : {e}")

    def draw_zone(self, zone_obj, color, border_color="black", text_color="black"):
        """Dessine une zone rectangulaire sur la carte en inversant l'axe Y"""
        w_px = int(zone_obj.width * SCALE)
        h_px = int(zone_obj.height * SCALE)
        
        x0_px = int(zone_obj.x_min() * SCALE)
        y0_px = int(self.canvas_height - (zone_obj.y_max() * SCALE))
        
        rect = pygame.Rect(x0_px, y0_px, w_px, h_px)
        
        pygame.draw.rect(self.screen, pygame.Color(color), rect)
        pygame.draw.rect(self.screen, pygame.Color(border_color), rect, 2)
        
        text_surface = self.font.render(zone_obj.name, True, pygame.Color(text_color))
        cx_px = int(zone_obj.center.x * SCALE)
        cy_px = int(self.canvas_height - (zone_obj.center.y * SCALE))
        text_rect = text_surface.get_rect(center=(cx_px, cy_px))
        
        self.screen.blit(text_surface, text_rect)

    def draw_estimation_circle(self, zone_obj, marge_cm, color="lightblue"):
        # Appel à la fonction de la classe Zone
        rayon_cm = zone_obj.estime_zone(marge_cm)
        rayon_px = int(rayon_cm * SCALE)
        
        # Calcul du centre du cercle (Pygame a besoin du centre, pas du coin haut gauche)
        cx_px = int(zone_obj.center.x * SCALE)
        cy_px = int(self.canvas_height - (zone_obj.center.y * SCALE))
        
        # On dessine un contour de cercle (le '2' à la fin indique l'épaisseur en pixels)
        # Si on enlève le 2, ça remplit le cercle entier et cache le terrain.
        pygame.draw.circle(self.screen, pygame.Color(color), (cx_px, cy_px), rayon_px, 2)


    def draw_rotated_robot(self, zone_obj, color, border_color="black"):
        cx_cm = zone_obj.center.x
        cy_cm = zone_obj.center.y
        angle_rad = zone_obj.center.angle if zone_obj.center.angle is not None else 0.0

        w2 = zone_obj.width / 2
        h2 = zone_obj.height / 2

        # 1. Définition des 4 coins par rapport au centre (Avant rotation)
        # Comme l'angle 0 pointe vers +X, l'avant correspond aux X positifs (w2)
        coins = [
            (w2, h2),   # Avant-gauche
            (-w2, h2),  # Arrière-gauche
            (-w2, -h2), # Arrière-droit
            (w2, -h2)   # Avant-droit
        ]

        # 2. Application de la matrice de rotation sur les 4 coins
        coins_px = []
        for x, y in coins:
            x_rot = x * math.cos(angle_rad) - y * math.sin(angle_rad)
            y_rot = x * math.sin(angle_rad) + y * math.cos(angle_rad)

            # Conversion en pixels et inversion de l'axe Y
            px = int((cx_cm + x_rot) * SCALE)
            py = int(self.canvas_height - ((cy_cm + y_rot) * SCALE))
            coins_px.append((px, py))

        # 3. Dessin du polygone tourné
        pygame.draw.polygon(self.screen, pygame.Color(color), coins_px)
        pygame.draw.polygon(self.screen, pygame.Color(border_color), coins_px, 2)

        # 4. Dessin du trait rouge pour montrer "l'avant" du robot
        centre_px_x = int(cx_cm * SCALE)
        centre_px_y = int(self.canvas_height - (cy_cm * SCALE))
        
        avant_x = w2 * math.cos(angle_rad)
        avant_y = w2 * math.sin(angle_rad)
        avant_px_x = int((cx_cm + avant_x) * SCALE)
        avant_px_y = int(self.canvas_height - ((cy_cm + avant_y) * SCALE))
        
        pygame.draw.line(self.screen, pygame.Color("red"), (centre_px_x, centre_px_y), (avant_px_x, avant_px_y), 4)

    def draw_map(self):

        for key, zone in self.carte.ramassage.items():
            self.draw_estimation_circle(zone, marge_cm=7, color="deepskyblue")

        # Thermomètre
        #for key, zone in self.carte.thermometre.items():
        #    self.draw_zone(zone, "lightcoral")
            
        # Exclusion
        for key, zone in self.carte.exclusion.items():
            self.draw_zone(zone, "lightgray")
            
        # Nids
        for key, zone in self.carte.nids.items():
            color = "yellow" if key == "yellow" else "lightblue"
            self.draw_zone(zone, color)
            
        # Garde Mangers
        for key, zone in self.carte.garde_mangers.items():
            self.draw_estimation_circle(zone, marge_cm=5, color="lightblue")
            self.draw_zone(zone, "lightgreen")
            
        # Ramassage
        #for key, zone in self.carte.ramassage.items():
        #    self.draw_zone(zone, "orange")

        # Object mobile 
        #if hasattr(self.carte, 'curseur'):
        #    for key, zone in self.carte.curseur.items():
        #        self.draw_zone(zone, "gray")

        if hasattr(self.carte, 'robot'):
            for key, zone in self.carte.robot.items():
                self.draw_rotated_robot(zone, "dimgray")

        if hasattr(self.carte, 'caisses'):
            for key, zone in self.carte.caisses.items():
                self.draw_zone(zone, "yellow", border_color="saddlebrown", text_color="black")

    def update_logic(self):
        """C'est ici que tu mettras à jour la position de ton robot !"""
        # Exemple : Lire le port série ou les variables de tes capteurs.
        # Si tu modifies `self.carte.robot["mon_robot"].center.x` ici, 
        # le dessin s'actualisera tout seul à la prochaine frame.
        pass

    def run(self):
        running = True
        
        while running:
            # 1. Gestion des événements (clics, clavier, fermeture de fenêtre)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # 2. Mise à jour des positions (lecture capteurs)
            self.update_logic()

            # 3. Dessin de la frame
            if self.bg_image:
                self.screen.blit(self.bg_image, (0, 0)) # Affiche l'image de fond
            else:
                self.screen.fill(pygame.Color("white")) # Fond blanc par défaut

            self.draw_map() # Dessine toutes les zones par dessus

            # 4. Actualisation de l'écran
            pygame.display.flip()

            # 5. Limitation des FPS à 60 (pour ne pas surcharger le processeur)
            self.clock.tick(60)

        # Quitter proprement à la fin de la boucle
        pygame.quit()
        sys.exit()
   
    def update_display(self):
        """Met à jour l'écran une seule fois. Remplace la boucle 'run()'."""
        # 1. Gérer les événements (pour éviter que la fenêtre ne "plante")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # 2. Dessiner le fond
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(pygame.Color("white"))

        # 3. Dessiner la carte et ses éléments
        self.draw_map()

        # 4. Actualiser l'écran et limiter les FPS
        pygame.display.flip()
        self.clock.tick(60) # 60 images par seconde


if __name__ == "__main__":
    # 1. Instanciation de la logique
    carte_jaune = Map(team="yellow")
    
    # 2. Création de l'application Pygame
    app = MapGUI(carte_jaune, image_path="img/table_FINALE_1.0-1.png") 
    
    # 3. Lancement de la boucle infinie
    app.run()