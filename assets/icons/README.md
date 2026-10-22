# Custom flora & fauna icons

Drop your own marker images in this folder. The app picks them up on the next
Streamlit rerun (press **R** or use the ⋮ menu → *Rerun*), no code changes
needed.

## File names

Name the file after the taxon key used by the app, in any of these spellings
(case, dashes, underscores and spaces are ignored):

| Taxon key in the app | Accepted file names |
| --- | --- |
| `Orangutan` | `orangutan.*` |
| `Proboscis_monkey` | `proboscis-monkey.*`, `proboscis_monkey.*`, `proboscismonkey.*` |
| `Rafflesia` | `rafflesia.*` |
| `Nepenthes` | `nepenthes.*` |
| any other taxon | `default.*` (fallback) |

## Formats

`png`, `webp`, `jpg`, `jpeg`, `svg` — in that order of preference (if both
`orangutan.png` and `orangutan.svg` exist, the PNG wins).

Use a square image with a transparent background; it is drawn at 28×28 CSS
pixels on the map (30×30 on the Kalimantan-wide map), anchored at the centre.
256×256 source images stay sharp on high-DPI screens.

## Replacing an icon

1. Add or overwrite e.g. `orangutan.png` here.
2. Rerun the app.
3. To go back to the built-in icon, restore the original `.svg` file.

If a taxon has neither a specific icon nor `default.*`, the app falls back to
its plain geometric marker (a coloured triangle/circle), so a missing file
never breaks the map.
