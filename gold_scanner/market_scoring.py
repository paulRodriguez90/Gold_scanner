from .sources.markets import MarketReading


def market_factor_scores(readings: dict[str, MarketReading]) -> dict[str, float]:
    return {name: reading.score for name, reading in readings.items()}
