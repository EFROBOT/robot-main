import pygame
import sys
from Map import Map

TERRAIN_WIDTH  = 300.0
TERRAIN_HEIGHT = 200.0
SCALE = 4 

class MapGUI:
    def __init__(self, carte, image_path=None):
        # Initialisation obligatoire de pygame
        pygame.init()
        self.carte = carte
        
        # Dimensions de la fenêtre
        self.canvas_width = int(TERRAIN_WIDTH * SCALE)
        self.canvas_height = int(TERRAIN_HEIGHT * SCALE)
        
        # Création de la fenêtre
        self.screen = pygame.display.set_mode((self.canvas_width, self.canvas_height))
        pygame.display.set_caption(f"Carte Eurobot - Team {self.carte.team.capitalize()}")
        
        # Horloge pour contrôler les FPS (Images par seconde)
        self.clock = pygame.time.Clock()
        
        # Police pour le texte (taille 12, en gras)
        self.font = pygame.font.SysFont("Arial", 12, bold=True)
        
        # --- LOGIQUE : CHARGEMENT DE L'IMAGE ---
        self.bg_image = None
        if image_path:
            try:
                # 1. Ouvrir l'image avec Pygame
                raw_image = pygame.image.load(image_path)
                # 2. La redimensionner aux dimensions du canvas
                self.bg_image = pygame.transform.scale(raw_image, (self.canvas_width, self.canvas_height))
                print(f"Image '{image_path}' chargée et redimensionnée.")
            except Exception as e:
                print(f"Erreur lors du chargement de l'image : {e}")
        # ---------------------------------------

    def draw_zone(self, zone_obj, color):
        """Dessine une zone rectangulaire sur la carte en inversant l'axe Y"""
        
        # 1. Calcul des dimensions en pixels
        w_px = int(zone_obj.width * SCALE)
        h_px = int(zone_obj.height * SCALE)
        
        # 2. Calcul des coordonnées (Pygame place l'origine du rectangle en haut à gauche)
        x0_px = int(zone_obj.x_min() * SCALE)
        y0_px = int(self.canvas_height - (zone_obj.y_max() * SCALE))
        
        # 3. Création de l'objet Rectangle Pygame
        rect = pygame.Rect(x0_px, y0_px, w_px, h_px)
        
        # 4. Dessin de la zone (Pygame Color comprend les noms html comme "yellow", "lightcoral")
        pygame.draw.rect(self.screen, pygame.Color(color), rect)        # Remplissage
        pygame.draw.rect(self.screen, pygame.Color("black"), rect, 2)   # Contour (épaisseur 2)
        
        # 5. Rendu et centrage du texte
        text_surface = self.font.render(zone_obj.name, True, pygame.Color("black"))
        cx_px = int(zone_obj.center.x * SCALE)
        cy_px = int(self.canvas_height - (zone_obj.center.y * SCALE))
        text_rect = text_surface.get_rect(center=(cx_px, cy_px))
        
        # 6. Affichage du texte
        self.screen.blit(text_surface, text_rect)

    def draw_map(self):
        """Parcourt tous les dictionnaires et les dessine avec une couleur spécifique"""
        
        # Thermomètre
        for key, zone in self.carte.thermometre.items():
            self.draw_zone(zone, "lightcoral")
            
        # Exclusion
        for key, zone in self.carte.exclusion.items():
            self.draw_zone(zone, "lightgray")
            
        # Nids
        for key, zone in self.carte.nids.items():
            color = "yellow" if key == "yellow" else "lightblue"
            self.draw_zone(zone, color)
            
        # Garde Mangers
        for key, zone in self.carte.garde_mangers.items():
            self.draw_zone(zone, "lightgreen")
            
        # Ramassage
        for key, zone in self.carte.ramassage.items():
            self.draw_zone(zone, "orange")

        # Curseur et Robot
        # (J'utilise hasattr pour éviter les crashs si les attributs ne sont pas initialisés)
        if hasattr(self.carte, 'curseur'):
            for key, zone in self.carte.curseur.items():
                self.draw_zone(zone, "gray")

        if hasattr(self.carte, 'robot'):
            for key, zone in self.carte.robot.items():
                self.draw_zone(zone, "dimgray")


    def update_logic(self):
        """C'est ici que tu mettras à jour la position de ton robot !"""
        # Exemple : Lire le port série ou les variables de tes capteurs.
        # Si tu modifies `self.carte.robot["mon_robot"].center.x` ici, 
        # le dessin s'actualisera tout seul à la prochaine frame.
        pass

    def run(self):
        """La boucle principale (Main Loop) du programme"""
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


if __name__ == "__main__":
    # 1. Instanciation de la logique
    carte_jaune = Map(team="yellow")
    
    # 2. Création de l'application Pygame
    app = MapGUI(carte_jaune, image_path="img/table_FINALE_1.0-1.png") 
    
    # 3. Lancement de la boucle infinie
    app.run()