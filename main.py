import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path


Z_LEVELS = (-1.645, -0.674, 0.0, 0.674, 1.645)
MIN_PCT = 0.01
MAX_PCT = 99.99


def parse_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def linear_fit(xs, ys):
    if len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    variance_x = sum((x - mean_x) ** 2 for x in xs)
    if variance_x == 0.0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / variance_x
    return mean_y - slope * mean_x, slope


def clamp_pct(value):
    return min(MAX_PCT, max(MIN_PCT, value))


def logit_pct(value):
    fraction = clamp_pct(value) / 100.0
    return math.log(fraction / (1.0 - fraction))


def sigmoid_pct(value):
    if value >= 0.0:
        fraction = 1.0 / (1.0 + math.exp(-value))
    else:
        exp_value = math.exp(value)
        fraction = exp_value / (1.0 + exp_value)
    return clamp_pct(100.0 * fraction)


def quantiles(median, spread):
    center = logit_pct(median)
    result = [round(sigmoid_pct(center + z * spread), 4) for z in Z_LEVELS]
    for index in range(1, len(result)):
        result[index] = max(result[index], result[index - 1])
    return result


def estimate_players(history, target_time):
    samples = []
    for item in history:
        players = item.get("players_tracked")
        if players is not None and players > 0:
            samples.append((parse_time(item["slot"]), float(players)))
    if not samples:
        return 1.0

    origin = samples[0][0]
    xs = [(slot - origin).total_seconds() / 3600.0 for slot, _ in samples]
    target_hours = (target_time - origin).total_seconds() / 3600.0
    ys = [math.log(players) for _, players in samples]
    if len(set(ys)) == 1:
        days_after_last = max(0.0, (target_time - samples[-1][0]).total_seconds() / 86400.0)
        return samples[-1][1] * (1.5 ** days_after_last)

    fit = linear_fit(xs, ys)
    if fit is None:
        return samples[-1][1]
    intercept, slope = fit
    try:
        return max(1.0, math.exp(intercept + slope * target_hours))
    except OverflowError:
        return float("inf")


def forecast_earners(reads, target_time, at_time):
    points = []
    running_max = 0.0
    for slot_time, rate, players in reads:
        running_max = max(running_max, max(0.0, rate / 100.0 * players))
        hours = (slot_time - at_time).total_seconds() / 3600.0
        points.append((hours, running_max))

    last_earners = points[-1][1]
    xs = [hour for hour, _ in points]
    ys = [math.log1p(earners) for _, earners in points]
    fit = linear_fit(xs, ys)
    if fit is None:
        return last_earners
    target_hours = (target_time - at_time).total_seconds() / 3600.0
    intercept, slope = fit
    try:
        predicted = math.expm1(intercept + slope * target_hours)
    except OverflowError:
        predicted = float("inf")
    return max(last_earners, predicted)


def persistence_result(trophy, rate, horizon_days):
    if rate is None:
        return {"id": trophy.get("id"), "q": quantiles(MIN_PCT, 2.0)}
    spread = 0.9 * math.sqrt(max(0.0, horizon_days))
    return {"id": trophy.get("id"), "q": quantiles(rate, spread)}


def forecast_trophy(trophy, trophy_index, history, target_time, at_time, players_hat, horizon_days):
    if not history:
        return persistence_result(trophy, None, horizon_days)

    reads = []
    for item in history:
        rates = item.get("rates")
        if not isinstance(rates, list) or trophy_index >= len(rates):
            continue
        rate = rates[trophy_index]
        if rate is None:
            continue
        players = item.get("players_tracked")
        if players is None or players <= 0:
            continue
        reads.append((parse_time(item["slot"]), float(rate), float(players)))

    if not reads:
        return persistence_result(trophy, None, horizon_days)

    earners_hat = forecast_earners(reads, target_time, at_time)
    median = clamp_pct(100.0 * earners_hat / players_hat)

    logit_points = [
        ((slot_time - at_time).total_seconds() / 3600.0, logit_pct(rate))
        for slot_time, rate, _ in reads
    ]
    residual_spread = 0.0
    if len(set(logit_points)) >= 3:
        fit = linear_fit([hour for hour, _ in logit_points], [value for _, value in logit_points])
        if fit is not None:
            intercept, slope = fit
            residuals = [value - (intercept + slope * hour) for hour, value in logit_points]
            residual_spread = math.sqrt(sum(residual * residual for residual in residuals) / len(residuals))

    walk_spread = 0.9 * math.sqrt(max(0.0, horizon_days))
    spread = math.sqrt(walk_spread * walk_spread + residual_spread * residual_spread)
    return {"id": trophy.get("id"), "q": quantiles(median, spread)}


def forecast_case(case):
    trophies = case.get("trophies", [])
    history = case.get("history", [])
    at_time = parse_time(case["at"])
    target_time = parse_time(case["target"])
    horizon_days = max(0.0, float(case.get("horizon_minutes", 0.0)) / 1440.0)
    players_hat = estimate_players(history, target_time)

    forecasts = []
    for index, trophy in enumerate(trophies):
        fallback_rate = None
        if index < len(trophies):
            for item in reversed(history):
                rates = item.get("rates")
                if isinstance(rates, list) and index < len(rates) and rates[index] is not None:
                    try:
                        fallback_rate = clamp_pct(float(rates[index]))
                    except (TypeError, ValueError):
                        fallback_rate = None
                    break
        try:
            forecasts.append(
                forecast_trophy(
                    trophy,
                    index,
                    history,
                    target_time,
                    at_time,
                    players_hat,
                    horizon_days,
                )
            )
        except Exception:
            forecasts.append(persistence_result(trophy, fallback_rate, horizon_days))
    return {"trophies": forecasts}


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    for input_path in sorted(input_dir.glob("*.in")):
        with input_path.open("r", encoding="utf-8") as source:
            case = json.load(source)
        result = forecast_case(case)
        output_path = output_dir / (str(case["id"]) + ".out")
        with output_path.open("w", encoding="utf-8") as destination:
            json.dump(result, destination, separators=(",", ":"), allow_nan=False)
            destination.write("\n")


if __name__ == "__main__":
    main()
