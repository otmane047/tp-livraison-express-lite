"""Permet `python -m livraison_express ...`."""

import sys

try:
    from livraison_express_lite.cli import main
except ImportError:
    from src.livraison_express_lite.cli import main

if __name__ == "__main__":
    sys.exit(main())

