# Action Logger Cooperator

This repo contains some Python scripts that are helpful for use with the Action Logger RuneLite plugin.

## Configuring

You can modify the `config.toml` file to change the behaviour of the commands.
I will be keeping `config.toml` updated with my own preferences. I might make it load a `config.local.toml` too after `config.toml` and use values from that if they exist.

## Watching for new Action Logger lines

```bash
uv run tail.py
```

## Updating the gamevals

```bash
uv run update-gamevals.py
```

You can set the `RUNELITE_DIR` environment variable to override where to find the [RuneLite](https://github.com/runelite/runelite) repository:

```bash
RUNELITE_DIR=/path/to/runelite uv run update-gamevals.py
```
