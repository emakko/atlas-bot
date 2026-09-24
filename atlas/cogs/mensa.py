from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from atlas import mensa
from atlas.cogs.news import EMBED_COLOR

if TYPE_CHECKING:
    from atlas.bot import AtlasBot

log = logging.getLogger(__name__)

BERLIN = ZoneInfo("Europe/Berlin")
CANTEEN_CACHE_SECONDS = 6 * 3600
DAY_CHOICES = [
    app_commands.Choice(name="heute", value=0),
    app_commands.Choice(name="morgen", value=1),
    app_commands.Choice(name="übermorgen", value=2),
]


def format_price(value: float | None) -> str:
    return f"{value:.2f} €".replace(".", ",") if value is not None else ""


class Mensa(commands.Cog):
    mensa_group = app_commands.Group(name="mensa", description="Mensa menus near the UDE campuses")

    def __init__(self, bot: AtlasBot) -> None:
        self.bot = bot
        self._canteens: list[mensa.Canteen] = []
        self._canteens_at = 0.0

    async def _get_canteens(self) -> list[mensa.Canteen]:
        if not self._canteens or time.monotonic() - self._canteens_at > CANTEEN_CACHE_SECONDS:
            cat = self.bot.settings.catalog
            self._canteens = await mensa.canteens_near(
                self.bot.http_session, cat.mensa_points, cat.mensa_radius_km
            )
            self._canteens_at = time.monotonic()
        return self._canteens

    async def canteen_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        try:
            canteens = await self._get_canteens()
        except Exception:
            log.exception("Loading canteens failed")
            return []
        needle = current.casefold()
        return [
            app_commands.Choice(name=f"{c.name} ({c.city})"[:100] if c.city else c.name[:100], value=c.id)
            for c in canteens
            if needle in c.name.casefold() or needle in c.city.casefold()
        ][:25]

    @mensa_group.command(name="canteens", description="List canteens near the UDE campuses")
    async def canteens_cmd(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            canteens = await self._get_canteens()
        except Exception as exc:
            await interaction.followup.send(f"OpenMensa is unreachable ({exc.__class__.__name__}).")
            return
        if not canteens:
            await interaction.followup.send("OpenMensa doesn't list any canteens near the campuses.")
            return
        lines = [f"`{c.id}` – **{c.name}**" + (f" · {c.address}" if c.address else "") for c in canteens]
        embed = discord.Embed(title="Canteens near UDE", description="\n".join(lines)[:4096], color=EMBED_COLOR)
        embed.set_footer(text="Data: openmensa.org")
        await interaction.followup.send(embed=embed)

    @mensa_group.command(name="menu", description="Show a canteen's menu")
    @app_commands.describe(canteen="Canteen (start typing)", day="Which day")
    @app_commands.autocomplete(canteen=canteen_autocomplete)
    @app_commands.choices(day=DAY_CHOICES)
    async def menu(
        self,
        interaction: discord.Interaction,
        canteen: int,
        day: app_commands.Choice[int] | None = None,
    ) -> None:
        offset = day.value if day else 0
        target = (datetime.now(BERLIN) + timedelta(days=offset)).date()
        await interaction.response.defer(thinking=True)
        try:
            meals = await mensa.meals(self.bot.http_session, canteen, target)
        except Exception as exc:
            await interaction.followup.send(f"OpenMensa is unreachable ({exc.__class__.__name__}).")
            return

        canteens = {c.id: c for c in self._canteens}
        name = canteens[canteen].name if canteen in canteens else f"Mensa {canteen}"
        title = f"{name} – {target.strftime('%a, %d.%m.%Y')}"
        if not meals:
            await interaction.followup.send(f"**{title}**\nNo menu published (closed or not yet available).")
            return

        by_category: dict[str, list[mensa.Meal]] = defaultdict(list)
        for meal in meals:
            by_category[meal.category].append(meal)

        embed = discord.Embed(title=title[:256], color=EMBED_COLOR)
        for category, items in list(by_category.items())[:25]:
            lines = []
            for m in items:
                price = format_price(m.student_price)
                lines.append(f"• {m.name}" + (f" — **{price}**" if price else ""))
            embed.add_field(name=category[:256], value="\n".join(lines)[:1024], inline=False)
        embed.set_footer(text="Student prices · Data: openmensa.org")
        await interaction.followup.send(embed=embed)


async def setup(bot: AtlasBot) -> None:
    await bot.add_cog(Mensa(bot))
