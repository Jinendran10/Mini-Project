from weighting import mitigation_weight

def test_weight_range():
    w = mitigation_weight(0.9, 0.9)
    assert 0.1 <= w <= 1.0
