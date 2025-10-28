from scripts.utils_pint import to_canonical

def test_to_canonical_mass():
    val, unit = to_canonical(1, "kg")
    assert unit == "g" and abs(val - 1000) < 1e-6

def test_to_canonical_volume():
    val, unit = to_canonical(2, "L")
    assert unit == "ml" and abs(val - 2000) < 1e-6

def test_to_canonical_pcs():
    val, unit = to_canonical(5, "pcs")
    assert unit == "pcs" and val == 5