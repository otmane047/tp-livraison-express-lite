"""Point d'entrée racine du projet.

Permet de :
1. Lancer l'API via Uvicorn :
   uvicorn main:app --reload

2. Utiliser la CLI :
   python main.py serve
   python main.py train
   python main.py predict --file order.json
"""

import sys

try:
    from src.livraison_express_lite.api.app import app
    from src.livraison_express_lite.cli import main
except ImportError:
    from livraison_express_lite.api.app import app
    from livraison_express_lite.cli import main

__all__ = ["app"]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(main())
    else:
        sys.exit(main(["serve"]))
