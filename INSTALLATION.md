# Installing easymir — no experience needed

This guide assumes you have **never used a terminal, Python, or git**. You will
click through four steps; the installer does everything else and checks its own
work. Total time: **10–20 minutes** (mostly waiting).

## Before you start — will it run on your Mac?

Click the ** menu (top-left) → About This Mac** and check:

| You need | Where it says so |
|---|---|
| An Apple Silicon chip (M1, M2, M3, M4 …) | "Chip: Apple M…" — 2021 or newer Macs. *Intel Macs are not supported.* |
| macOS 15 (Sequoia) or newer | "macOS 15…" or higher (update via System Settings → General → Software Update) |
| ~6 GB free space, internet, and your Mac password | — |

---

## Step 1 — Install Miniconda (the scientific Python)

1. Download: **<https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.pkg>**
2. Double-click the downloaded file and click **Continue / Agree / Install**
   through all the screens (the standard choices are fine).

## Step 2 — Download easymir

1. On the easymir GitHub page, click the green **`<> Code`** button → **Download ZIP**.
2. In your **Downloads** folder, double-click the ZIP. A folder named
   **`easymir-main`** appears — that folder is easymir.
   *(Re-downloading later? Delete the old `easymir-main` folder first.)*

## Step 3 — Run the installer

Open the `easymir-main` folder and **double-click `install.command`**.

> **macOS will block it the first time — this is expected.** The installer is a
> university research script, not an App Store app, so macOS shows:
> *"Apple could not verify 'install.command' is free of malware…"*
>
> 1. Click **Done**. ⚠️ **Not "Move to Trash"** — that deletes the installer
>    (if that happens, just re-do Step 2).
> 2. Open ** → System Settings → Privacy & Security**, scroll down to
>    *"'install.command' was blocked…"* and click **Open Anyway**, then
>    confirm with your password or Touch ID.
>    *(This entry only appears right after the blocked attempt in point 1.)*
> 3. A Terminal window opens. If macOS asks whether Terminal may access your
>    **Downloads** folder, click **Allow**.

You only do this unblock dance **once per `.command` file**.

## Step 4 — Wait for the checkmark

The installer window prints what it is doing. While it runs:

- Keep the laptop **open and plugged in**. A long wall of scrolling text for
  5–15 minutes is **normal**.
- The installer accepts conda's standard Terms of Service
  ([anaconda.com/legal](https://anaconda.com/legal)) — conda requires this for
  automated installs, and it tells you so on screen.

You are done when it prints:

```
✓✓✓  easymir is ready!  ✓✓✓
```

---

## Using easymir (every day)

Two buttons, described in [how_to_run.md](how_to_run.md):

- **`analyze_folder.command`** — analyze everything automatically → CSV.
- **`run_easymir.command`** — explore interactively.

Both: double-click (same one-time unblock as Step 3), **drag your audio folder
into the window**, press Return. Results land in an **`Analysis_…`** folder in
`easymir-main`.

## If anything goes wrong

Every run writes a file called **`install_log.txt`** inside `easymir-main`.
Open a new email to the easymir author, **drag `install_log.txt` into the
email**, and send — it contains everything needed to help you. You can always
safely re-run `install.command`; it never breaks an existing installation.

**If double-clicking opens the file in a text editor instead of running it**
(or nothing happens): open **Terminal** (⌘-space, type "Terminal", Return),
type `zsh ` (with a space), **drag `install.command` into the Terminal
window**, and press Return. This always works.

---

<details>
<summary><b>Appendix — manual installation (for terminal users)</b></summary>

```bash
git clone https://github.com/Atilik/easymir.git
cd easymir
conda env create -f environment.yml
conda activate easymir
python download_models.py     # optional: enables genre/mood/pitch features
python run_tests.py           # should finish with "… passed" and no failures
python -m easymir /path/to/audio/
```

Requirements: conda and git. Nothing compiles — the two non-PyPI dependencies
install from prebuilt wheels in `wheels/` (see `wheels/README.md`).
See README.md for the full feature documentation.
</details>
