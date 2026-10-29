"""Orchestrateur de réentraînement continu du modèle Machine Learning.

Surveille l'arrivée de nouvelles commandes dans le dépôt de données (PostgreSQL, MongoDB, etc.)
et déclenche automatiquement le réentraînement lorsque le volume de nouvelles données
atteint un seuil paramétré et que la qualité du modèle est validée (quality gate).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import Core

logger = logging.getLogger(__name__)


class ModelRetrainOrchestrator:
    """Orchestrateur responsable de l'évaluation et du réentraînement périodique du modèle."""

    def __init__(
        self,
        core: Core | None = None,
        min_new_orders: int = 50,
        min_f1_threshold: float = 0.65,
        state_file: str | Path = "artifacts/orchestrator_state.json",
    ) -> None:
        self.core = core or Core(load_model=False)
        self.min_new_orders = min_new_orders
        self.min_f1_threshold = min_f1_threshold
        self.state_file = Path(state_file)
        self._state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Charge l'état d'orchestration persisté s'il existe."""
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Impossible de lire l'état de l'orchestrateur (%s) : %s", self.state_file, e)
        return {
            "last_trained_order_count": 0,
            "last_trained_at": None,
            "last_run_id": None,
            "last_metrics": None,
            "status": "initialized",
        }

    def _save_state(self, state: dict[str, Any]) -> None:
        """Persiste l'état d'orchestration."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            self._state = state
        except Exception as e:
            logger.error("Erreur lors de la sauvegarde de l'état de l'orchestrateur : %s", e)

    def evaluate_and_retrain(self, force: bool = False) -> bool:
        """Vérifie si les conditions de réentraînement sont réunies et lance le pipeline.

        Returns:
            bool: True si un réentraînement a été exécuté avec succès, False sinon.
        """
        repo = self.core.get_order_repository()
        total_orders = repo.count()
        last_count = int(self._state.get("last_trained_order_count", 0))
        new_orders = total_orders - last_count

        logger.info(
            "Vérification orchestrateur : total_commandes=%d, déjà_entraînées=%d, nouvelles=%d (seuil=%d, force=%s)",
            total_orders,
            last_count,
            new_orders,
            self.min_new_orders,
            force,
        )

        if not force and new_orders < self.min_new_orders:
            logger.info("Volume de nouvelles commandes insuffisant pour réentraîner (%d < %d)", new_orders, self.min_new_orders)
            return False

        logger.info("Démarrage du réentraînement déclenché par l'orchestrateur...")
        try:
            run_id, metrics, _, _ = self.core.train_model()
        except Exception as exc:
            logger.exception("Échec lors de l'exécution du réentraînement : %s", exc)
            return False

        f1 = float(metrics.get("f1_score", 0.0))
        logger.info("Entraînement terminé (run_id=%s, F1=%.4f)", run_id, f1)

        # Quality Gate : vérification de la performance avant validation
        if f1 < self.min_f1_threshold:
            logger.warning(
                "Quality Gate échoué : score F1=%.4f inférieur au seuil minimal requis=%.4f. Modèle non validé.",
                f1,
                self.min_f1_threshold,
            )
            return False

        # Sauvegarde de l'état mis à jour
        new_state = {
            "last_trained_order_count": total_orders,
            "last_trained_at": datetime.now(timezone.utc).isoformat(),
            "last_run_id": run_id,
            "last_metrics": metrics,
            "status": "success",
        }
        self._save_state(new_state)
        logger.info("Modèle validé et nouvel état enregistré avec succès.")
        return True

    def run_loop(self, interval_seconds: int = 60, max_iterations: int | None = None) -> None:
        """Boucle de surveillance périodique."""
        logger.info(
            "Lancement de la boucle de l'orchestrateur (intervalle=%ds, seuil_nouvelles_commandes=%d)",
            interval_seconds,
            self.min_new_orders,
        )
        iterations = 0
        try:
            while max_iterations is None or iterations < max_iterations:
                self.evaluate_and_retrain()
                iterations += 1
                if max_iterations is not None and iterations >= max_iterations:
                    break
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Arrêt de l'orchestrateur demandé par l'utilisateur.")
