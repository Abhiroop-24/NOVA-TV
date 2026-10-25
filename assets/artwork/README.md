# assets/artwork

Large cinematic artwork shown on the home screen and content cards.

`nova/ui/screens/home_screen.py` loads `hero_demo.png` (1920×420) for the
featured hero area.  If it is missing, the home screen draws a dark gradient
placeholder instead, so the project runs with an empty `artwork/` directory.

## Generating demo artwork

```
python scripts/generate_assets.py artwork
```

This produces a violet-to-charcoal gradient hero (marked as demo) plus a few
demo content posters.  These are procedurally generated and licence-free.

## Using real artwork

Replace the demo files with licensed posters/backdrops (1920×420 for the
hero, 240×360 for portrait posters).  Demo content shown to the user must be
marked as demo and made replaceable with real data, per the NOVA TV spec.
