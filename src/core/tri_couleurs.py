import random
import time
from collections import Counter, defaultdict


class TriCouleursCaisses:
    """Utilitaires robustes pour estimer l'ordre des 4 caisses (2 bleu / 2 jaune).

    Cette version est pensée pour être branchée facilement sur un détecteur ArUco
    existant via une fonction `frame_provider` et `detecteur.detect_markers(frame)`.
    """

    def __init__(self, logs=None):
        self.logs = logs

    def _log(self, niveau, message):
        if self.logs is not None:
            self.logs.log(niveau, message)

    @staticmethod
    def _normaliser_couleur(couleur):
        if couleur is None:
            return None
        c = str(couleur).strip().lower()
        if c in ("bleu", "blue"):
            return "bleu"
        if c in ("jaune", "yellow"):
            return "jaune"
        return None

    @staticmethod
    def trier_caisses_par_ordre_devant_soi(caisses):
        """Trie les caisses de la plus proche à la plus lointaine.

        Le code existant utilise souvent la plus lointaine comme repère d'alignement,
        mais pour reconstruire l'ordre des 4 caisses, un tri stable par distance est
        simple et robuste.
        """
        return sorted(caisses, key=lambda c: float(getattr(c, "distance", 10**9)))

    def extraire_ordre_couleurs_frame(self, caisses):
        """Retourne un ordre partiel de couleurs pour une frame: [c1, c2, ...].

        Les valeurs sont normalisées en `bleu`/`jaune`. Les éléments inconnus sont
        ignorés.
        """
        triees = self.trier_caisses_par_ordre_devant_soi(caisses)
        ordre = []
        for caisse in triees[:4]:
            couleur = self._normaliser_couleur(getattr(caisse, "equipe", None))
            if couleur is not None:
                ordre.append(couleur)
        return ordre

    @staticmethod
    def _completer_avec_contrainte_2_2(ordre_partiel, rng=None):
        """Complète une liste partielle pour obtenir 4 caisses avec 2 bleu / 2 jaune.

        Les cases manquantes sont remplies aléatoirement sous contrainte de bilan.
        """
        rng = rng or random
        base = list(ordre_partiel[:4])

        nb_bleu = sum(1 for c in base if c == "bleu")
        nb_jaune = sum(1 for c in base if c == "jaune")

        # Sécurité: si un bruit excessif casse déjà la contrainte, on repart proprement.
        if nb_bleu > 2 or nb_jaune > 2:
            base = [c for c in base if c in ("bleu", "jaune")]
            while sum(1 for c in base if c == "bleu") > 2:
                base.remove("bleu")
            while sum(1 for c in base if c == "jaune") > 2:
                base.remove("jaune")
            nb_bleu = sum(1 for c in base if c == "bleu")
            nb_jaune = sum(1 for c in base if c == "jaune")

        manquants = []
        manquants.extend(["bleu"] * (2 - nb_bleu))
        manquants.extend(["jaune"] * (2 - nb_jaune))
        rng.shuffle(manquants)

        while len(base) < 4 and manquants:
            base.append(manquants.pop())

        # Ultime garde-fou si la liste n'atteint pas 4 (cas pathologique).
        while len(base) < 4:
            base.append(rng.choice(["bleu", "jaune"]))

        return base[:4]

    def consolider_ordre_couleurs(
        self,
        frame_provider,
        detecteur,
        nb_captures=12,
        timeout_s=1.2,
        pause_s=0.03,
        graine_aleatoire=None,
    ):
        """Construit un ordre robuste des couleurs sur plusieurs captures.

        Retourne un dictionnaire avec:
        - ordre_final: liste de 4 couleurs ["bleu"|"jaune", ...]
        - confiance_par_position: dict {1..4: score_0_1}
        - captures_utiles: nombre de captures ayant fourni >=1 couleur
        - details: infos de debug compactes
        """
        rng = random.Random(graine_aleatoire)
        debut = time.time()

        votes_par_position = defaultdict(Counter)
        captures_total = 0
        captures_utiles = 0

        while captures_total < nb_captures and (time.time() - debut) < timeout_s:
            captures_total += 1
            frame = frame_provider() if frame_provider is not None else None
            if frame is None:
                time.sleep(pause_s)
                continue

            try:
                caisses = detecteur.detect_markers(frame)
            except Exception as exc:
                self._log("ERR", f"tri_couleurs: detect_markers a échoué: {exc}")
                time.sleep(pause_s)
                continue

            ordre = self.extraire_ordre_couleurs_frame(caisses)
            if not ordre:
                time.sleep(pause_s)
                continue

            captures_utiles += 1
            for i, couleur in enumerate(ordre[:4], start=1):
                votes_par_position[i][couleur] += 1

            time.sleep(pause_s)

        ordre_partiel = []
        confiance_par_position = {}
        for pos in range(1, 5):
            votes = votes_par_position.get(pos, Counter())
            if not votes:
                confiance_par_position[pos] = 0.0
                continue

            couleur_majoritaire, nb_votes = votes.most_common(1)[0]
            total = sum(votes.values())
            confiance = (nb_votes / total) if total else 0.0
            ordre_partiel.append(couleur_majoritaire)
            confiance_par_position[pos] = round(confiance, 3)

        ordre_final = self._completer_avec_contrainte_2_2(ordre_partiel, rng=rng)

        self._log(
            "INFO",
            (
                "tri_couleurs: "
                f"captures={captures_total}, utiles={captures_utiles}, "
                f"partiel={ordre_partiel}, final={ordre_final}, "
                f"confiance={confiance_par_position}"
            ),
        )

        return {
            "ordre_final": ordre_final,
            "confiance_par_position": confiance_par_position,
            "captures_utiles": captures_utiles,
            "details": {
                "captures_total": captures_total,
                "ordre_partiel": ordre_partiel,
            },
        }
