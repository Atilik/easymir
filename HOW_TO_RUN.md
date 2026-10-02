# How to use mireasy

You have two buttons. Both live in the mireasy folder, and both work the same
way: **double-click → drag your audio folder into the window → press Return.**

| | `analyze_folder.command` | `run_mireasy.command` |
|---|---|---|
| **What it does** | Analyzes **everything automatically** and saves a CSV. No questions asked. | Opens mireasy **interactively** — explore songs, play them, try single measurements. |
| **When to use it** | You want the results spreadsheet. | You want to look around first. |
| **How long** | Roughly as long as the audio itself (a 10-song session: 30–60 min). Go get a coffee. | Instant to open; each measurement runs when you ask for it. |
| **When it's done** | Prints ✓, tells you where the CSV is, closes itself after 15 s. | You leave by typing `exit()` and pressing Return. |

## Where do my results go?

In the mireasy folder, look for the **newest `Analysis_…` folder** — your CSV
is inside (one row per song: tempo, syncopation, loudness, key, genre, mood,
and more). Open it with Excel, Numbers, SPSS, or R.

## Good to know

- **First time only:** macOS blocks each `.command` file once — the unblock
  steps are in [INSTALLATION.md](INSTALLATION.md), Step 3.
- You can drag a **single audio file** instead of a folder.
- A folder **of session folders** works too — the CSV gets a `session` column.
- Keep the laptop **open and plugged in** while analyzing.
- Something wrong? `analyze_log.txt` (same folder) has the details — drag it
  into an email to the mireasy author.
