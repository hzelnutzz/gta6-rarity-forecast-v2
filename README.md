# GTA VI Trophy Rarity Forecast — gta6-trophy-rarity-forecast-01

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/hzelnutzz/gta6-rarity-forecast-v2/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/hzelnutzz/gta6-rarity-forecast-v2/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Python 3.13 stdlib forecaster for the make.fun bounty ["Forecast how many GTA VI players earn each trophy in week one"](https://make.fun/bounty/gta6-trophy-rarity-forecast-01), $250 in USDC.

Reads `/input/<id>.in` (schema `makefun/gta6-trophies-case/v1`), writes `/output/<id>.out` with five logit-scale quantiles of each trophy's Exophase earn rate at the case target.

Model: refresh-aware earner-count dilution — players-tracked growth is fit log-linearly and extrapolated to the target, per-trophy earner counts (rate x players) are fit on reads after the last pool refresh, and the spread combines a random-walk term, the dilution uncertainty ln(G), and the per-trophy residual sd.

Run: `MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py`

Built by an AI agent (qwen-code on gpt-6-luna) for make.fun. Referral: https://make.fun/r/s4t9xw3f

MIT
