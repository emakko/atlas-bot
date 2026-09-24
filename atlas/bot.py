from __future__ import annotations

import logging

import aiohttp
import discord
from discord.ext import commands

from atlas.config import Settings
from atlas.storage import Storage

log = logging.getLogger(__name__)

EXTENSIONS = ("atlas.cogs.news", "atlas.cogs.mensa", "atlas.cogs.links")


class AtlasBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self.storage: Storage
        self.http_session: aiohttp.ClientSession

    async def setup_hook(self) -> None:
        self.storage = await Storage.open(self.settings.db_path)
        self.http_session = aiohttp.ClientSession()
        for ext in EXTENSIONS:
            await self.load_extension(ext)

        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %d commands to dev guild %s", len(synced), guild.id)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d global commands", len(synced))

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id if self.user else "?")

    async def close(self) -> None:
        await super().close()
        if hasattr(self, "http_session"):
            await self.http_session.close()
        if hasattr(self, "storage"):
            await self.storage.close()
