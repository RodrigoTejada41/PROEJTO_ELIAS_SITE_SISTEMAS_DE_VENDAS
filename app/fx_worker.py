"""Check the public reference while the Docker worker is running."""

import logging
import time

import psycopg

from app.fx import refresh

logging.basicConfig(level=logging.INFO)


def main():
    while True:
        try:
            changed = refresh()
            logging.info("Referência cambial verificada. Atualizada: %s", changed)
        except psycopg.Error:
            logging.error("Falha no banco durante consulta cambial.")
        time.sleep(3600)


if __name__ == "__main__":
    main()
