from __future__ import annotations

import logging
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
CAMPUS_CHOICES = [app_commands.Choice(name=c.label, value=key) for key, c in mensa.CAMPUSES.items()]
DAY_CHOICES = [
    app_commands.Choice(name="heute", value=0),
    app_commands.Choice(name="morgen", value=1),
    app_commands.Choice(name="übermorgen", value=2),
]


def format_price(value: float | None) -> str:
    return f"{value:.2f} €".replace(".", ",") if value is not None else ""


class Mensa(commands.Cog):
    def __init__(self, bot: AtlasBot) -> None:
        self.bot = bot

    @app_commands.command(name="mensa", description="Menu of the Mensa at Campus Essen or Duisburg")
    @app_commands.describe(campus="Which Mensa", day="Which day")
    @app_commands.choices(campus=CAMPUS_CHOICES, day=DAY_CHOICES)
    async def mensa_cmd(
        self,
        interaction: discord.Interaction,
        campus: app_commands.Choice[str],
        day: app_commands.Choice[int] | None = None,
    ) -> None:
        site = mensa.CAMPUSES[campus.value]
        target = (datetime.now(BERLIN) + timedelta(days=day.value if day else 0)).date()
        await interaction.response.defer(thinking=True)
        try:
            meals = await mensa.fetch_menu(self.bot.http_session, site, target)
        except Exception as exc:
            log.warning("Loading menu for %s failed: %r", campus.value, exc)
            await interaction.followup.send(
                f"Couldn't load the menu ({exc.__class__.__name__}). See {site.url}"
            )
            return

        title = f"{site.label} – {target.strftime('%d.%m.%Y')}"
        if not meals:
            await interaction.followup.send(
                f"**{title}**\nNo menu published for this day (closed or not yet available).\n{site.url}"
            )
            return

        by_category: dict[str, list[mensa.Meal]] = defaultdict(list)
        for meal in meals:
            by_category[meal.category].append(meal)

        embed = discord.Embed(title=title[:256], url=site.url, color=EMBED_COLOR)
        for category, items in list(by_category.items())[:25]:
            lines = []
            for m in items:
                price = format_price(m.student_price)
                lines.append(f"• {m.name}" + (f" — **{price}**" if price else ""))
            embed.add_field(name=category[:256], value="\n".join(lines)[:1024], inline=False)
        embed.set_footer(text="Student prices · Studierendenwerk Essen-Duisburg")
        await interaction.followup.send(embed=embed)


async def setup(bot: AtlasBot) -> None:
    await bot.add_cog(Mensa(bot))
