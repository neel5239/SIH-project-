from services.m5_fusion.services.prakriti import PrakritiScorer


def test_single_dosha_scoring():
    scorer = PrakritiScorer()

    result = scorer.score(
        [
            {
                "ontology_key": "ayush.prakriti.dosha_tendency",
                "value": "vata",
                "confidence": 1.0,
                "provenance_id": "p1",
            }
        ]
    )

    assert result.vata == 1.0
    assert result.pitta == 0.0
    assert result.kapha == 0.0
    assert result.dominant == "vata"
    assert result.items_total == 1
    assert result.answered_questions == 1


def test_mixed_dosha_scores_are_normalized():
    scorer = PrakritiScorer()

    result = scorer.score(
        [
            {
                "ontology_key": "ayush.prakriti.one",
                "value": "vata",
                "confidence": 1.0,
                "provenance_id": "p1",
            },
            {
                "ontology_key": "ayush.prakriti.two",
                "value": "pitta",
                "confidence": 1.0,
                "provenance_id": "p2",
            },
            {
                "ontology_key": "ayush.prakriti.three",
                "value": "kapha",
                "confidence": 1.0,
                "provenance_id": "p3",
            },
        ]
    )

    assert round(result.vata + result.pitta + result.kapha, 6) == 1.0
    assert round(result.vata, 2) == 0.33
    assert round(result.pitta, 2) == 0.33
    assert round(result.kapha, 2) == 0.33
    assert result.dominant == "vata-pitta"


def test_low_confidence_answer_reduces_score_confidence():
    scorer = PrakritiScorer()

    result = scorer.score(
        [
            {
                "ontology_key": "ayush.prakriti.dosha_tendency",
                "value": "vata",
                "confidence": 0.4,
                "provenance_id": "p1",
            }
        ]
    )

    assert result.vata == 1.0
    assert result.confidence < 0.5
    assert result.provisional is True


def test_missing_prakriti_data_is_provisional():
    scorer = PrakritiScorer()

    result = scorer.score(
        [
            {
                "ontology_key": "general.chief_complaint",
                "value": "headache",
                "confidence": 1.0,
                "provenance_id": "p1",
            }
        ]
    )

    assert result.items_total == 0
    assert result.answered_questions == 0
    assert result.provisional is True
    assert result.confidence == 0.0
    assert result.to_dict()["dominant"] == "vata"


def test_weighted_prakriti_answer():
    scorer = PrakritiScorer()

    result = scorer.score(
        [
            {
                "ontology_key": "ayush.prakriti.one",
                "value": "vata",
                "weight": 2.0,
                "confidence": 1.0,
                "provenance_id": "p1",
            },
            {
                "ontology_key": "ayush.prakriti.two",
                "value": "pitta",
                "weight": 1.0,
                "confidence": 1.0,
                "provenance_id": "p2",
            },
        ]
    )

    assert result.vata > result.pitta
    assert round(result.vata + result.pitta + result.kapha, 6) == 1.0


def test_non_prakriti_slots_are_ignored():
    scorer = PrakritiScorer()

    result = scorer.score(
        [
            {
                "ontology_key": "general.chief_complaint",
                "value": "vata",
                "confidence": 1.0,
                "provenance_id": "p1",
            },
            {
                "ontology_key": "ayush.prakriti.dosha_tendency",
                "value": "kapha",
                "confidence": 1.0,
                "provenance_id": "p2",
            },
        ]
    )

    assert result.vata == 0.0
    assert result.pitta == 0.0
    assert result.kapha == 1.0
    assert result.items_total == 1
    assert result.answered_questions == 1
