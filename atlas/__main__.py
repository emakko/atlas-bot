import logging

from dotenv import load_dotenv

from atlas.bot import AtlasBot
from atlas.config import load_settings


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    )
    settings = load_settings()
    AtlasBot(settings).run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
