from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from atlas.cogs.news import EMBED_COLOR
from atlas.config import Catalog

if TYPE_CHECKING:
    from atlas.bot import AtlasBot

PO_CHOICES = [
    app_commands.Choice(name="neu (PO 2026)", value="new"),
    app_commands.Choice(name="alt (PO 2023)", value="old"),
]
PO_LABELS = {"new": "Neu", "old": "Alt"}


def po_embed(catalog: Catalog, version: str | None = None) -> discord.Embed:
    """Links to the Prüfungsordnung documents, either one version or all of them."""
    versions = [version] if version else list(PO_LABELS)
    embed = discord.Embed(title="Prüfungsordnung – B.Sc. Software Engineering", color=EMBED_COLOR)
    for key in versions:
        doc = catalog.po_documents.get(key)
        value = f"[{doc.name}]({doc.url})" if doc else "Not configured."
        embed.add_field(name=PO_LABELS[key], value=value, inline=False)
    if catalog.po_overview:
        embed.description = f"[All PO documents and module handbooks]({catalog.po_overview})"
    return embed


class Links(commands.Cog):
    def __init__(self, bot: AtlasBot) -> None:
        self.bot = bot

    @app_commands.command(name="links", description="Useful UDE links for Software Engineering students")
    async def links(self, interaction: discord.Interaction) -> None:
        links = self.bot.settings.catalog.links
        description = "\n".join(f"• [{l.name}]({l.url})" for l in links) or "No links configured."
        embed = discord.Embed(title="UDE quick links", description=description[:4096], color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="po", description="Prüfungsordnung / Modulhandbuch for B.Sc. Software Engineering")
    @app_commands.describe(version="Old or new PO (default: both)")
    @app_commands.choices(version=PO_CHOICES)
    async def po(
        self, interaction: discord.Interaction, version: app_commands.Choice[str] | None = None
    ) -> None:
        embed = po_embed(self.bot.settings.catalog, version.value if version else None)
        await interaction.response.send_message(embed=embed)


async def setup(bot: AtlasBot) -> None:
    await bot.add_cog(Links(bot))
