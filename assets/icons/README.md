# assets/icons

PNG icons used by the interface, 128×128, transparent background.

These are referenced by `nova/theme.py` (`ICON_MAP`) and loaded by
`nova/assets.py` (`load_icon`).  When an icon file is missing the interface
degrades gracefully — a coloured circle with the app's first letter is drawn
instead — so the project runs with an empty `icons/` directory.

## Generating the icons

Run the procedural generator to produce simple, licence-free icons:

```
python scripts/generate_assets.py icons
```

This draws geometric glyphs (home, apps, movies, favourites, settings, etc.)
using `pygame.draw` and writes them here as PNGs.  You can replace any of
these with your own artwork as long as the filenames match `theme.ICON_MAP`.

## Adding your own icons

- Format: PNG, 128×128, alpha transparency
- Filename must match the value in `theme.ICON_MAP`
- License: keep only artwork you have the right to bundle (MIT, CC0, OFL, etc.)
