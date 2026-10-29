"""Script de lancement du serveur API.

Usage:
    python scripts/run_server.py [--host 127.0.0.1] [--port 8000]
"""

import sys
from pathlib import Path

# Ajoute la racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from src.livraison_express_lite.cli import main
except ImportError:
    from livraison_express_lite.cli import main

if __name__ == "__main__":
    args = ["serve"] + sys.argv[1:]
    sys.exit(main(args))
