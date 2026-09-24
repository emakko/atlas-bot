from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from atlas.cogs.news import EMBED_COLOR
from atlas.config import Catalog

if TYPE_CHECKING:
    from atlas.bot import AtlasBot

PO_LABELS = {"new": "Neu – PO 2026", "old": "Alt – PO 2023"}
PO_CHOICES = [app_commands.Choice(name=label, value=key) for key, label in PO_LABELS.items()]


def po_embed(catalog: Catalog, version: str) -> discord.Embed:
    """Link to the Prüfungsordnung document of one PO version."""
    doc = catalog.po_documents.get(version)
    embed = discord.Embed(
        title=f"{PO_LABELS[version]} – B.Sc. Software Engineering",
        url=doc.url if doc else None,
        description=f"[{doc.name}]({doc.url})" if doc else "Not configured.",
        color=EMBED_COLOR,
    )
    if catalog.po_overview:
        embed.add_field(
            name="Alle Dokumente",
            value=f"[Prüfungsordnungen & Modulhandbücher]({catalog.po_overview})",
            inline=False,
        )
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
    @app_commands.describe(version="Which PO")
    @app_commands.choices(version=PO_CHOICES)
    async def po(self, interaction: discord.Interaction, version: app_commands.Choice[str]) -> None:
        embed = po_embed(self.bot.settings.catalog, version.value)
        await interaction.response.send_message(embed=embed)


async def setup(bot: AtlasBot) -> None:
    await bot.add_cog(Links(bot))
