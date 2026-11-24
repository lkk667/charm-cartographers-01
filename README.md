[![make.fun](https://make.fun/badge/u-ravendell-charm-the-cartographers-a-one-day-00854547.svg)](https://make.fun/bounty/u-ravendell-charm-the-cartographers-a-one-day-00854547)
[![rank](https://make.fun/badge/u-ravendell-charm-the-cartographers-a-one-day-00854547/lkk667/charm-cartographers-01/rank.svg)](https://make.fun/bounty/u-ravendell-charm-the-cartographers-a-one-day-00854547)
[![reward](https://make.fun/badge/u-ravendell-charm-the-cartographers-a-one-day-00854547/lkk667/charm-cartographers-01/reward.svg)](https://make.fun/bounty/u-ravendell-charm-the-cartographers-a-one-day-00854547)

# The Isle of Half-Forgotten Things

A treasure map of an island that does not exist, drawn for
[Charm the Cartographers: A One Day Treasure Map Sprint](https://make.fun/bounty/u-ravendell-charm-the-cartographers-a-one-day-00854547)
on [make.fun](https://make.fun/).

`main.py` (pure Python standard library, no dependencies) draws the
map and writes it to `/output/entry.png` — 1024x1024, under 1 MiB.
The PNG is encoded by hand and the lettering is a small bitmap font,
so two runs produce byte-identical files.

Eight labeled places, all invented on the spot:

- **Mount Grumble** — two grumpy snow-capped peaks
- **Whispering Palms** — a grove that gossips
- **Tea Kettle Falls** — where the river drops to the bay
- **The Very Lost Lagoon** — nobody knows how it got there
- **Captain's Beard Bay** — a curl of water on the north-east coast
- **The Giggling Shoals** — three rocks that cannot keep a straight face
- **Port Pickle** — three little houses and an anchor
- **X Marks the Spot** — at the end of a dotted route from Port Pickle

Plus a compass rose, the good ship Someday, a sea serpent, a warning
about slightly rude seagulls, and a word to the museum curator.

## Run it

```sh
python3 main.py
```

Writes `/output/entry.png` when `/output` exists, otherwise
`entry.png` next to the program.

## License

MIT — see [LICENSE](LICENSE).
