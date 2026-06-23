# gd-tp-porter

Port Geometry Dash **2.1-era texture packs** so they work cleanly on **2.2**,
without manually splitting icon sheets or hunting down broken plists.

This automates a process that's usually done by hand (or with a one-off
script + a lot of trial and error): split the old monolithic icon sheet into
the per-icon sheets 2.2 expects, and repair a handful of real-world plist
bugs that show up in packs distributed in the wild.

## What it does

1. **Splits icons for 2.2.** Pre-2.2, every player/ship/robot/spider/dart/
   bird icon variant lived crammed into `GJ_GameSheet02` (+ glow variants in
   `GJ_GameSheetGlow`). 2.2 instead expects one small sheet per icon under
   `Resources/icons/`. This tool does that split for you, for whichever
   quality level(s) the pack ships (`""`, `-hd`, `-uhd`).

2. **Repairs known plist corruption.** Some distributed packs have a
   `<true/>`/`<false/>` for `textureRotated` that's missing its preceding
   `<key>textureRotated</key>` tag. This is invalid plist XML and breaks
   parsing (and the game). Detected and fixed automatically.

3. **Fixes stale `metadata.size` fields.** Cosmetic only — doesn't affect
   rendering — but several packs have a leftover value from an older
   export. Corrected for cleanliness.

4. **Flags (and can fix) sheets that are missing their `.plist` entirely.**
   Seen in the wild with `GJ_GameSheet04` (the sheet behind Hall of Fame,
   Daily, Weekly, Map Packs, Gauntlets, Featured, etc.) — some packs ship
   the `.png` with no matching `.plist` at all. Without a descriptor,
   Cocos2d can't know where to crop each sprite, and the UI renders as
   broken/misplaced fragments. If you pass `--reference <vanilla_2.2_dir>`
   and the pack's PNG is **pixel-identical in size** to the reference's,
   the tool borrows the reference's frame *coordinates* (not artwork) to
   regenerate a working plist. If the size doesn't match, it refuses and
   tells you why, rather than guessing.

5. **Never touches the in-game gameplay sheet.** See below — this is the
   single most important design decision in this tool.

## Install

```bash
git clone https://github.com/<you>/gd-tp-porter.git
cd gd-tp-porter
pip install -r requirements.txt
```

`.rar` extraction needs a working unrar-compatible tool on your system. The
non-free `unrar` binary works out of the box; on Debian/Ubuntu the default
`unrar-free` package only supports RAR4 and **not** RAR5 (which a lot of
texture packs are distributed as). If extraction fails, install one of:

```bash
sudo apt install p7zip-full       # provides 7z, reads RAR5
sudo apt install libarchive-tools # provides bsdtar
```

The tool tries `rarfile`/`unrar` first and automatically falls back to
`7z`/`7za`/`bsdtar` if needed.

## Usage

```bash
# Straight from a downloaded archive:
python -m gd_tp_porter MyPack.rar

# Also produce a ready-to-share .zip:
python -m gd_tp_porter MyPack.rar --zip

# Already extracted:
python -m gd_tp_porter ./MyPackFolder -o ./MyPackFolder_2.2

# Also backfill missing menu-sheet plists (GJ_GameSheet04, GauntletSheet,
# etc.) using coordinates borrowed from a vanilla 2.2 Resources folder:
python -m gd_tp_porter MyPack.rar --reference ./vanilla_2.2_resources
```

Run `python -m gd_tp_porter --help` for the full option list. Every run
prints a report of exactly what was changed, what was skipped, and why —
nothing happens silently.

### Getting a `--reference` folder

Any legitimate, unmodified copy of Geometry Dash 2.2's `Resources` folder
works. The tool only ever reads `GJ_GameSheet02/03/04`, `GameSheetGlow`,
`LaunchSheet`, `BE_GameSheet01`, and `GauntletSheet` from it — and only
to borrow plist *coordinates* when a pack is missing its own plist and the
PNG dimensions match exactly.

## Why this tool never touches `GJ_GameSheet` (no number)

This is the most important thing to understand before using this tool, so
it gets its own section.

Geometry Dash has **two** very differently-named sheets that are easy to
confuse:

- `GJ_GameSheet02` / `03` / `04` / `Glow` — **menu, UI, and icon** sprites.
  Texture packs customize these.
- `GJ_GameSheet` (no number) — the **in-game gameplay** sheet: spikes,
  blocks, orbs, portals, and decorations that actually appear inside levels.

The overwhelming majority of texture packs — including ones whose names
suggest otherwise — **only re-skin menus and icons** and never touch
in-game sprites at all. If a pack doesn't ship its own `GJ_GameSheet`, that
is not a bug to fix. It means the player's own existing Geometry Dash
installation keeps supplying it, exactly as it already was before they
installed the pack.

An earlier (manual, pre-this-tool) attempt at this exact porting process
got this wrong: it saw `GJ_GameSheet` "missing" from a pack and copied in a
vanilla copy from an unrelated source to "complete" it. That copy wasn't
guaranteed to byte-match the user's actual game version, and it broke
in-game decorative spikes that had been rendering correctly using the
user's own real copy the whole time. The fix was to simply stop doing that.

`gd_tp_porter.guardrails` enforces this in code (`assert_not_protected`,
exercised by `tests/test_porter_integration.py::
test_port_pack_never_creates_protected_ingame_sheet`), not just in this
paragraph: nothing in this tool's pipeline is capable of writing
`GJ_GameSheet.png`, `GJ_GameSheet-hd.png`, `GJ_GameSheet-uhd.png` (or their
`.plist`s) under any circumstance, even if a `--reference` folder happens
to contain one. If a pack genuinely does ship its own customized
`GJ_GameSheet`, the tool leaves it completely untouched — it just never
adds or replaces one itself.

## What this tool deliberately does NOT do

- **Generate missing artwork.** If a pack never drew a sprite for some 2.2
  addition (decorative spikes, boost/portal shine variants, etc.), this
  tool does not invent a texture for it. Those elements fall back to
  vanilla Geometry Dash's own art, which is the correct, non-broken
  behavior — not a bug.
- **Guess plist coordinates without evidence.** The `--reference` backfill
  only fires when the pack's PNG is pixel-identical in size to the
  reference. If sizes differ even slightly, the tool refuses and tells you
  why rather than producing a misaligned UI.
- **Modify in-game gameplay sprites**, per above.

## Project layout

```
gd_tp_porter/
  plist_utils.py   # plist parsing/repair primitives (Rect, size fixups)
  icon_split.py     # GameSheet02+Glow -> per-icon sheets (the 2.2 split)
  sheet_audit.py    # menu/UI sheet repair (missing/stale plists)
  guardrails.py     # the in-game-sheet protection described above
  extract.py        # .zip/.rar extraction with RAR5 fallback handling
  porter.py         # ties it all together, produces a PortReport
  __main__.py       # CLI
tests/              # pytest suite, including the guardrail regression test
```

## Credits

The icon-splitting approach (which frames belong to which 2.2 icon sheet,
and how to lay out the resulting per-icon atlas) was originally worked out
by [Weebifying's 2.2tpconvert](https://github.com/Weebifying/2.2tpconvert).
This project reimplements that logic with a different internal structure
(no regex-based rect parsing, multi-quality in one pass) and adds the
plist-repair and guardrail logic on top.

## License

MIT — see [LICENSE](LICENSE).
