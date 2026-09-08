from gold_scanner.scoring import classify, weighted_score

def test_classification():
    assert classify(80) == "COMPRA FUERTE"
    assert classify(45) == "COMPRA MODERADA"
    assert classify(0) == "INDECISION"
    assert classify(-45) == "VENTA MODERADA"
    assert classify(-80) == "VENTA FUERTE"

def test_weighted_score():
    assert weighted_score({"dxy": 100}) == 12
