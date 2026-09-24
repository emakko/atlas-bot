# atlas-bot

Atlas is a Discord bot for students at the **Universität Duisburg-Essen (UDE)**,
with a focus on **Software Engineering / Informatik**. It posts news from the SE
groups, the Fakultät für Informatik and the central UDE feeds into your Discord
channels, shows Mensa menus, and keeps the important study links close at hand.

## Features

| Command | What it does |
| --- | --- |
| `/news sources` | List all configured news sources, grouped (Software Engineering, Informatik, UDE) |
| `/news latest <source> [count]` | Show the newest items of a source right now |
| `/news subscribe <source> [channel] [role]` | Auto-post new items into a channel, optionally pinging a role *(Manage Server)* |
| `/news unsubscribe <source> [channel]` | Stop auto-posting *(Manage Server)* |
| `/news subscriptions` | Show this server's subscriptions |
| `/mensa <Essen\|Duisburg>` | Today's menu of the Mensa at Campus Essen or Duisburg with student prices and diet tags, plus links to the weekly PDF plans (from [stw-edu.de](https://www.stw-edu.de/gastronomie/speisen/)) |
| `/links` | Quick links: paluno, SSE, SE chair, Informatik, Moodle, HISinOne, ZIM, UB, … |
| `/po <Neu – PO 2026\|Alt – PO 2023>` | Prüfungsordnung / Modulhandbuch for the B.Sc. Software Engineering, links configured in `sources.yaml` |

### News sources

Configured in [`sources.yaml`](sources.yaml):

- **Software Engineering**
  - `paluno`: paluno, the Ruhr Institute for Software Technology
  - `sse`: Software Systems Engineering
  - `se-chair`: Lehrstuhl für Software Engineering
  - `softec`: softec (RIS)
  - `ude-se`, `ude-studium-se`: the central UDE feeds, filtered by SE/Informatik keywords
- **Informatik**
  - `informatik`: news of the Fakultät für Informatik
- **UDE**
  - `ude-studium`, `ude-aktuell`, `ude-forschung`, `ude-presse`, `ude-press-en`: central [UDE newsfeeds](https://www.uni-due.de/de/presse/feeds.php)

Most faculty and chair websites don't publish RSS. For those, Atlas uses
`type: html` and watches the news overview page for **new links**. It keeps only
links whose URL matches `link_pattern` and whose text is at least `min_title_len`
characters, which filters out navigation links. When a source is first
subscribed, Atlas only records what is already there. After that it posts at most
5 new items per source per check, so a page redesign can't flood a channel.

To add a source, add an entry to `sources.yaml` and restart the bot. `/news latest`
is a quick way to check that a new source parses the way you expect.

## Setup

1. Create an application at <https://discord.com/developers/applications>, add a
   **Bot**, and copy its token.
2. Invite it with the scopes `bot` and `applications.commands`. It needs the
   permissions *Send Messages*, *Embed Links* and, if you want role pings for roles
   that aren't mentionable, *Mention Everyone*.
3. Configure and run:

```bash
cp .env.example .env          # put DISCORD_TOKEN in here
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m atlas
```

Set `ATLAS_DEV_GUILD_ID` to your server's ID while developing so slash commands
show up immediately. Global sync can take up to an hour.

### Docker

```bash
docker build -t atlas-bot .
docker run -d --name atlas --env-file .env -v atlas-data:/app/data atlas-bot
```

### Configuration

| Variable | Default | |
| --- | --- | --- |
| `DISCORD_TOKEN` | – | required |
| `ATLAS_DEV_GUILD_ID` | – | sync commands to one server instantly |
| `ATLAS_POLL_MINUTES` | `15` | how often subscribed sources are checked |
| `ATLAS_DB_PATH` | `data/atlas.db` | SQLite file for subscriptions and seen items |
| `ATLAS_SOURCES_FILE` | `sources.yaml` | news sources, links and PO documents |

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

Layout:

- `atlas/feeds.py`: fetches sources and parses RSS and HTML pages
- `atlas/poller.py`: finds new items and fans them out to subscribed channels
- `atlas/storage.py`: SQLite storage for subscriptions and seen items
- `atlas/mensa.py`: menu parser for stw-edu.de (Mensa Campus Essen and Duisburg)
- `atlas/cogs/`: the Discord slash commands (`news`, `mensa`, `links`)
