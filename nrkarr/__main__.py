import logging
import os

from waitress import serve

from .app import create_app
from .config import load


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load(os.environ.get("NRKARR_CONFIG", "config.yml"))
    app = create_app(config)

    serve(
        app,
        host=config["server"]["host"],
        port=config["server"]["port"],
        threads=8,
    )


if __name__ == "__main__":
    main()
