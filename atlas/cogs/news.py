from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from atlas.config import Source
from atlas.feeds import NewsItem, fetch_items
from atlas.poller import Poller
from atlas.storage import Subscription

if TYPE_CHECKING:
    from atlas.bot import AtlasBot

log = logging.getLogger(__name__)

EMBED_COLOR = discord.Color.from_rgb(0, 76, 147)  # UDE blue


def item_embed(source: Source, item: NewsItem) -> discord.Embed:
    embed = discord.Embed(
        title=item.title[:256],
        url=item.link or None,
        description=item.summary or None,
        color=EMBED_COLOR,
        timestamp=item.published,
    )
    embed.set_footer(text=source.name[:2048])
    return embed


class News(commands.Cog):
    news = app_commands.Group(name="news", description="News from UDE, Informatik and Software Engineering")

    def __init__(self, bot: AtlasBot) -> None:
        self.bot = bot
        self.sources = bot.settings.catalog.sources
        self.poller = Poller(bot.storage, self.sources, self._fetch, self._send)
        self.poll_loop.change_interval(minutes=bot.settings.poll_minutes)
        self.poll_loop.start()

    async def cog_unload(self) -> None:
        self.poll_loop.cancel()

    # --- background polling ---------------------------------------------

    async def _fetch(self, source: Source) -> list[NewsItem]:
        return await fetch_items(self.bot.http_session, source)

    async def _send(self, sub: Subscription, source: Source, item: NewsItem) -> None:
        channel = self.bot.get_channel(sub.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(sub.channel_id)
            except discord.NotFound:
                log.info("Channel %s is gone, removing its subscriptions", sub.channel_id)
                await self.bot.storage.remove_channel(sub.channel_id)
                return
        if not isinstance(channel, discord.abc.Messageable):
            return
        content = f"<@&{sub.role_id}>" if sub.role_id else None
        await channel.send(
            content=content,
            embed=item_embed(source, item),
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

    @tasks.loop(minutes=15)
    async def poll_loop(self) -> None:
        posted = await self.poller.poll_all()
        if posted:
            log.info("Posted %d news items", posted)

    @poll_loop.before_loop
    async def _before_poll(self) -> None:
        await self.bot.wait_until_ready()

    # --- helpers ----------------------------------------------------------

    async def source_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        needle = current.casefold()
        choices = [
            app_commands.Choice(name=f"{s.group}: {s.name}"[:100], value=s.key)
            for s in self.sources.values()
            if needle in s.key.casefold() or needle in s.name.casefold() or needle in s.group.casefold()
        ]
        return choices[:25]

    def _resolve(self, key: str) -> Source | None:
        return self.sources.get(key)

    # --- commands ---------------------------------------------------------

    @news.command(name="sources", description="List the news sources Atlas knows about")
    async def sources_cmd(self, interaction: discord.Interaction) -> None:
        grouped: dict[str, list[Source]] = defaultdict(list)
        for s in self.sources.values():
            grouped[s.group].append(s)

        embed = discord.Embed(title="News sources", color=EMBED_COLOR)
        for group, sources in grouped.items():
            lines = []
            for s in sources:
                line = f"`{s.key}` – [{s.name}]({s.url})"
                if s.keywords:
                    line += " *(filtered)*"
                lines.append(line)
            embed.add_field(name=group, value="\n".join(lines)[:1024], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @news.command(name="latest", description="Show the latest items from a source")
    @app_commands.describe(source="Which source", count="How many items (1-10)")
    @app_commands.autocomplete(source=source_autocomplete)
    async def latest(
        self,
        interaction: discord.Interaction,
        source: str,
        count: app_commands.Range[int, 1, 10] = 5,
    ) -> None:
        src = self._resolve(source)
        if src is None:
            await interaction.response.send_message(f"Unknown source `{source}`.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        try:
            items = await self._fetch(src)
        except Exception as exc:
            log.warning("Fetching %s failed: %s", src.key, exc)
            await interaction.followup.send(f"Couldn't load **{src.name}** right now ({exc.__class__.__name__}).")
            return
        if not items:
            await interaction.followup.send(f"No items found for **{src.name}**.")
            return
        embeds = [item_embed(src, item) for item in items[:count]]
        await interaction.followup.send(embeds=embeds)

    @news.command(name="subscribe", description="Post new items from a source into a channel")
    @app_commands.describe(
        source="Which source",
        channel="Target channel (default: this channel)",
        role="Role to ping for new items (optional)",
    )
    @app_commands.autocomplete(source=source_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def subscribe(
        self,
        interaction: discord.Interaction,
        source: str,
        channel: discord.TextChannel | None = None,
        role: discord.Role | None = None,
    ) -> None:
        src = self._resolve(source)
        if src is None:
            await interaction.response.send_message(f"Unknown source `{source}`.", ephemeral=True)
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Please pick a text channel.", ephemeral=True)
            return
        perms = target.permissions_for(target.guild.me)
        if not (perms.send_messages and perms.embed_links):
            await interaction.response.send_message(
                f"I need *Send Messages* and *Embed Links* in {target.mention}.", ephemeral=True
            )
            return

        created = await self.bot.storage.subscribe(
            target.guild.id, target.id, src.key, role.id if role else None
        )
        verb = "Subscribed" if created else "Updated subscription of"
        ping = f", pinging {role.mention}" if role else ""
        await interaction.response.send_message(
            f"{verb} {target.mention} to **{src.name}**{ping}. New items are checked every "
            f"{self.bot.settings.poll_minutes:g} minutes.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @news.command(name="unsubscribe", description="Stop posting a source into a channel")
    @app_commands.describe(source="Which source", channel="Channel (default: this channel)")
    @app_commands.autocomplete(source=source_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def unsubscribe(
        self,
        interaction: discord.Interaction,
        source: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        target = channel or interaction.channel
        if target is None:
            await interaction.response.send_message("Please pick a channel.", ephemeral=True)
            return
        removed = await self.bot.storage.unsubscribe(target.id, source)
        msg = "Unsubscribed." if removed else "That channel wasn't subscribed to this source."
        await interaction.response.send_message(msg, ephemeral=True)

    @news.command(name="subscriptions", description="List news subscriptions on this server")
    @app_commands.guild_only()
    async def subscriptions(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        subs = await self.bot.storage.subscriptions(guild_id=interaction.guild.id)
        if not subs:
            await interaction.response.send_message(
                "No subscriptions yet. Use `/news subscribe` to add one.", ephemeral=True
            )
            return
        lines = []
        for sub in subs:
            src = self.sources.get(sub.source_key)
            name = src.name if src else f"{sub.source_key} (removed)"
            ping = f" → <@&{sub.role_id}>" if sub.role_id else ""
            lines.append(f"<#{sub.channel_id}>: **{name}**{ping}")
        embed = discord.Embed(title="Subscriptions", description="\n".join(lines)[:4096], color=EMBED_COLOR)
        await interaction.response.send_message(
            embed=embed, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot: AtlasBot) -> None:
    await bot.add_cog(News(bot))
