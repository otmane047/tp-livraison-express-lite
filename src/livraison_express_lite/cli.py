"""Interface en ligne de commande : le point d'entrée non HTTP.

```bash
python -m livraison_express serve                      # démarre l'API
python -m livraison_express train                      # entraîne et sauvegarde le modèle
python -m livraison_express predict --file order.json  # prédiction en local, sans serveur
```

Pourquoi une CLI en plus de l'API ? Parce que toutes les opérations d'un projet ML ne
sont pas des requêtes HTTP : l'entraînement est ici un **job** (CI, cron),
pas un endpoint. Exposer un `POST /train` serait une erreur d'architecture :
n'importe qui pourrait consommer le CPU/GPU du service de prédiction.

Code de sortie : `0` = succès, `1` = échec. Un job en CI qui renvoie 0 après un
entraînement raté est un piège silencieux, d'où le `try/except` central de `main()`
qui journalise l'erreur complète et renvoie 1 (la trace part dans stderr, pas dans
un faux succès).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

try:
    from .domain.entities import OrderEntity
except (ImportError, ValueError):
    from src.livraison_express_lite.domain.entities import OrderEntity

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """On construit les arguments de la ligne de commande (`serve`, `train`, `predict`)."""
    parser = argparse.ArgumentParser(
        prog="livraison_express",
        description="Outils du projet eligibilite-livraison-express.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    serve = subcommands.add_parser("serve", help="Démarrer l'API de prédiction.")
    serve.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute (défaut : %(default)s).")
    serve.add_argument("--port", type=int, default=8000, help="Port d'écoute (défaut : %(default)s).")

    subcommands.add_parser(
        "train",
        help="Entraîner le modèle et écrire ses artefacts (MODEL_PATH).",
    )

    predict = subcommands.add_parser(
        "predict",
        help="Prédire l'éligibilité d'une commande lue dans un fichier JSON.",
    )
    predict.add_argument(
        "--file",
        required=True,
        help="Fichier JSON contenant une commande (champs du schéma OrderFeatures).",
    )

    orchestrate = subcommands.add_parser(
        "orchestrate",
        help="Surveiller les nouvelles données et réentraîner le modèle si nécessaire.",
    )
    orchestrate.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Intervalle de vérification en secondes (défaut : %(default)s).",
    )
    orchestrate.add_argument(
        "--min-orders",
        type=int,
        default=50,
        help="Nombre de nouvelles commandes minimum pour déclencher le réentraînement.",
    )
    orchestrate.add_argument(
        "--once",
        action="store_true",
        help="Effectuer une seule vérification puis quitter.",
    )
    orchestrate.add_argument(
        "--force",
        action="store_true",
        help="Forcer le réentraînement immédiatement.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """On renvoie les arguments de la ligne de commande vers les fonctions Python associées
    et on retourne un code (succès = 0, échec = 1).
    """
    args = build_parser().parse_args(argv)
    try:
        if args.command == "serve":
            return _serve(args)
        if args.command == "train":
            return _train()
        if args.command == "predict":
            return _predict(args.file)
        if args.command == "orchestrate":
            return _orchestrate(args)
    except KeyboardInterrupt:
        print("Interrompu.", file=sys.stderr)
        return 1
    except Exception:  # fin du processus : trace complète sur stderr, exit 1
        traceback.print_exc()
        return 1
    return 1  # Si aucune condition n'est réunie, on retourne un échec.


def _serve(args: argparse.Namespace) -> int:
    """On lance l'API sur le port 8000 par défaut."""
    import uvicorn

    try:
        from .api.app import create_app
    except (ImportError, ValueError):
        from src.livraison_express_lite.api.app import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def _train() -> int:
    """Entrainement du modèle de machine learning."""
    try:
        from .core.core import Core
    except (ImportError, ValueError):
        from src.livraison_express_lite.core.core import Core

    started_at = time.perf_counter()
    core = Core()
    logger.info("Début de l'entraînement du modèle")
    core.train_model()
    logger.info("Entraînement terminé avec succès en %.2f s", time.perf_counter() - started_at)
    return 0


def _predict(file_path: str) -> int:
    """Charger le modèle persisté puis prédire une commande JSON."""
    try:
        from .core.core import Core
    except (ImportError, ValueError):
        from src.livraison_express_lite.core.core import Core

    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    order = OrderEntity(**payload)
    core = Core(load_model=True)
    predict_service = core.get_predict_service()

    if predict_service is None:
        print(
            f"Modèle indisponible ({core.get_settings().model_path}) : "
            "lancez `python -m livraison_express train` d'abord.",
            file=sys.stderr,
        )
        return 1

    prediction = predict_service.predict(order)
    print(json.dumps(asdict(prediction), ensure_ascii=False, indent=2))
    return 0


def _orchestrate(args: argparse.Namespace) -> int:
    """Surveillance et réentraînement périodique du modèle."""
    try:
        from .core.orchestrator import ModelRetrainOrchestrator
    except (ImportError, ValueError):
        from src.livraison_express_lite.core.orchestrator import ModelRetrainOrchestrator

    orchestrator = ModelRetrainOrchestrator(min_new_orders=args.min_orders)
    if args.once:
        orchestrator.evaluate_and_retrain(force=args.force)
        return 0
    orchestrator.run_loop(interval_seconds=args.interval)
    return 0
