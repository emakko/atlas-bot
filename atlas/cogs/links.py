from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from atlas.cogs.news import EMBED_COLOR

if TYPE_CHECKING:
    from atlas.bot import AtlasBot


class Links(commands.Cog):
    def __init__(self, bot: AtlasBot) -> None:
        self.bot = bot

    @app_commands.command(name="links", description="Useful UDE links for Software Engineering students")
    async def links(self, interaction: discord.Interaction) -> None:
        links = self.bot.settings.catalog.links
        description = "\n".join(f"• [{l.name}]({l.url})" for l in links) or "No links configured."
        embed = discord.Embed(title="UDE quick links", description=description[:4096], color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed)


async def setup(bot: AtlasBot) -> None:
    await bot.add_cog(Links(bot))
