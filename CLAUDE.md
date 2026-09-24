# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## Project

Atlas is a Discord bot (discord.py 2.x, Python 3.10+) for students at the
Universität Duisburg-Essen. It posts news from RSS feeds and HTML pages, shows
Mensa menus from stw-edu.de, and serves study links. See `README.md` for features
and setup.

- `atlas/__main__.py`: entry point (`python -m atlas`)
- `atlas/bot.py`: `AtlasBot`, loads the cogs and syncs slash commands
- `atlas/cogs/`: slash commands (`news`, `mensa`, `links`)
- `atlas/feeds.py`, `atlas/poller.py`, `atlas/storage.py`, `atlas/mensa.py`: core logic
- `sources.yaml`: news sources and links
- `tests/`: pytest suite (`asyncio_mode = auto`)

## Commands

```bash
pip install -r requirements-dev.txt
pytest                # run all tests
python -m atlas       # run the bot (needs DISCORD_TOKEN in .env)
```

Never commit `.env` or a real Discord token.

## Branches

`prod` is the default branch. Create every branch from an up-to-date `prod` and
open pull requests against `prod`. Don't push directly to `prod`.

Name branches `<type>/<short-description>`:

| Prefix | Use for | Example |
| --- | --- | --- |
| `feature/` | new functionality | `feature/mensa-weekly-menu` |
| `fix/` | bug fixes | `fix/rss-duplicate-posts` |
| `docs/` | documentation only | `docs/setup-guide` |
| `refactor/` | restructuring without behavior changes | `refactor/poller-cleanup` |
| `test/` | adding or fixing tests | `test/storage-edge-cases` |
| `chore/` | dependencies, config, CI, tooling | `chore/bump-discord-py` |

Rules:

- Use lowercase kebab-case: `feature/news-role-pings`, not `Feature/NewsRolePings`.
- Keep the description short (2–5 words) and descriptive.
- If there is an issue, you may add its number: `fix/42-mensa-timeout`.
- One topic per branch. Delete the branch after it is merged.
- This applies to branches created by Claude Code too. Don't use tool-generated
  names like `claude/<random-name>`; pick the matching prefix above instead.

## Before opening a pull request

- `pytest` passes.
- New sources in `sources.yaml` are checked with `/news latest <source>`.
- `README.md` is updated when commands, configuration or sources change.
