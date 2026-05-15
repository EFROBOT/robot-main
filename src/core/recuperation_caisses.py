import time


class RecuperationCaisses:
    def __init__(self, robot, logs=None):
        self.robot = robot
        self.logs = logs or getattr(robot, "logs", None)

    def _log(self, niveau, message):
        if self.logs:
            self.logs.log(niveau, message)
        else:
            print(f"[{niveau}] {message}")

    @staticmethod
    def _normaliser_couleur(couleur):
        if couleur is None:
            return None
        c = str(couleur).strip().lower()
        if c in ("yellow", "jaune", "y"):
            return "jaune"
        if c in ("blue", "bleu", "b"):
            return "bleu"
        return None

    def _couleur_equipe(self):
        equipe = getattr(self.robot, "team", "yellow")
        return self._normaliser_couleur(equipe)

    def _rotation_active(self, couleur_caisse, couleur_equipe):
        return 1 if couleur_caisse == couleur_equipe else 0

    def executer_cycle(self, liste_couleurs, pause_s=0.05):
        couleurs = [self._normaliser_couleur(c) for c in list(liste_couleurs or [])][:4]
        while len(couleurs) < 4:
            couleurs.append(None)

        couleur_equipe = self._couleur_equipe()
        if couleur_equipe not in ("bleu", "jaune"):
            self._log("ERR", f"Couleur équipe invalide: {getattr(self.robot, 'team', None)}")
            return False

        self._log("RPi", f"Cycle récupération: equipe={couleur_equipe}, couleurs={couleurs}")

        succes_global = True
        for index, couleur_caisse in enumerate(couleurs):
            if couleur_caisse not in ("bleu", "jaune"):
                couleur_caisse = "jaune" if couleur_equipe == "bleu" else "bleu"

            rotation = self._rotation_active(couleur_caisse, couleur_equipe)
            est_derniere = index == 3

            if est_derniere:
                ok = self.robot.pince_recuperer_et_stocker(rotation)
                commande = "Pince_RecupererEtStocker"
            else:
                ok = self.robot.pince_recuperer_avancer_et_stocker(rotation)
                commande = "Pince_RecupererAvancerEtStocker"

            succes_global = succes_global and bool(ok)
            self._log("RPi", f"{commande} rotation={rotation} -> {'OK' if ok else 'ECHEC'}")
            time.sleep(pause_s)

        self.robot.stop()
        self._log("RPi", "Cycle récupération terminé: robot STOP et attente")
        return succes_global
