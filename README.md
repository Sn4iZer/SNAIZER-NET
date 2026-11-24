---
title: SNAIZER//NET
emoji: 🕶️
colorFrom: pink
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
short_description: Cyberpunk terminal portfolio of Mohammed Tchichi (Sn4iZer)
---

# SNAIZER//NET

```
▄▀▀▀▀ █▄  █ ▄▀▀▀▄ ▀▀█▀▀ ▀▀▀█▀ █▀▀▀▀ █▀▀▀▄    ▄▀    ▄▀ █▄  █ █▀▀▀▀ ▀▀█▀▀
 ▀▀▀▄ █ ▀▄█ █▀▀▀█   █    ▄▀   █▀▀▀  █▀▀█   ▄▀    ▄▀   █ ▀▄█ █▀▀▀    █
▀▀▀▀  ▀   ▀ ▀   ▀ ▀▀▀▀▀ ▀▀▀▀▀ ▀▀▀▀▀ ▀   ▀ ▀     ▀     ▀   ▀ ▀▀▀▀▀   ▀
```

A cyberpunk terminal portfolio for **Mohammed Tchichi (Sn4iZer)**, 1st-year
Master's student in AI & IoT. A single [Textual](https://textual.textualize.io)
app, served three ways:

| Mode  | How                                   |
|-------|---------------------------------------|
| Local | `python -m snaizer_net`               |
| Web   | `python servers/web.py` → browser     |
| SSH   | `ssh -p 2222 guest@<host>`            |

