# Contributing

Thanks for helping. This project aims to work on any desktop with the tools
that are already installed, and to be tested before it is changed.

## Ground rules

1. **Keep the LXQt scripts unchanged.** `install-lxqt.sh`, `dock-lxqt.sh` and
   `restore-lxqt.sh` must match the tested version byte for byte. A test checks this.
   Put shared logic in `lib/` and call it from the KDE side, or add a new file.
2. **Work with what is installed.** Do not require a package unless the feature
   cannot work without it. If an optional tool is missing, skip that feature, say so
   in one clear line, and keep going.
3. **Never run as root.** Scripts ask for `sudo` only where a package must be installed,
   and only when you pass `--install-deps`.
4. **Back up before changing a file.** Use the existing backup helpers. Every install
   must be reversible with `restore.sh`.
5. **Do not commit your own settings.** `config/theme.json` and backup folders stay
   on your machine.
6. **Do not add assets you have no right to share.** Fonts, icons and wallpapers from
   other projects must have a licence that allows it, and must be listed in
   `THIRD_PARTY.md`.
7. **Write plainly.** Comments and messages should describe what the user sees.
   Avoid internal project shorthand in user-facing text.

## Speed and quality targets

These are requirements, not wishes. A change that breaks one needs a good reason.

- **Installing again must be quick and quiet.** A repeat install with nothing to change
  should finish in a few seconds and must not restart the Plasma panel process.
- **Open the launcher fast.** It should be ready in well under half a second, and answer a
  keystroke in a few milliseconds. Slow work (files, network) goes in the background.
- **Do each check once.** Remember the result of anything that runs another program
  (for example `fc-list` or `kscreen-doctor`) instead of running it again.
- **Do not leave the desktop broken.** Anything that stops a service must start it again,
  even when something fails, and must handle systemd's start-rate limit.
- **Measure before you optimise.** Say what you measured and the before and after numbers.
- **Keep it simple.** Use the standard library, avoid copying code, and keep functions short
  enough to read in one screen.

## Setting up

```bash
git clone https://github.com/prashantjain25/darwin-theme.git
cd darwin-theme
python3 -m unittest discover -s tests -v
```

Run the tests before and after your change. They must pass.

## Tests that need a display

Some tests open the real dock and launcher. They are off by default because they
need a running desktop and a few extra tools:

```bash
DARWIN_QML_TEST=1 python3 -m unittest tests.test_dock_component -v
```

They need PyQt6, `ydotool` for the pointer tests and a Wayland session.

## Checking your change on a real desktop

Before you send a change that affects looks, please:

1. Run `./install.sh --dry-run` and read the output.
2. Install it on your own desktop and check the top bar, dock, launcher and Alt+Tab
   in both light and dark mode, if you can.
3. Run `./restore.sh` and check that your desktop goes back to how it was.
4. Say which desktop and version you tested on (for example "Plasma 6.6 on Wayland").

## Style

- Shell scripts: `set -euo pipefail` at the top, quote variables, and run `bash -n`.
- Python: standard library only where possible. No new third-party packages without a
  discussion first.
- QML: run `qmllint` on the files you touch.
- Keep each change small. One fix per pull request is easiest to review.

## Reporting a problem

Open an issue and include:

- Your distribution and version (`lsb_release -a`)
- Your desktop and version (KDE Plasma or LXQt; `plasmashell --version` for KDE)
- Whether you are on Wayland or X11
- What you expected and what happened
- The output of `./install.sh --dry-run`, if the problem happens during install

Remove any personal file names or paths from the output before you post it.

## For maintainers: keeping the project easy to find

- Keep the README title and first paragraph plain: what it is, which desktops it supports,
  and the main features. People and search tools read those first.
- Keep `llms.txt`, `CITATION.cff` and the README in step when features or commands change.
- Repository description and topics are set on GitHub (not in a file). After logging in with
  `gh auth login`, run:

  ```bash
  gh repo edit prashantjain25/darwin-theme \
    --description "Darwin: a dark, translucent Mac-like desktop theme for KDE Plasma 6 and LXQt. Dock with magnification, Spotlight-style launcher, Alt+Tab, WhiteSur icons" \
    --add-topic desktop-theme --add-topic kde-plasma --add-topic plasma-6 --add-topic lxqt --add-topic lubuntu \
    --add-topic dock --add-topic spotlight --add-topic whitesur --add-topic wayland --add-topic linux-theme --add-topic ricing
  ```

## Licence

By contributing, you agree that your work is released under the MIT licence, the
same as the rest of the project. Files derived from GPL or OFL projects keep their
original licence; say so in the file header and in `THIRD_PARTY.md`.
