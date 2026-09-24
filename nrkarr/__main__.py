import os

from .app import create_app
from .config import load


def main():
    config = load(os.environ.get("NRKARR_CONFIG", "config.yml"))
    app = create_app(config)

    app.run(
        host=config["server"]["host"],
        port=config["server"]["port"],
    )


if __name__ == "__main__":
    main()
