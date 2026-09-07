from services.m3_conversation.services.dialogue_manager import DialogueManager
from services.m3_conversation.services.ontology_loader import OntologyLoader


AYUSH_IDS = [
    # Prakriti
    "ayush.prakriti.dosha_tendency",

    # Vikriti
    "ayush.vikriti.current_dosha_change",
    "ayush.vikriti.symptom_pattern",

    # Agni
    "ayush.agni.appetite",
    "ayush.agni.digestion",

    # Koshtha
    "ayush.koshtha.bowel_pattern",

    # Ahara / Vihara
    "ayush.ahara_vihara.diet",
    "ayush.ahara_vihara.hydration",
    "ayush.ahara_vihara.sleep",
    "ayush.ahara_vihara.activity",

    # Nidana
    "ayush.nidana.possible_triggers",
    "ayush.nidana.recent_changes",

    # Samprapti
    "ayush.samprapti.progression",
    "ayush.samprapti.associated_pattern",

    # Trividha Pariksha
    "ayush.trividha.darshana",
    "ayush.trividha.prashna",
    "ayush.trividha.sparshana",

    # Ashtavidha Pariksha
    "ayush.ashtavidha.nadi",
    "ayush.ashtavidha.mutra",
    "ayush.ashtavidha.mala",
    "ayush.ashtavidha.jihva",
    "ayush.ashtavidha.shabda",
    "ayush.ashtavidha.sparsha",
    "ayush.ashtavidha.drishti",
    "ayush.ashtavidha.akriti",

    # Dashavidha Pariksha
    "ayush.dashavidha.prakriti",
    "ayush.dashavidha.vikriti",
    "ayush.dashavidha.sara",
    "ayush.dashavidha.samhanana",
    "ayush.dashavidha.pramana",
    "ayush.dashavidha.satmya",
    "ayush.dashavidha.sattva",
    "ayush.dashavidha.ahara_shakti",
    "ayush.dashavidha.vyayama_shakti",
    "ayush.dashavidha.vaya",
]


def _answer_current_question(manager, session_id, answer):
    return manager.process_turn(
        session_id,
        text_english=answer,
        audio_provenance_ref="ayush-test-audio",
        asr_confidence=0.95,
    )


def _complete_core_interview(manager, session_id):
    result = manager.start_session(session_id)

    assert result["state"] == "continue"
    assert result["question"]["id"] == "general.chief_complaint"

    answers = [
        "I have fever.",
        "For three days.",
        "It is moderate.",
        "It started three days ago.",
        "I feel it mainly in my chest.",
        "It feels like a dull discomfort.",
        "It becomes worse when I exert myself.",
        "Rest makes it better.",
        "I also have body ache.",
        "I have no major medical conditions.",
    ]

    expected_next = [
        "hpi.duration",
        "hpi.severity",
        "hpi.onset",
        "hpi.location",
        "hpi.character",
        "hpi.aggravating_factors",
        "hpi.relieving_factors",
        "hpi.associated_symptoms",
        "general.past_medical_history",
    ]

    for index, answer in enumerate(answers):
        result = _answer_current_question(
            manager,
            session_id,
            answer,
        )

        if index < len(expected_next):
            assert result["next_question"]["id"] == expected_next[index]

    # Continue through every ROS question until AYUSH begins.
    while (
        result.get("next_question") is not None
        and result["next_question"]["id"].startswith("ros.")
    ):
        result = _answer_current_question(
            manager,
            session_id,
            "No.",
        )

    return result

def test_ayush_questions_are_loaded():
    loader = OntologyLoader()

    questions = loader.load()

    ids = {question["id"] for question in questions}

    for question_id in AYUSH_IDS:
        assert question_id in ids


def test_ayush_starts_after_core_hpi():
    manager = DialogueManager()

    session_id = "ayush-flow-001"

    result = manager.start_session(session_id)

    assert result["state"] == "continue"
    assert result["question"]["id"] == "general.chief_complaint"

    result = _complete_core_interview(
        manager,
        session_id,
    )

    assert result["next_question"] is not None
    assert result["next_question"]["id"] in AYUSH_IDS


def test_ayush_does_not_interrupt_initial_clinical_flow():
    manager = DialogueManager()

    session_id = "ayush-flow-002"

    result = manager.start_session(session_id)

    assert not result["question"]["id"].startswith("ayush.")

    clinical_answers = [
        "I have fever.",
        "For three days.",
        "It is moderate.",
    ]

    for answer in clinical_answers:
        result = _answer_current_question(
            manager,
            session_id,
            answer,
        )

        assert result["next_question"] is not None
        assert not result["next_question"]["id"].startswith("ayush.")


def test_ayush_questions_progress_without_restarting():
    manager = DialogueManager()

    session_id = "ayush-flow-003"

    result = _complete_core_interview(
        manager,
        session_id,
    )

    seen = []

    while result.get("next_question") is not None:
        current_id = result["next_question"]["id"]

        if not current_id.startswith("ayush."):
            break

        seen.append(current_id)

        result = _answer_current_question(
            manager,
            session_id,
            "AYUSH test response",
        )

        if len(seen) >= len(AYUSH_IDS):
            break

    assert seen
    assert seen[0] == "ayush.prakriti.dosha_tendency"

    assert all(
        question_id in AYUSH_IDS
        for question_id in seen
    )

    assert len(seen) == len(set(seen))


def test_prakriti_is_collected_but_not_scored_by_m3():
    manager = DialogueManager()

    session_id = "ayush-flow-004"

    _complete_core_interview(
        manager,
        session_id,
    )

    _answer_current_question(
        manager,
        session_id,
        "Usually I feel energetic but get tired in hot weather.",
    )

    slots = manager.get_slots(session_id)

    assert isinstance(slots, list)

    prakriti_slots = [
        slot
        for slot in slots
        if slot.get("ontology_key") == "ayush.prakriti.dosha_tendency"
    ]

    assert prakriti_slots

    # M3 collects the Prakriti response.
    # Prakriti scoring belongs to M5 and must not be performed here.
    assert "prakriti_score" not in manager.get_state(session_id).__dict__
    assert "dosha_score" not in manager.get_state(session_id).__dict__