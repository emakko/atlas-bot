from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from atlas import mensa
from atlas.cogs.news import EMBED_COLOR

if TYPE_CHECKING:
    from atlas.bot import AtlasBot

log = logging.getLogger(__name__)

CAMPUS_CHOICES = [app_commands.Choice(name=c.label, value=key) for key, c in mensa.CAMPUSES.items()]


def format_price(value: float | None) -> str:
    return f"{value:.2f} €".replace(".", ",") if value is not None else ""


def meal_line(meal: mensa.Meal) -> str:
    line = f"• {meal.name}"
    price = format_price(meal.student_price)
    if price:
        line += f" — **{price}**"
    if meal.diet:
        line += f"\n  {' · '.join(meal.diet)}"
    return line


def menu_embed(site: mensa.Campus, menu: mensa.Menu) -> discord.Embed:
    title = site.label + (f" – {menu.date_label}" if menu.date_label else "")
    embed = discord.Embed(title=title[:256], url=site.url, color=EMBED_COLOR)

    by_category: dict[str, list[mensa.Meal]] = defaultdict(list)
    for meal in menu.meals:
        by_category[meal.category].append(meal)

    # Leave room for the week-plan field (Discord allows 25 fields per embed).
    for category, meals in list(by_category.items())[:24]:
        value = "\n".join(meal_line(m) for m in meals)
        embed.add_field(name=category[:256], value=value[:1024], inline=False)

    if menu.week_pdfs:
        links = " · ".join(f"[{label}]({url})" for label, url in menu.week_pdfs.items())
        embed.add_field(name="Wochenplan (PDF)", value=links, inline=False)
    embed.set_footer(text="Studierendenpreise · Studierendenwerk Essen-Duisburg")
    return embed


class Mensa(commands.Cog):
    def __init__(self, bot: AtlasBot) -> None:
        self.bot = bot

    @app_commands.command(name="mensa", description="Today's menu of the Mensa at Campus Essen or Duisburg")
    @app_commands.describe(campus="Which Mensa")
    @app_commands.choices(campus=CAMPUS_CHOICES)
    async def mensa_cmd(self, interaction: discord.Interaction, campus: app_commands.Choice[str]) -> None:
        site = mensa.CAMPUSES[campus.value]
        await interaction.response.defer(thinking=True)
        try:
            menu = await mensa.fetch_menu(self.bot.http_session, site)
        except Exception as exc:
            log.warning("Loading menu for %s failed: %r", campus.value, exc)
            await interaction.followup.send(
                f"Couldn't load the menu ({exc.__class__.__name__}). See {site.url}"
            )
            return

        if not menu.meals:
            await interaction.followup.send(
                f"**{site.label}**: no menu published right now (closed or not yet available).\n{site.url}"
            )
            return
        await interaction.followup.send(embed=menu_embed(site, menu))


async def setup(bot: AtlasBot) -> None:
    await bot.add_cog(Mensa(bot))
