from services.m5_fusion.services.dual_coding import DualCodingService


def test_exact_namaste_lookup():
    service = DualCodingService()

    result = service.lookup("Amlapitta")

    assert result is not None
    assert result.namaste_code == "AAE-16"
    assert result.namaste_term == "Amlapitta"
    assert result.icd11_tm2_code == "SF7Y"
    assert result.icd11_tm2_term == (
        "Disorders of digestive function (TM2)"
    )
    assert result.match_type == "exact"
    assert result.confidence == 1.0


def test_normalized_term_lookup():
    service = DualCodingService()

    result = service.lookup("  AMLAPITTA ")

    assert result is not None
    assert result.namaste_code == "AAE-16"
    assert result.icd11_tm2_code == "SF7Y"


def test_fuzzy_term_lookup():
    service = DualCodingService(
        fuzzy_threshold=0.80,
    )

    result = service.lookup("Amlapitta")

    assert result is not None
    assert result.icd11_tm2_code == "SF7Y"


def test_unknown_term_does_not_fabricate_code():
    service = DualCodingService()

    result = service.lookup("Completely Unknown Condition")

    assert result is None


def test_unknown_namaste_code_returns_none():
    service = DualCodingService()

    result = service.lookup_code("UNKNOWN-999")

    assert result is None


def test_code_lookup():
    service = DualCodingService()

    result = service.lookup_code("AAE-16")

    assert result is not None
    assert result.namaste_term == "Amlapitta"
    assert result.icd11_tm2_code == "SF7Y"


def test_mapping_source_is_curated():
    service = DualCodingService()

    result = service.lookup("Amlapitta")

    assert result is not None
    assert result.source == "curated_mapping"


def test_all_mappings_are_loaded():
    service = DualCodingService()

    mappings = service.all_mappings()

    assert len(mappings) == 1
    assert mappings[0].namaste_code == "AAE-16"
