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
