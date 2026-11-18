# claude-usage-tray

Two small rings in your system tray / menu bar showing your **Claude Code usage limits**:

- **Session** – the rolling 5-hour window
- **Weekly** – the 7-day window

Hover for the exact percentage and time until reset. Right-click for details.

| Colour | Meaning |
|---|---|
| Green | under 70% |
| Yellow | 70–89% |
| Red | 90% and up |
| Grey | no data yet, or the window has reset since the last update |

> Unofficial community tool. Not affiliated with or endorsed by Anthropic.
> Requires a Claude Pro/Max subscription (rate limits are only reported for subscribers).

## Install

Needs Python 3.10+ and [pipx](https://pipx.pypa.io/).

```sh
pipx install git+https://github.com/chameen9/claude-usage-tray
claude-usage-tray install
```

`install` does three things:

1. **Wraps your status line.** Claude Code sends usage data to whatever `statusLine` command
   you configure. The installer points `statusLine` at this tool, which saves the usage data
   and then runs your original status line command with the same input, so your status line looks
   exactly as before. Your `settings.json` is backed up first (`settings.json.usage-tray-backup-*`).
2. **Starts the tray at login** (Windows: `HKCU\...\Run` registry value; macOS: a LaunchAgent;
   Linux: an XDG autostart `.desktop` file).
3. **Starts the tray now.**

The rings fill in the next time Claude Code renders its status line.

### Platform notes

- **Windows** – two icons. Windows 11 hides new tray icons under the `^` arrow; drag them onto
  the taskbar, or enable them in *Settings → Personalization → Taskbar → Other system tray icons*.
- **macOS** – one menu-bar icon with two rings: outer = weekly, inner = session.
- **Linux** – one icon with two rings. On GNOME you need the *AppIndicator and KStatusNotifierItem
  Support* extension. For the best result install the indicator libraries and give pipx access
  to them:
  ```sh
  sudo apt install python3-gi gir1.2-ayatanaappindicator3-0.1
  pipx install --system-site-packages git+https://github.com/chameen9/claude-usage-tray
  ```

Change the layout with `claude-usage-tray config --layout split|combined|auto`, then restart the tray.

## Live updates (optional, beta)

By default the numbers only update while you use Claude Code. While it's closed the reset
countdowns keep ticking, and a window drops to 0% (grey) once its reset time passes.

To keep updating while Claude Code is closed:

```sh
claude-usage-tray config --live on     # or tick "Live updates (beta)" in the tray menu
claude-usage-tray poll                 # one-off check that it works
```

What this does:

- Every 5 minutes (`--interval` to change, minimum 60s), the tray reads the login token Claude Code
  already saved (`~/.claude/.credentials.json`, or the macOS Keychain) and asks
  `api.anthropic.com/api/oauth/usage` for your usage. The token is sent **only** to `api.anthropic.com`.
- It **never refreshes** the token. When the token expires, live updates pause until Claude Code
  refreshes it the next time you use it.
- That endpoint is **undocumented** and may change or stop working at any time. If it does,
  the tray falls back to status-line data.

## Commands

```
claude-usage-tray                 start the tray (same as `run`)
claude-usage-tray install         wrap statusLine, enable autostart, start tray
                                  [--no-autostart] [--no-start]
claude-usage-tray uninstall       restore your original statusLine, remove autostart
claude-usage-tray status          print the latest numbers
claude-usage-tray config          show settings; --live on|off --layout ... --interval N
claude-usage-tray poll            one live poll now
```

## Uninstall

```sh
claude-usage-tray uninstall       # then choose Quit in the tray menu
pipx uninstall claude-usage-tray
```

Files this tool creates in `~/.claude` (or `$CLAUDE_CONFIG_DIR`): `usage-limits.json`,
`usage-tray.json`, `usage-tray.lock`, and the settings backups.

## Known limitations

- On Windows the original status line command runs through Git Bash, the same shell Claude Code uses.
- If you change your `statusLine` later, run `claude-usage-tray uninstall`, make your change, then
  `claude-usage-tray install` again.
- The tray runs on Windows, macOS and Linux, but has so far been tried by hand only on Windows 11.
  Automated tests run on all three. Reports from macOS and Linux are welcome.

## Development

```sh
python -m venv .venv
.venv/bin/pip install -e ".[dev]"     # Windows: .venv\Scripts\pip
.venv/bin/pytest
```

## License

MIT
