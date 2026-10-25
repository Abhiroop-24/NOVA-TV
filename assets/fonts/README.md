# assets/fonts

Bundled TrueType fonts.

`nova/assets.py` looks for:

- `Inter-Regular.ttf`  (default body font)
- `Inter-Bold.ttf`     (headings / emphasis)

If neither is found, it falls back to the first `.ttf` in this directory, and
if the directory is empty it falls back to Pygame's system sans font.  The
project therefore runs with an empty `fonts/` directory, though a bundled font
gives a more consistent look.

## Recommended font

[Inter](https://rsms.me/inter/) is a high-quality screen typeface licensed
under the SIL Open Font License (OFL).  Download `Inter-Regular.ttf` and
`Inter-Bold.ttf` and place them here.  Any other .ttf works too — the loader
picks the first one it finds.

## Generating a simple bundled font

If you have no internet access, `scripts/generate_assets.py fonts` creates a
minimal placeholder so the loader has a file to use.  For real typography,
install Inter or another OFL-licensed font here.
