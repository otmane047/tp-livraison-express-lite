"""Script d'entraînement du modèle Machine Learning.

Usage:
    python scripts/train.py
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
    sys.exit(main(["train"]))
