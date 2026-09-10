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
    assert result.state == "ALCISTA — ESPERAR RESOLUCIÓN DEL CONFLICTO"
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
    assert result.state in {"ALCISTA — ESPERAR RESOLUCIÓN DEL CONFLICTO", "BAJISTA — ESPERAR RESOLUCIÓN DEL CONFLICTO"}


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


def test_missing_core_macro_factor_caps_actionable_state():
    result = calculate_market_confluence({
        "dxy": r(90),
        "us10y": r(70),
        "real_yields": r(99, "UNAVAILABLE"),
        "xauusd": r(70),
    })
    assert result.available_macro_factors == 2
    assert result.missing_macro_factors == ("real_yields",)
    assert result.state == "ALCISTA — ESPERAR CONFIRMACIÓN MACRO (real_yields)"
    assert "Datos incompletos" in result.explanation

def test_bullish_macro_without_price_confirmation_says_what_to_wait_for():
    result = calculate_market_confluence({
        "dxy": r(45),
        "us10y": r(40),
        "real_yields": r(35),
        "xauusd": r(0),
    })
    assert result.state == "ALCISTA — ESPERAR CONFIRMACIÓN DE PRECIO"


def test_bearish_macro_with_bearish_price_is_confirmed():
    result = calculate_market_confluence({
        "dxy": r(-70),
        "us10y": r(-70),
        "real_yields": r(-70),
        "xauusd": r(-60),
    })
    assert result.state == "VENTA FUERTE"


def test_missing_macro_driver_names_the_missing_confirmation():
    result = calculate_market_confluence({
        "dxy": r(80),
        "us10y": r(70),
        "real_yields": r(99, "UNAVAILABLE"),
        "xauusd": r(60),
    })
    assert result.state == "ALCISTA — ESPERAR CONFIRMACIÓN MACRO (real_yields)"
