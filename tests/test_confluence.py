from types import SimpleNamespace

from gold_scanner.confluence import calculate_market_confluence


def r(score, source="test"):
    return SimpleNamespace(score=score, source=source)


def test_bullish_macro_with_bullish_gold_is_confirmed():
    result = calculate_market_confluence({
        "dxy": r(80),
        "us10y": r(70),
        "real_yields": r(75),
        "xauusd": r(60),
    })
    assert result.macro_pressure > 60
    assert result.state == "COMPRA FUERTE"
    assert result.conflict is False


def test_bullish_macro_with_bearish_gold_waits():
    result = calculate_market_confluence({
        "dxy": r(70),
        "us10y": r(60),
        "real_yields": r(65),
        "xauusd": r(-60),
    })
    assert result.conflict is True
    assert result.state == "ALCISTA — ESPERAR"
    assert "XAUUSD" in result.explanation


def test_macro_drivers_in_conflict_do_not_become_clean_signal():
    result = calculate_market_confluence({
        "dxy": r(80),
        "us10y": r(-70),
        "real_yields": r(75),
        "xauusd": r(50),
    })
    assert result.conflict is True
    assert result.conflict_level == "MEDIO"
    assert result.state in {"ALCISTA — ESPERAR", "BAJISTA — ESPERAR"}


def test_unavailable_real_yield_is_ignored_without_crash():
    result = calculate_market_confluence({
        "dxy": r(50),
        "us10y": r(40),
        "real_yields": r(99, "UNAVAILABLE"),
        "xauusd": r(30),
    })
    assert result.macro_pressure > 0
    assert result.xau_confirmation == 30


def test_neutral_market_is_indecision():
    result = calculate_market_confluence({
        "dxy": r(0),
        "us10y": r(5),
        "real_yields": r(-5),
        "xauusd": r(0),
    })
    assert result.state == "INDECISION"
    assert result.conflict is False
