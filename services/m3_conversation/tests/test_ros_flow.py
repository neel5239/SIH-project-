from services.m3_conversation.services.dialogue_manager import DialogueManager


def answer(manager, session_id, text):
    return manager.process_turn(
        session_id,
        text_english=text,
        audio_provenance_ref="ros-test-audio",
        asr_confidence=0.95,
    )


def start_chest_interview(manager, session_id):
    result = manager.start_session(session_id)

    assert result["question"]["id"] == "general.chief_complaint"

    result = answer(
        manager,
        session_id,
        "I have chest pain.",
    )

    return result


def test_ros_questions_exist_in_ontology():
    manager = DialogueManager()

    questions = manager.ontology_loader.get_all_questions()

    ros_questions = [
        question
        for question in questions
        if question["id"].startswith("ros.")
    ]

    assert len(ros_questions) == 17


def test_ros_does_not_interrupt_socrates():
    manager = DialogueManager()

    session_id = "ros-flow-001"

    result = manager.start_session(session_id)

    assert result["question"]["id"] == "general.chief_complaint"

    result = answer(
        manager,
        session_id,
        "I have chest pain.",
    )

    assert result["next_question"]["id"] == "socrates.site"

    result = answer(
        manager,
        session_id,
        "In the center of my chest.",
    )

    assert result["next_question"]["id"].startswith("socrates.")


def test_ros_does_not_interrupt_system_branch():
    manager = DialogueManager()

    session_id = "ros-flow-002"

    result = start_chest_interview(
        manager,
        session_id,
    )

    # The first question after chief complaint should remain
    # within the clinical branch rather than jumping directly
    # into ROS.
    assert not result["next_question"]["id"].startswith("ros.")


def test_general_ros_questions_are_valid():
    manager = DialogueManager()

    questions = manager.ontology_loader.get_all_questions()

    general_ros = [
        question
        for question in questions
        if question["id"].startswith("ros.general.")
    ]

    ids = {question["id"] for question in general_ros}

    assert ids == {
        "ros.general.fever",
        "ros.general.fatigue",
    }


def test_branch_specific_ros_questions_are_valid():
    manager = DialogueManager()

    questions = manager.ontology_loader.get_all_questions()

    ros_ids = {
        question["id"]
        for question in questions
        if question["id"].startswith("ros.")
    }

    expected = {
        "ros.cardiovascular.chest_discomfort",
        "ros.cardiovascular.palpitations",
        "ros.cardiovascular.leg_swelling",
        "ros.respiratory.cough",
        "ros.respiratory.breathlessness",
        "ros.respiratory.wheezing",
        "ros.gastrointestinal.nausea",
        "ros.gastrointestinal.bowel_change",
        "ros.gastrointestinal.appetite",
        "ros.neurological.headache",
        "ros.neurological.dizziness",
        "ros.neurological.numbness",
        "ros.musculoskeletal.joint_pain",
        "ros.musculoskeletal.stiffness",
        "ros.musculoskeletal.swelling",
    }

    assert expected.issubset(ros_ids)


def test_ros_questions_have_dual_input_modes():
    manager = DialogueManager()

    questions = manager.ontology_loader.get_all_questions()

    ros_questions = [
        question
        for question in questions
        if question["id"].startswith("ros.")
    ]

    assert ros_questions

    for question in ros_questions:
        input_modes = question.get("input_modes", [])

        assert "voice" in input_modes
        assert "touch" in input_modes