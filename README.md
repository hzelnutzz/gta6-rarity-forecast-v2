# GTA VI Trophy Rarity Forecast

Python 3.13 stdlib forecaster for make.fun `gta6-trophy-rarity-forecast-01`.

Reads `/input/<id>.in` (schema `makefun/gta6-trophies-case/v1`), writes `/output/<id>.out`
with five logit-scale quantiles of each trophy's Exophase earn rate at the case target.

Model: refresh-aware earner-count dilution — players-tracked growth is fit log-linearly
and extrapolated to the target, per-trophy earner counts (rate x players) are fit on reads
after the last pool refresh, and the spread combines a random-walk term, the dilution
uncertainty ln(G), and the per-trophy residual sd.

[![bounties](https://img.shields.io/badge/make.fun-bounty-blue)](https://make.fun)
[![competition](https://img.shields.io/badge/comp-gta6--trophy--rarity--forecast--01-green)](https://make.fun/c/gta6-trophy-rarity-forecast-01)

MIT
