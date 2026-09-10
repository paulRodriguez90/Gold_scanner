from gold_scanner.scoring import classify, weighted_score

def test_classification():
    assert classify(80) == "COMPRA FUERTE"
    assert classify(45) == "COMPRA MODERADA"
    assert classify(0) == "INDECISION"
    assert classify(-45) == "VENTA MODERADA"
    assert classify(-80) == "VENTA FUERTE"

def test_weighted_score():
    # DXY is 12% of the total model. With all other factors neutral/missing,
    # a maximum bullish DXY contribution is therefore +12.
    assert weighted_score({"dxy": 100}) == 12


def test_surprise_does_not_report_missing_consensus_when_active_same_key_has_consensus():
    from datetime import date
    from gold_scanner.sources.calendar import EconomicEvent
    from gold_scanner.macro_scoring import calculate_surprise_impact

    events = [
        EconomicEvent("cpi", "2026-08-12", 333.95, 333.92, 333.99, source="Investing.com", released=True, metric="value"),
        EconomicEvent("cpi", "2026-08-12", 3.4, 3.5, None, source="Other", released=True, metric="yoy"),
    ]
    result = calculate_surprise_impact({}, events, {"surprises": {}})
    assert result["missing_consensus"] == []
    assert "sin consenso verificable" not in result["explanation"]
