"""
Système de journalisation multi-sources pour EFROBOT.

Chaque source écrit dans un fichier dédié ET dans le fichier combiné robot.log.
Les buffers en mémoire sont également séparés par source.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path


# Correspondance source → nom de fichier de log
_SOURCE_FILE_MAP = {
    "STM32": "stm32.log",
    "RPi":   "rpi.log",
    "ERR":   "erreurs.log",
    "WARN":  "erreurs.log",
    "LIDAR": "lidar.log",
    "INFO":  "info.log",
}

# Catégories de sources disponibles (clé = catégorie, valeur = fichier)
_CATEGORIES = {
    "STM32": "stm32.log",
    "RPi":   "rpi.log",
    "ERR":   "erreurs.log",
    "WARN":  "erreurs.log",
    "LIDAR": "lidar.log",
    "INFO":  "info.log",
}

# Fichier combiné contenant tous les logs
_COMBINED_FILE = "robot.log"


class Logs:
    """Gestionnaire de logs multi-sources avec fichiers séparés."""

    def __init__(self, maxlen=200):
        # Répertoire de base pour tous les fichiers de log
        self._log_dir = Path(__file__).resolve().parents[2] / "data" / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Fichier combiné (tous les logs)
        self._combined_path = self._log_dir / _COMBINED_FILE

        # Buffer combiné en mémoire
        self.buffer = deque(maxlen=maxlen)

        # Buffers séparés par catégorie de source
        self._maxlen = maxlen
        self._buffers: dict[str, deque] = {}

        # Pré-créer les buffers pour chaque catégorie connue
        for source in _CATEGORIES:
            self._buffers[source] = deque(maxlen=maxlen)

    # ── Propriété de compatibilité ─────────────────────────────
    @property
    def log_file(self) -> Path:
        """Chemin du fichier combiné (rétrocompatibilité)."""
        return self._combined_path

    # ── Résolution du fichier selon la source ──────────────────
    def _fichier_pour_source(self, source: str) -> Path:
        """Retourne le chemin du fichier de log associé à une source."""
        nom = _SOURCE_FILE_MAP.get(source, "info.log")
        return self._log_dir / nom

    # ── Écriture d'un log ──────────────────────────────────────
    def log(self, source: str, message: str) -> None:
        """Enregistre un message dans le fichier source, le fichier combiné et la console."""
        line = f"[{source}] {message}"

        # Buffer combiné en mémoire
        self.buffer.append(line)

        # Buffer spécifique à la source
        if source not in self._buffers:
            self._buffers[source] = deque(maxlen=self._maxlen)
        self._buffers[source].append(line)

        # Écriture dans le fichier spécifique à la source
        fichier_source = self._fichier_pour_source(source)
        with fichier_source.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        # Écriture dans le fichier combiné
        with self._combined_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        print(line, flush=True)

    # ── Lecture des logs ───────────────────────────────────────
    def get_lines(self) -> list[str]:
        """Retourne toutes les lignes du buffer combiné."""
        return list(self.buffer)

    def get_lines_by_source(self, source: str) -> list[str]:
        """Retourne les lignes du buffer pour une source donnée."""
        normalized = (source or "").strip()
        aliases = {
            "stm32": "STM32",
            "rpi": "RPi",
            "err": "ERR",
            "warn": "WARN",
            "lidar": "LIDAR",
            "info": "INFO",
            "erreurs": "ERREURS",
        }
        normalized = aliases.get(normalized.lower(), normalized)

        if normalized == "ERREURS":
            errs = list(self._buffers.get("ERR", ()))
            warns = list(self._buffers.get("WARN", ()))
            return errs + warns

        buf = self._buffers.get(normalized)
        if buf is None:
            return []
        return list(buf)

    # ── Métadonnées ────────────────────────────────────────────
    def get_sources(self) -> list[str]:
        """Retourne la liste des catégories de sources disponibles."""
        return sorted(_CATEGORIES.keys())

    def get_log_files(self) -> dict[str, str]:
        """Retourne un dict catégorie → chemin absolu du fichier de log."""
        result = {}
        for source, nom_fichier in _CATEGORIES.items():
            result[source] = str(self._log_dir / nom_fichier)
        # Ajouter le fichier combiné
        result["ALL"] = str(self._combined_path)
        return result
