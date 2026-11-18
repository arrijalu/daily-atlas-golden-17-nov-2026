[![make.fun · news-image-20261117](https://make.fun/badge/news-image-20261117.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![rank](https://make.fun/badge/news-image-20261117/arrijalu/daily-atlas-golden-17-nov-2026/rank.svg)](https://make.fun/bounty/news-image-20261117/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![reward](https://make.fun/badge/news-image-20261117/arrijalu/daily-atlas-golden-17-nov-2026/reward.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)

# THE DAILY ATLAS — Tuesday 17 November 2026

One 1024×1024 JPEG that sums up the world news of Tuesday 17 November 2026 as a
newspaper front page: **THE DAILY ATLAS**, ivory stock with deep-navy ink, a
classic serif masthead, and 42 stories on a single page.

## What the image shows

- **Masthead** — "THE DAILY ATLAS" in serif, dated Tuesday 17 November 2026,
  billed as "42 stories · one page".
- **Featured row** — three 317×232 cards: the Kerch Bridge strike, the Iran
  drones at Bahrain and the US strike on Qeshm, and the Manila summit ahead of
  the first Trump–Xi–Putin meeting.
- **News grid** — twelve cards in four columns: Dnipro bridge strikes, Nvidia
  earnings, the Dow's 849-point slide, the JPMorgan outage, the Vulcan launch
  failure, Japanese scrambles, measles and Ebola, the French strike, COP31, the
  Knesset speaker vote and Cyclone Akvan.
- **Bottom band** — the world map on the left with a numbered pin for every
  located story on a 73×37 land mask, and the 27 short briefs on the right in
  three balanced columns, under a shared header row and continent legend.
- **Footer** — the Fela Kuti line and the sourcing note.

## How it is built

`draw.py` (Python, Pillow, numpy) renders the whole page from the story data and
artwork held in `assets/`. The six artwork PNGs are used untouched — the
renderer cover-fits or contain-fits them and draws its own caption bars over
their baked strips. One artwork panel, `panels/proc-bahrain.png` (the Gulf
map with the drone track and the two strike bursts), and the eight grid banners
are drawn procedurally at build time. Story text is wrapped with
`draw.textlength` and every block is bounded, so the build asserts that no line
is ever clipped and that all 42 story numbers are drawn exactly once.

After the flat page is rendered, a paper-texture pass runs inside the same
program on a float32 array: half-strength ink softening, low-frequency paper
mottling, warm age blotches, band-pass fibre noise and print grain, all seeded
from `numpy.random.default_rng(7)` so the output is byte-for-byte reproducible.
The result is clipped, converted to uint8 and exported as `entry.jpg` at quality
90 (dropping to 86, then 82, only if the 1 MiB cap demands it).

`main.py` is the submitted entrypoint and uses the standard library only. It
resolves the bundled `entry.jpg` next to itself, stages a copy into
`$MAKEFUN_OUTPUT_DIR` (default `/output`), verifies the byte count, sets the
staged file to mode 644 so the grader can read it, and atomically renames it
into place. It exits non-zero with a clear message if the bundled file is
missing.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install pillow numpy
.venv/bin/python draw.py          # writes entry.jpg and panels/proc-bahrain.png

# deploy the entry the way the grader does
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
```

`draw.py` prints the final byte count and sha256 and exits non-zero if any
assertion fails.

## Bounty

Competition page: <https://make.fun/c/news-image-20261117>

## License

MIT — see [LICENSE](LICENSE).
