from types import SimpleNamespace
from gold_scanner.bias import classify_bias, build_daily_bias, build_weekly_bias


def test_bias_labels_are_directional_not_trade_actions():
    assert classify_bias(75)[0] == "SESGO ALCISTA FUERTE"
    assert classify_bias(45)[0] == "SESGO ALCISTA MODERADO"
    assert classify_bias(20)[0] == "SESGO ALCISTA DÉBIL"
    assert classify_bias(0)[0] == "SESGO NEUTRAL"
    assert classify_bias(-20)[0] == "SESGO BAJISTA DÉBIL"
    assert classify_bias(-45)[0] == "SESGO BAJISTA MODERADO"
    assert classify_bias(-75)[0] == "SESGO BAJISTA FUERTE"


def test_weekly_bias_emphasizes_fundamental_context():
    macro = SimpleNamespace(score=-50, factors=())
    result = build_weekly_bias(macro, {"score": 20})
    assert result.score == -29.0
    assert result.bias == "SESGO BAJISTA DÉBIL"


def test_daily_bias_uses_combined_context():
    confluence = SimpleNamespace(score=-30, conflict=True)
    macro = SimpleNamespace(score=-40)
    result = build_daily_bias(-25, confluence, macro, {"score": 10})
    assert result.score == -25.0
    assert result.bias == "SESGO BAJISTA DÉBIL"
    assert "conflicto" in result.reason
