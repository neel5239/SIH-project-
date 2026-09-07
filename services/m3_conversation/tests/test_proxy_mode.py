from services.m3_conversation.services.dialogue_manager import DialogueManager
from services.m3_conversation.services.ontology_loader import OntologyLoader
from services.m3_conversation.services.slot_filler import SlotFiller
from services.m3_conversation.services.branch_selector import BranchSelector
from services.m3_conversation.services.completion import CompletionPolicy


def make_manager():
    loader = OntologyLoader()
    filler = SlotFiller()
    branch_selector = BranchSelector()
    completion = CompletionPolicy()
    return DialogueManager(
        ontology_loader=loader,
        slot_filler=filler,
        branch_selector=branch_selector,
        completion_policy=completion,
    )


def test_proxy_mode_marks_answered_by_proxy():
    manager = make_manager()
    manager.start_session("proxy-1", proxy_mode=True)

    result = manager.process_turn(
        "proxy-1",
        text_english="The patient has chest pain.",
    )

    assert result["slots_filled"]
    assert result["slots_filled"][0]["answered_by"] == "proxy"


def test_proxy_mode_can_be_disabled():
    manager = make_manager()
    manager.start_session("proxy-2", proxy_mode=True)

    manager.set_proxy_mode("proxy-2", False)

    result = manager.process_turn(
        "proxy-2",
        text_english="The patient has chest pain.",
    )

    assert result["slots_filled"]
    assert result["slots_filled"][0]["answered_by"] == "self"


def test_proxy_touch_answer_preserves_proxy_attribution():
    manager = make_manager()
    manager.start_session("proxy-3", proxy_mode=True)

    result = manager.process_turn(
        "proxy-3",
        touch_selection="Yes",
        input_mode="touch",
    )

    assert result["slots_filled"]
    assert result["slots_filled"][0]["answered_by"] == "proxy"
    assert result["slots_filled"][0]["input_mode"] == "touch"


def test_proxy_answer_still_triggers_red_flag():
    manager = make_manager()
    manager.start_session("proxy-4", proxy_mode=True)

    result = manager.process_turn(
        "proxy-4",
        text_english="The patient has chest pain.",
    )

    assert result["slots_filled"]
    assert result["slots_filled"][0]["answered_by"] == "proxy"

    state = manager.get_state("proxy-4")

    from services.m3_conversation.services.slot_filler import FilledSlot

    state.slots["socrates.site"] = FilledSlot(
        ontology_key="socrates.site",
        value="chest",
        confidence=1.0,
        answered_by="proxy",
        input_mode="voice",
    )

    state.slots["socrates.radiation"] = FilledSlot(
        ontology_key="socrates.radiation",
        value="left_arm",
        confidence=1.0,
        answered_by="proxy",
        input_mode="voice",
    )

    state.slots["socrates.onset"] = FilledSlot(
        ontology_key="socrates.onset",
        value=6,
        confidence=1.0,
        answered_by="proxy",
        input_mode="voice",
    )

    events = manager.red_flag_engine.evaluate(
        slots=manager._slots_for_red_flag_engine(state),
        utterance="The patient has chest pain.",
    )

    assert events
    assert any(event.rule_id == "CARDIAC-01" for event in events)

    assert all(
        slot["answered_by"] == "proxy"
        for slot in manager.get_slots("proxy-4")
        if slot["ontology_key"] in {
            "general.chief_complaint",
            "socrates.site",
            "socrates.radiation",
            "socrates.onset",
        }
    )
