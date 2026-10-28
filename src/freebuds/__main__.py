"""Permite executar o pacote com ``python -m freebuds``."""

from .cli.app import main

if __name__ == "__main__":
    raise SystemExit(main())
