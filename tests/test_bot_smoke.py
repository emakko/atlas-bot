from pathlib import Path

import aiohttp

from atlas.bot import EXTENSIONS, AtlasBot
from atlas.config import Settings, load_catalog
from atlas.storage import Storage

ROOT = Path(__file__).resolve().parents[1]


async def test_extensions_load_and_register_commands():
    settings = Settings(
        token="x",
        dev_guild_id=None,
        db_path=Path(":memory:"),
        sources_file=ROOT / "sources.yaml",
        catalog=load_catalog(ROOT / "sources.yaml"),
    )
    bot = AtlasBot(settings)
    bot.storage = await Storage.open(":memory:")
    bot.http_session = aiohttp.ClientSession()
    try:
        for ext in EXTENSIONS:
            await bot.load_extension(ext)
        names = {c.qualified_name for c in bot.tree.walk_commands()}
        assert {
            "news sources", "news latest", "news subscribe", "news unsubscribe",
            "news subscriptions", "mensa", "links",
        } <= names
        # Payloads must be valid for Discord (names, option limits, ...).
        for cmd in bot.tree.get_commands():
            cmd.to_dict(bot.tree)
    finally:
        for ext in EXTENSIONS:
            await bot.unload_extension(ext)
        await bot.http_session.close()
        await bot.storage.close()