Every visit opens with a boot sequence and a **fake** "neural-link" login
(any credentials work, it's theater) before the portfolio unlocks.

---

## Contents

- [Features](#features)
- [Quick start (local)](#quick-start-local)
- [Web mode](#web-mode)
- [SSH mode](#ssh-mode)
- [Editing your content](#editing-your-content)
- [Deploy to a VPS (Ubuntu, ~15 minutes)](#deploy-to-a-vps-ubuntu-15-minutes)
- [Port 22 trade-off: moving your real SSH](#port-22-trade-off-moving-your-real-ssh)
- [Deploy without Docker (systemd)](#deploy-without-docker-systemd)
- [Configuration reference](#configuration-reference)
- [Security model](#security-model)
- [Development](#development)
- [Project layout](#project-layout)
- [Known limitations](#known-limitations)

## Features

- **Boot sequence**: BIOS-style log with a spinner on the line being
  loaded, glitching logo, progress bar. Any key skips.
- **Fake login**: masked passphrase, red shake on empty fields, a fake trace
  joke on `1234`, a hint for `guest`/`guest`, and an **ADMIN** badge plus a
  secret `[0] BLACK-ICE` tab for `snaizer` or `admin`.
- **Main HUD**: ticking status bar (fake CPU/NET, real uptime and clock),
  sidebar navigation that collapses into a tab strip under 100 columns,
  context-aware key hints, a neon scanline sweep on every section change and
  a slow neon "pulse" on the active item.
- **Sections** (each headed by its path, e.g. `~/experience`, and one plain
  sentence on what it is):
  - profile: the handle in block type, typewriter bio, a "now" readout
    (studying, last role, top award), counters that count up, and a clearly
    labelled **simulated IoT telemetry** panel with live sparklines;
  - education and experience as a ledger: dates in their own column;
  - animated skill bars;
  - project "dossiers" (Enter expands, `f` filters by tag);
  - awards (the frame encodes the placing);
  - contact, with the phone number **sealed** until you press `d` (or run
    `decrypt phone`), which decodes it character by character;
  - a **timeline** that merges degrees, jobs, projects and awards into one
    animated career log;
  - a sandboxed **fake shell**.
- **The classified file**: a flickering `TOP SECRET // EYES ONLY` stamp on the
  profile (click it, or Tab then Enter). Opening it trips a red alarm
  (three slow flashes), a glitching `INTRUSION DETECTED` breach, then a
  fictional surveillance AI, OVERWATCH-7, "compiles" the subject like a
  one-minute video: a targeting reticle locks onto each block of real data
  (identity, education, skills, projects, awards, experience, contact, where
  the phone number decodes on screen). It ends with an urgent "this file
  should not have been opened... contact the subject for an interview" card,
  a countdown, and `CONNECTION TERMINATED`. Space pauses, ←/→ skip, Esc
  leaves. Afterwards the stamp is gone for the rest of the visit; the shell
  command `classified` replays it. The framing lives in `lore.yaml`
  (`overwatch:`); every fact comes from `profile.yaml`.
- **Command palette** (`/` or `Ctrl+P`): fuzzy-search sections, dossiers, tag
  filters, themes and actions (including turning animations on/off).
- **Fake shell commands**: `help`, `whoami`, `ls`, `cd`, `pwd`, `cat`,
  `echo`, `grep`, `projects`, `open <n>`, `timeline`, `skills`, `contact`,
  `decrypt phone`, `classified`,
  `neofetch`, `fortune`, `hack`, `history`, `matrix`, `theme`, `clear`,
  `exit` (and try `sudo`). Output streams in line by line.
- **Themes**: `neon-night` (default), `synthwave`, `toxic-green`,
  `red-alert`, plus `neon-16` for 16-color terminals (picked automatically).
- **Matrix rain** with `m` (or `matrix` in the shell).
- **Accessible**: works at 80x24, every animation is ≤ 12 fps, `--no-anim`
  (or the palette) turns them all off, and below 80x24 you get a friendly
  "enlarge" notice.

**Keys:** `0-9` jump · `/` search · `↑↓`/`j k`/`Tab` move · `Enter` open
dossier · `f`/`F` filter projects · `PgUp/PgDn` scroll · `m` rain · `?` help
· `q` / `Ctrl+C` quit · `Esc` leaves the terminal prompt. The mouse works
everywhere.

## Quick start (local)

Requires Python 3.11+.

```bash
# with uv (recommended)
uv sync --extra dev
uv run python -m snaizer_net

# or with pip
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m snaizer_net
```

Useful flags:

```bash
python -m snaizer_net --skip-intro     # straight to the HUD
python -m snaizer_net --no-anim        # no animations
python -m snaizer_net --colors 16      # force the 16-color palette
python -m snaizer_net --content-dir /path/to/content
```

## Web mode

```bash
python servers/web.py                  # http://localhost:8000
HOST=127.0.0.1 PORT=9000 python servers/web.py
```

Each browser tab gets its own app process (via `textual-serve`). Keyboard
and mouse both work. Web mode sets `SNAIZER_MODE=web`, which adds
"Open GitHub" and "Write an email" buttons to the contact section. Behind a
reverse proxy the public `wss://` URL is worked out from
`X-Forwarded-Proto/Host`. Set `PUBLIC_URL` to pin it.

The page uses [Martian Mono](https://github.com/evilmartians/mono) (OFL,
served locally from `servers/web_static/fonts`, no Google Fonts request). On
small screens it picks a font size that fits the 80x24 layout; add
`?fontsize=14` to the URL to override. The connecting and disconnected
screens show the `ssh` command too (set `SSH_PUBLIC_PORT` if you moved the
gateway to port 22).

## SSH mode

The SSH gateway needs **Linux or macOS** because it allocates real PTYs. On
Windows, run it in Docker or WSL.

```bash
python servers/ssh_server.py           # listens on 0.0.0.0:2222
ssh -p 2222 guest@localhost            # any username, no password
```

The first run creates a host key at `./data/ssh_host_key` (mode 0600), so the
fingerprint never changes after that. Every session runs a fresh, isolated
`python -m snaizer_net --mode ssh` process. Window resizes are passed through
live, and pressing `q` ends the session cleanly. Logs are JSON lines on stdout:

```json
{"ts":"...","level":"info","event":"session_start","ip":"203.0.113.7","session":"9f2c1a0b","term":"xterm-256color"}
```

## Editing your content

**All real portfolio data lives in [`content/profile.yaml`](content/profile.yaml).**
No widget hardcodes any of it. Edit the YAML and restart. There is no build step.

- `identity`: name, handle, title, location, bio.
- `contact`: email, GitHub handle, location, and an optional `phone_sealed`.
- `highlights`: extra headline stats on the profile screen (projects and
  awards are counted automatically).

### The sealed phone number

The phone number never sits in plain text. Seal it and paste the token into
`contact.phone_sealed`:

```bash
python -m snaizer_net.cipher "+212 600 000 000"
# snz1:...
```

Visitors see block noise until they press `d` in the contact section (or run
`decrypt phone` in the terminal). Be clear about what this is: **obfuscation,
not encryption**. Anyone with this code can decode the token. It keeps the
number out of your repository and away from scrapers that grep for digits;
the deliberate "decrypt" action is the real gate. Remove the field to hide
the number entirely.
- `education`, `skills` (with a stylized 0-100 `level`), `languages` (the
  `level` text is shown as-is, `bar` only drives the visual), `projects`
  (`slug` must be kebab-case and unique), `awards`, `experience`.
- Periods accept `2023`, `2023-2025`, `2023-present` or month ranges like
  `Jun 2026 - Jul 2026`. The timeline sorts on them automatically.

Fictional flavor text (boot log lines, shell jokes, the BLACK-ICE lore) lives
separately in [`content/lore.yaml`](content/lore.yaml).

The files are checked at startup. A mistake gives a precise error and exit
code 2 instead of a crash:

```
SNAIZER//NET: content error
content/profile.yaml:projects[0].year: 19 is not a valid year
```

In Docker the content is baked into the image, so rebuild after editing:
`docker compose up -d --build`.

## Deploy to a VPS (Ubuntu, ~15 minutes)

Target: Ubuntu 22.04/24.04, 1 vCPU / 1 GB RAM minimum. Every live visitor
gets their own Python process (tens of MB each), so size the box and the
session caps for your traffic.

### 1. DNS (do this first; it needs a few minutes to propagate)

At your DNS provider, create an **A** record (and an **AAAA** record if you have IPv6):

```
snaizer.example.com.   A     203.0.113.10
```

Check it with `dig +short snaizer.example.com`.

### 2. Base system and Docker

```bash
ssh root@203.0.113.10
apt update && apt -y upgrade
adduser deploy && usermod -aG sudo deploy        # if you don't have a user yet
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
su - deploy
```

### 3. Firewall (ufw)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp          # your admin SSH (change if you move it, see below)
sudo ufw allow 80/tcp          # HTTP (ACME challenge + redirect)
sudo ufw allow 443/tcp         # HTTPS
sudo ufw allow 443/udp         # HTTP/3
sudo ufw allow 2222/tcp        # portfolio SSH
sudo ufw enable
sudo ufw status verbose
```

> Docker-published ports go around ufw (Docker writes its own iptables
> rules). The compose file only publishes 80, 443 and the SSH port, and the
> web container is reachable only through Caddy.

### 4. Get the code and configure

Push this folder to a GitHub repo first (the URL below assumes
`Sn4iZer/SNAIZER-NET`), or copy it over with `scp -r snaizer-net deploy@203.0.113.10:`.

```bash
git clone https://github.com/Sn4iZer/SNAIZER-NET.git
cd snaizer-net
cp .env.example .env
nano .env        # set DOMAIN=snaizer.example.com
```

### 5. Launch

```bash
docker compose up -d --build
docker compose ps                  # all three should be "running (healthy)"
docker compose logs -f ssh         # JSON connection logs
```

Caddy fetches a Let's Encrypt certificate on first start (DNS must resolve
to the server and ports 80/443 must be open).

### 6. Verify

```bash
curl -I https://snaizer.example.com          # 200, served by Caddy
ssh -p 2222 guest@snaizer.example.com        # boot → fake login → portfolio
ssh -p 2222 guest@snaizer.example.com ls     # refused (exec is disabled)
```

Updating later: `git pull && docker compose up -d --build`.

## Free web hosting on Hugging Face Spaces (no SSH)

Spaces runs the existing `Dockerfile`, so there is nothing to build by hand.
The YAML block at the top of this README (`sdk: docker`, `app_port: 8000`)
tells Spaces what to do. SSH is not possible there (one HTTP port only).

1. Create a Space at <https://huggingface.co/new-space>: SDK **Docker**,
   template **Blank**, visibility **Public**.
2. In the Space's **Settings → Variables**, add:
   - `PUBLIC_URL` = `https://<user>-<space>.hf.space`
   - `SSH_PUBLIC_PORT` = `0` (hides the `ssh` hint on the page)
   - `WEB_MAX_SESSIONS` = `10` (each visitor is a Python process)
3. Create a token at <https://huggingface.co/settings/tokens> with **write**
   access, then push this repo to the Space:

   ```bash
   git remote add space https://huggingface.co/spaces/<user>/<space>
   git push space main --force   # username: your HF user, password: the token
   ```

4. Watch the **Logs** tab until the build finishes, then open
   `https://<user>-<space>.hf.space`.

Free Spaces may sleep when idle and wake on the next visit. To update, push
to `space` again.

## Port 22 trade-off: moving your real SSH

Visitors would love plain `ssh guest@snaizer.example.com`, but port 22 is
almost certainly your **own** admin `sshd`. Two options:

| Option | Visitor command | Your admin login |
|---|---|---|
| **Keep 2222** (default, safest) | `ssh -p 2222 guest@domain` | unchanged, port 22 |
| **Portfolio on 22** | `ssh guest@domain` | moved, e.g. `ssh -p 2200 deploy@domain` |

To put the portfolio on 22, **move your real sshd first** (keep your current
session open until the new port works):

```bash
# 1. open the new admin port
sudo ufw allow 2200/tcp

# 2. change sshd's port
sudo sed -i 's/^#\?Port .*/Port 2200/' /etc/ssh/sshd_config
grep ^Port /etc/ssh/sshd_config            # → Port 2200

# 3. restart sshd
#    Ubuntu 24.04 (socket-activated):
sudo systemctl daemon-reload && sudo systemctl restart ssh.socket
#    Ubuntu 22.04:
sudo systemctl restart ssh

# 4. from a NEW local terminal, confirm you can still get in:
ssh -p 2200 deploy@snaizer.example.com

# 5. hand port 22 to the portfolio
sudo ufw delete allow 22/tcp && sudo ufw allow 22/tcp   # now for the portfolio
echo "SSH_PUBLIC_PORT=22" >> .env
docker compose up -d
```

Tip: add `Host snaizer-admin / HostName snaizer.example.com / Port 2200` to
your local `~/.ssh/config` so you don't forget the new port.

## Deploy without Docker (systemd)

```bash
sudo useradd --system --no-create-home --home-dir /opt/snaizer-net --shell /usr/sbin/nologin snaizer
sudo git clone https://github.com/Sn4iZer/SNAIZER-NET.git /opt/snaizer-net
sudo chown -R snaizer:snaizer /opt/snaizer-net
cd /opt/snaizer-net
sudo -u snaizer python3 -m venv .venv
sudo -u snaizer .venv/bin/pip install -r requirements.txt
sudo -u snaizer mkdir -p data
sudo cp deploy/snaizer.service /etc/systemd/system/snaizer-web.service
sudo cp deploy/snaizer-ssh.service /etc/systemd/system/snaizer-ssh.service
sudo systemctl daemon-reload
sudo systemctl enable --now snaizer-web snaizer-ssh
```

Then install Caddy (`sudo apt install caddy`) and use
`reverse_proxy 127.0.0.1:8000` in `/etc/caddy/Caddyfile`.

## Configuration reference

| Variable | Default | Used by | Meaning |
|---|---|---|---|
| `SNAIZER_MODE` | `local` | app | `local` / `web` / `ssh` (set for you by the servers) |
| `SNAIZER_NO_ANIM` | unset | app | `1` disables animations |
| `SNAIZER_SKIP_INTRO` | unset | app | `1` skips boot + login |
| `SNAIZER_COLORS` | `auto` | app | `auto` / `16` / `truecolor` |
| `SNAIZER_CONTENT_DIR` | `./content` | app | where `profile.yaml` + `lore.yaml` live |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | web | bind address |
| `PUBLIC_URL` | derived | web | public base URL, e.g. `https://snaizer.example.com` |
| `WEB_MAX_SESSIONS` | `50` | web | concurrent browser sessions (503 beyond) |
| `SSH_HOST` / `SSH_PORT` | `0.0.0.0` / `2222` | ssh | bind address |
| `SSH_HOST_KEY` | `./data/ssh_host_key` | ssh | persistent host key |
| `SSH_MAX_SESSIONS` | `50` | ssh | global concurrent sessions |
| `SSH_MAX_PER_IP` | `5` | ssh | concurrent sessions per IP |
| `SSH_IDLE_TIMEOUT` | `900` | ssh | seconds without input before disconnect |
| `SSH_MAX_SESSION_SECONDS` | `3600` | ssh | hard session length cap |
| `SSH_RATE_BURST` / `SSH_RATE_PER_MINUTE` | `10` / `20` | ssh | new-connection token bucket per IP |
| `DOMAIN` | `localhost` | caddy | site address for automatic HTTPS |
| `SSH_PUBLIC_PORT` | `2222` | compose | host port mapped to the SSH gateway |

## Security model

- **The login is fake.** It never checks real secrets, files or accounts.
  The ADMIN badge only unlocks a lore tab.
- **The fake shell is a lookup table.** Its input is tokenized and matched
  against a dict of Python methods that read an in-memory "filesystem" built
  from the YAML. There is no `subprocess`, `eval`/`exec`, `open` or `os`
  import. A test scans the shell's source to enforce this, and another
  replays inputs like `rm -rf /`, `$(...)`, `;`, backticks and path
  traversal with tripwires on every execution primitive.
- **The SSH gateway:**
  - only offers PTY + shell, and the "shell" is the portfolio app;
  - refuses `exec`, every subsystem (SFTP), SCP, local/remote/UNIX
    forwarding, tun/tap, agent and X11 forwarding;
  - gives each session its own process with a minimal environment, so
    nothing the client sends leaks into it;
  - enforces global and per-IP session caps, per-IP connection rate limits,
    an idle timeout and a maximum session length;
  - logs JSON without usernames, keystrokes or commands.
- **Containers** run as UID 10001 with a read-only root filesystem,
  `no-new-privileges`, all capabilities dropped, and memory/PID limits.
- **Visitor input is always escaped** before rendering, so typed text can't
  inject Textual markup.

## Development

```bash
pytest                 # content, login logic, shell + sandbox, limits, SSH policy, Pilot UI
ruff check .
black --check .
```

The SSH tests run a real asyncssh server on localhost. They cover exec,
SFTP and forwarding rejection, rate limiting and per-IP caps. The PTY
round-trip test (client window size reaches the app, clean exit) runs on
Linux/macOS only.

## Project layout

```
snaizer-net/
├── content/               profile.yaml (real data) · lore.yaml (fiction)
├── snaizer_net/
│   ├── __main__.py        entry point, content error handling
│   ├── app.py             App, screen routing, theme + size handling
│   ├── theme.tcss         Textual CSS using $neon-* variables
│   ├── themes.py          palettes → Textual themes
│   ├── content.py         YAML loading + validation
│   ├── auth_theater.py    pure fake-login rules
│   ├── timeline.py        merged, sorted career log + period labels
│   ├── cipher.py          seals/unseals the phone number (obfuscation)
│   ├── overwatch.py       the classified walkthrough as data (segments, timing)
│   ├── palette.py         command palette provider
│   ├── config.py · markup.py · navigation.py
│   ├── screens/           boot · login · main · overwatch · overlays (help/matrix/too-small)
│   ├── sections/          one pane per navigation entry
│   ├── shell/             sandboxed fake shell (commands, vfs, tokenizer)
│   ├── widgets/           matrix_rain · glitch_label · skill_bar · typewriter
│   │                      fake_shell · project_card · hex_stream · nav · status_bar
│   │                      counter · sensor_panel · scanline · ledger · decrypt_text
│   │                      classified
│   └── assets/ascii.py    block font + ASCII art
├── servers/               web.py · ssh_server.py · pty_bridge.py · limits.py · healthcheck.py
│                          web_templates/ (page) · web_static/fonts/ (Martian Mono, OFL)
├── tests/
├── Dockerfile · docker-compose.yml · .env.example
└── deploy/                Caddyfile · snaizer.service · snaizer-ssh.service
```

## Known limitations

- The SSH gateway needs a POSIX PTY, so on Windows run it in Docker or WSL.
- `pip install .` installs the package but not `content/`. Run from the
  source tree, or point `SNAIZER_CONTENT_DIR` at your content.
- "Matrix rain mode" is a full-screen overlay. Terminals can't layer text
  behind other text, so it isn't a literal background.
- Fake CPU/NET readings and the IoT telemetry panel are decorative random
  data, labelled as such in the UI. Uptime and clock are real.
