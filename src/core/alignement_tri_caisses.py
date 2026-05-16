import threading
import time

from core.tri_couleurs import TriCouleursCaisses
from core.affinite_cpu import fixer_affinite_cpu


class AlignementTriCaisses:
    """Lance l'alignement ArUco et le tri des couleurs en parallèle."""

    def __init__(self, strategy, logs=None):
        self.strategy = strategy
        self.logs = logs if logs is not None else getattr(strategy.robot, "logs", None)
        self.tri = TriCouleursCaisses(logs=self.logs)

    def _log(self, niveau, message):
        if self.logs is not None:
            self.logs.log(niveau, message)

    def lancer(self, timeout_alignement_s=15.0):
        """Exécute l'alignement et le tri des couleurs.

        Le frame_provider est lu depuis self.strategy.frame_provider (injecté par
        AffichageWeb ou aligner_et_recuperer_caisses avant l'appel).

        Retour:
            {
              "aligne": bool,
              "ordre_couleurs": ["bleu"|"jaune", x4],
              "resultat_alignement": any,
            }
        """
        frame_provider = getattr(self.strategy, "frame_provider", None)

        stop_tri = threading.Event()
        lock_resultat = threading.Lock()

        meilleur_resultat_tri = {
            "ordre_final": ["bleu", "bleu", "jaune", "jaune"],
            "confiance_par_position": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
            "captures_utiles": 0,
            "details": {"captures_total": 0, "ordre_partiel": []},
        }

        def boucle_tri_couleurs():
            fixer_affinite_cpu(2, logs=self.logs, nom_thread="tri_couleurs")
            nonlocal meilleur_resultat_tri
            while not stop_tri.is_set():
                resultat = self.tri.consolider_ordre_couleurs(
                    frame_provider=frame_provider,
                    detecteur=self.strategy.robot.camera.aruco,
                    nb_captures=8,
                    timeout_s=0.7,
                    pause_s=0.02,
                )

                with lock_resultat:
                    score_nouveau = (
                        resultat.get("captures_utiles", 0),
                        sum(resultat.get("confiance_par_position", {}).values()),
                    )
                    score_actuel = (
                        meilleur_resultat_tri.get("captures_utiles", 0),
                        sum(meilleur_resultat_tri.get("confiance_par_position", {}).values()),
                    )
                    if score_nouveau >= score_actuel:
                        meilleur_resultat_tri = resultat

                time.sleep(0.01)

        self._log("INFO", "Alignement+tri: démarrage.")
        thread_tri = threading.Thread(target=boucle_tri_couleurs, daemon=True)
        thread_tri.start()

        try:
            resultat_alignement = self.strategy.aligner_sur_aruco(
                timeout_s=timeout_alignement_s,
                frame_provider=frame_provider,
            )
            aligne = bool(resultat_alignement)
        finally:
            stop_tri.set()
            thread_tri.join(timeout=0.8)

        with lock_resultat:
            ordre_couleurs = list(meilleur_resultat_tri.get("ordre_final", []))

        self._log("INFO", f"Alignement+tri: ordre final={ordre_couleurs}")
        print(f"[ALIGNEMENT+TRI] Ordre couleurs: {ordre_couleurs}")

        return {
            "aligne": aligne,
            "ordre_couleurs": ordre_couleurs,
            "resultat_alignement": resultat_alignement,
            "resultat_tri": meilleur_resultat_tri,
        }