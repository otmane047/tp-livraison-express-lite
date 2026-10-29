"""Script d'exécution de l'orchestrateur de réentraînement continu.

Usage:
    python scripts/orchestrator.py [--interval SEC] [--min-orders N] [--once] [--force]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ajoute la racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.livraison_express_lite.core.orchestrator import ModelRetrainOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orchestrateur de réentraînement continu du modèle ML.")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("ORCHESTRATOR_INTERVAL", "60")),
        help="Intervalle de vérification en secondes (défaut : %(default)s).",
    )
    parser.add_argument(
        "--min-orders",
        type=int,
        default=int(os.getenv("ORCHESTRATOR_MIN_ORDERS", "50")),
        help="Nombre minimal de nouvelles commandes pour déclencher le réentraînement (défaut : %(default)s).",
    )
    parser.add_argument(
        "--min-f1",
        type=float,
        default=float(os.getenv("ORCHESTRATOR_MIN_F1", "0.65")),
        help="Seuil F1 minimal pour valider le nouveau modèle (défaut : %(default)s).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Exécute une seule vérification et termine le processus immédiatement (mode batch/cron).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force le réentraînement sans vérifier le nombre minimal de nouvelles commandes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    orchestrator = ModelRetrainOrchestrator(
        min_new_orders=args.min_orders,
        min_f1_threshold=args.min_f1,
    )

    if args.once:
        success = orchestrator.evaluate_and_retrain(force=args.force)
        return 0 if success else 0  # 0 même si aucune commande nouvelle n'était présente
    else:
        orchestrator.run_loop(interval_seconds=args.interval)
        return 0


if __name__ == "__main__":
    sys.exit(main())
