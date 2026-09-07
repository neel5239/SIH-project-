from services.m3_conversation.services.ontology_loader import OntologyLoader
def test_ontology_loads_questions():
    loader = OntologyLoader()

    questions = loader.load()

    assert len(questions) == 85

    ids = {
        question["id"]
        for question in questions
    }

    expected_ids = {
        # ============================================================
        # General / HPI
        # ============================================================
        "general.chief_complaint",
        "hpi.duration",
        "hpi.severity",
        "hpi.onset",
        "hpi.location",
        "hpi.character",
        "hpi.aggravating_factors",
        "hpi.relieving_factors",
        "hpi.associated_symptoms",
        "general.past_medical_history",

        # ============================================================
        # SOCRATES
        # ============================================================
        "socrates.site",
        "socrates.onset",
        "socrates.character",
        "socrates.radiation",
        "socrates.associated_symptoms",
        "socrates.timing",
        "socrates.exacerbating",
        "socrates.severity",

        # ============================================================
        # Cardiac
        # ============================================================
        "systems.cardiac.chest_pressure",
        "systems.cardiac.palpitations",
        "systems.cardiac.breathlessness",

        # ============================================================
        # Respiratory
        # ============================================================
        "systems.respiratory.cough",
        "systems.respiratory.sputum",
        "systems.respiratory.wheezing",

        # ============================================================
        # Gastrointestinal
        # ============================================================
        "systems.gi.nausea",
        "systems.gi.vomiting",
        "systems.gi.bowel_change",

        # ============================================================
        # Neurological
        # ============================================================
        "systems.neuro.dizziness",
        "systems.neuro.weakness",
        "systems.neuro.vision",

        # ============================================================
        # Musculoskeletal
        # ============================================================
        "systems.msk.swelling",
        "systems.msk.movement",
        "systems.msk.stiffness",

        # ============================================================
        # General ROS
        # ============================================================
        "ros.general.fever",
        "ros.general.fatigue",

        # ============================================================
        # Cardiovascular ROS
        # ============================================================
        "ros.cardiovascular.chest_discomfort",
        "ros.cardiovascular.palpitations",
        "ros.cardiovascular.leg_swelling",

        # ============================================================
        # Respiratory ROS
        # ============================================================
        "ros.respiratory.cough",
        "ros.respiratory.breathlessness",
        "ros.respiratory.wheezing",

        # ============================================================
        # Gastrointestinal ROS
        # ============================================================
        "ros.gastrointestinal.nausea",
        "ros.gastrointestinal.bowel_change",
        "ros.gastrointestinal.appetite",

        # ============================================================
        # Neurological ROS
        # ============================================================
        "ros.neurological.headache",
        "ros.neurological.dizziness",
        "ros.neurological.numbness",

        # ============================================================
        # Musculoskeletal ROS
        # ============================================================
        "ros.musculoskeletal.joint_pain",
        "ros.musculoskeletal.stiffness",
        "ros.musculoskeletal.swelling",

        # ============================================================
        # AYUSH - Prakriti
        # ============================================================
        "ayush.prakriti.dosha_tendency",

        # ============================================================
        # AYUSH - Vikriti
        # ============================================================
        "ayush.vikriti.current_dosha_change",
        "ayush.vikriti.symptom_pattern",

        # ============================================================
        # AYUSH - Agni
        # ============================================================
        "ayush.agni.appetite",
        "ayush.agni.digestion",

        # ============================================================
        # AYUSH - Koshtha
        # ============================================================
        "ayush.koshtha.bowel_pattern",

        # ============================================================
        # AYUSH - Ahara / Vihara
        # ============================================================
        "ayush.ahara_vihara.diet",
        "ayush.ahara_vihara.hydration",
        "ayush.ahara_vihara.sleep",
        "ayush.ahara_vihara.activity",

        # ============================================================
        # AYUSH - Nidana
        # ============================================================
        "ayush.nidana.possible_triggers",
        "ayush.nidana.recent_changes",

        # ============================================================
        # AYUSH - Samprapti
        # ============================================================
        "ayush.samprapti.progression",
        "ayush.samprapti.associated_pattern",

        # ============================================================
        # AYUSH - Trividha Pariksha
        # ============================================================
        "ayush.trividha.darshana",
        "ayush.trividha.prashna",
        "ayush.trividha.sparshana",

        # ============================================================
        # AYUSH - Ashtavidha Pariksha
        # ============================================================
        "ayush.ashtavidha.nadi",
        "ayush.ashtavidha.mutra",
        "ayush.ashtavidha.mala",
        "ayush.ashtavidha.jihva",
        "ayush.ashtavidha.shabda",
        "ayush.ashtavidha.sparsha",
        "ayush.ashtavidha.drishti",
        "ayush.ashtavidha.akriti",

        # ============================================================
        # AYUSH - Dashavidha Pariksha
        # ============================================================
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
    }

    assert ids == expected_ids