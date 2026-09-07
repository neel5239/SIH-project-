from typing import Any


class BranchSelector:
    """
    Phase 2 adaptive branch selector.

    Conversation order:

    1. General/HPI
    2. SOCRATES when indicated
    3. System-specific branch
    4. Remaining General/HPI
    5. Branch-specific ROS
    6. General ROS
    7. AYUSH assessment

    AYUSH questions are deliberately kept after the
    primary biomedical history so they cannot interrupt
    chief complaint, SOCRATES, system-specific flows,
    or ROS.
    """

    SOCRATES_KEYS = [
        "socrates.site",
        "socrates.onset",
        "socrates.character",
        "socrates.radiation",
        "socrates.associated_symptoms",
        "socrates.timing",
        "socrates.exacerbating",
        "socrates.severity",
    ]

    SOCRATES_TRIGGERS = [
        "pain",
        "ache",
        "aching",
        "discomfort",
        "headache",
        "chest pain",
        "stomach pain",
        "abdominal pain",
        "back pain",
        "joint pain",
        "body pain",
        "burning",
        "cramp",
        "cramping",
        "pressure",
        "tightness",
    ]

    SYSTEM_BRANCH_KEYS = {
        "cardiac": [
            "systems.cardiac.chest_pressure",
            "systems.cardiac.palpitations",
            "systems.cardiac.breathlessness",
        ],
        "respiratory": [
            "systems.respiratory.cough",
            "systems.respiratory.sputum",
            "systems.respiratory.wheezing",
        ],
        "gastrointestinal": [
            "systems.gi.nausea",
            "systems.gi.vomiting",
            "systems.gi.bowel_change",
        ],
        "neurological": [
            "systems.neuro.dizziness",
            "systems.neuro.weakness",
            "systems.neuro.vision",
        ],
        "musculoskeletal": [
            "systems.msk.swelling",
            "systems.msk.movement",
            "systems.msk.stiffness",
        ],
    }

    ROS_BRANCH_KEYS = {
        "cardiac": [
            "ros.cardiovascular.chest_discomfort",
            "ros.cardiovascular.palpitations",
            "ros.cardiovascular.leg_swelling",
        ],
        "respiratory": [
            "ros.respiratory.cough",
            "ros.respiratory.breathlessness",
            "ros.respiratory.wheezing",
        ],
        "gastrointestinal": [
            "ros.gastrointestinal.nausea",
            "ros.gastrointestinal.bowel_change",
            "ros.gastrointestinal.appetite",
        ],
        "neurological": [
            "ros.neurological.headache",
            "ros.neurological.dizziness",
            "ros.neurological.numbness",
        ],
        "musculoskeletal": [
            "ros.musculoskeletal.joint_pain",
            "ros.musculoskeletal.stiffness",
            "ros.musculoskeletal.swelling",
        ],
    }

    GENERAL_ROS_KEYS = [
        "ros.general.fever",
        "ros.general.fatigue",
    ]

    AYUSH_KEYS = [
        "ayush.prakriti.dosha_tendency",

        "ayush.vikriti.current_dosha_change",
        "ayush.vikriti.symptom_pattern",

        "ayush.agni.appetite",
        "ayush.agni.digestion",

        "ayush.koshtha.bowel_pattern",

        "ayush.ahara_vihara.diet",
        "ayush.ahara_vihara.hydration",
        "ayush.ahara_vihara.sleep",
        "ayush.ahara_vihara.activity",

        "ayush.nidana.possible_triggers",
        "ayush.nidana.recent_changes",

        "ayush.samprapti.progression",
        "ayush.samprapti.associated_pattern",

        "ayush.trividha.darshana",
        "ayush.trividha.prashna",
        "ayush.trividha.sparshana",

        "ayush.ashtavidha.nadi",
        "ayush.ashtavidha.mutra",
        "ayush.ashtavidha.mala",
        "ayush.ashtavidha.jihva",
        "ayush.ashtavidha.shabda",
        "ayush.ashtavidha.sparsha",
        "ayush.ashtavidha.drishti",
        "ayush.ashtavidha.akriti",

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

    def select_next(
        self,
        questions: list[dict[str, Any]],
        asked_keys: set[str],
        skipped_keys: set[str],
        slots: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:

        slots = slots or {}

        chief_complaint = self._get_chief_complaint(
            slots
        )

        # ---------------------------------
        # 1. GENERAL / HPI FIRST
        # ---------------------------------

        if not chief_complaint:
            for question in questions:
                key = question["id"]

                if key in asked_keys:
                    continue

                if key in skipped_keys:
                    continue

                if key in self.SOCRATES_KEYS:
                    continue

                if self._is_system_question(key):
                    continue

                if self._is_ros_question(key):
                    continue

                if self._is_ayush_question(key):
                    continue

                if not self._should_ask(
                    question,
                    slots,
                ):
                    continue

                return question

        # ---------------------------------
        # 2. SOCRATES
        # ---------------------------------

        if self._needs_socrates(
            chief_complaint
        ):
            question = self._select_from_keys(
                questions,
                self.SOCRATES_KEYS,
                asked_keys,
                skipped_keys,
                slots,
            )

            if question is not None:
                return question

        # ---------------------------------
        # 3. SYSTEM BRANCHES
        # ---------------------------------

        system_branches = self._get_system_branches(
            chief_complaint
        )

        for branch in system_branches:
            question = self._select_from_keys(
                questions,
                self.SYSTEM_BRANCH_KEYS[branch],
                asked_keys,
                skipped_keys,
                slots,
            )

            if question is not None:
                return question

        # ---------------------------------
        # 4. REMAINING GENERAL / HPI
        # ---------------------------------

        for question in questions:
            key = question["id"]

            if key in asked_keys:
                continue

            if key in skipped_keys:
                continue

            if key in self.SOCRATES_KEYS:
                continue

            if self._is_system_question(key):
                continue

            if self._is_ros_question(key):
                continue

            if self._is_ayush_question(key):
                continue

            if not self._should_ask(
                question,
                slots,
            ):
                continue

            return question

        # ---------------------------------
        # 5. BRANCH-SPECIFIC ROS
        # ---------------------------------

        for branch in system_branches:
            question = self._select_from_keys(
                questions,
                self.ROS_BRANCH_KEYS[branch],
                asked_keys,
                skipped_keys,
                slots,
            )

            if question is not None:
                return question

        # ---------------------------------
        # 6. GENERAL ROS
        # ---------------------------------

        question = self._select_from_keys(
            questions,
            self.GENERAL_ROS_KEYS,
            asked_keys,
            skipped_keys,
            slots,
        )

        if question is not None:
            return question

        # ---------------------------------
        # 7. AYUSH
        # ---------------------------------

        question = self._select_from_keys(
            questions,
            self.AYUSH_KEYS,
            asked_keys,
            skipped_keys,
            slots,
        )

        if question is not None:
            return question

        return None

    def _select_from_keys(
        self,
        questions: list[dict[str, Any]],
        allowed_keys: list[str],
        asked_keys: set[str],
        skipped_keys: set[str],
        slots: dict[str, Any],
    ) -> dict[str, Any] | None:

        for key in allowed_keys:
            if key in asked_keys:
                continue

            if key in skipped_keys:
                continue

            question = self._find_question(
                questions,
                key,
            )

            if question is None:
                continue

            if not self._should_ask(
                question,
                slots,
            ):
                continue

            return question

        return None

    @staticmethod
    def _find_question(
        questions: list[dict[str, Any]],
        question_id: str,
    ) -> dict[str, Any] | None:

        for question in questions:
            if question["id"] == question_id:
                return question

        return None

    @staticmethod
    def _is_system_question(
        question_id: str,
    ) -> bool:

        return question_id.startswith(
            "systems."
        )

    @staticmethod
    def _is_ros_question(
        question_id: str,
    ) -> bool:

        return question_id.startswith(
            "ros."
        )

    @staticmethod
    def _is_ayush_question(
        question_id: str,
    ) -> bool:

        return question_id.startswith(
            "ayush."
        )

    def _get_system_branches(
        self,
        chief_complaint: str,
    ) -> list[str]:

        if not chief_complaint:
            return []

        branches: list[str] = []

        chest_triggers = [
            "chest",
            "heart",
            "cardiac",
        ]

        respiratory_triggers = [
            "cough",
            "breath",
            "breathing",
            "shortness of breath",
            "wheezing",
            "asthma",
        ]

        abdominal_triggers = [
            "abdomen",
            "abdominal",
            "stomach",
            "belly",
            "gastric",
            "indigestion",
        ]

        neurological_triggers = [
            "headache",
            "head pain",
            "migraine",
            "dizziness",
            "vertigo",
            "numbness",
            "weakness",
            "seizure",
        ]

        musculoskeletal_triggers = [
            "joint",
            "joints",
            "knee",
            "shoulder",
            "elbow",
            "wrist",
            "ankle",
            "muscle",
            "back pain",
            "neck pain",
        ]

        if self._contains_any(
            chief_complaint,
            chest_triggers,
        ):
            branches.extend(
                [
                    "cardiac",
                    "respiratory",
                ]
            )

        elif self._contains_any(
            chief_complaint,
            abdominal_triggers,
        ):
            branches.append(
                "gastrointestinal"
            )

        elif self._contains_any(
            chief_complaint,
            neurological_triggers,
        ):
            branches.append(
                "neurological"
            )

        elif self._contains_any(
            chief_complaint,
            musculoskeletal_triggers,
        ):
            branches.append(
                "musculoskeletal"
            )

        elif self._contains_any(
            chief_complaint,
            respiratory_triggers,
        ):
            branches.append(
                "respiratory"
            )

        return branches

    @staticmethod
    def _contains_any(
        text: str,
        triggers: list[str],
    ) -> bool:

        return any(
            trigger in text
            for trigger in triggers
        )

    def _should_ask(
        self,
        question: dict[str, Any],
        slots: dict[str, Any],
    ) -> bool:

        conditions = question.get(
            "ask_if",
            [],
        )

        if not conditions:
            return True

        for condition in conditions:
            if not isinstance(
                condition,
                dict,
            ):
                continue

            if "slot_exists" in condition:
                slot_key = condition[
                    "slot_exists"
                ]

                if not self._slot_exists(
                    slots,
                    slot_key,
                ):
                    return False

            if "branch" in condition:
                branch = condition[
                    "branch"
                ]

                chief_complaint = (
                    self._get_chief_complaint(
                        slots
                    )
                )

                active_branches = (
                    self._get_system_branches(
                        chief_complaint
                    )
                )

                if branch not in active_branches:
                    return False

        return True

    @staticmethod
    def _slot_exists(
        slots: dict[str, Any],
        slot_key: str,
    ) -> bool:

        if slot_key not in slots:
            return False

        slot = slots[slot_key]

        if hasattr(slot, "value"):
            value = slot.value

        elif isinstance(slot, dict):
            value = slot.get(
                "value",
                None,
            )

        else:
            value = slot

        return (
            value is not None
            and value != ""
        )

    @staticmethod
    def _get_chief_complaint(
        slots: dict[str, Any],
    ) -> str:

        slot = slots.get(
            "general.chief_complaint"
        )

        if slot is None:
            return ""

        if hasattr(slot, "value"):
            value = slot.value

        elif isinstance(slot, dict):
            value = slot.get(
                "value",
                "",
            )

        else:
            value = slot

        if isinstance(value, dict):
            value = value.get(
                "raw_text",
                "",
            )

        return str(
            value or ""
        ).strip().lower()

    def _needs_socrates(
        self,
        chief_complaint: str,
    ) -> bool:

        if not chief_complaint:
            return False

        return any(
            trigger in chief_complaint
            for trigger in self.SOCRATES_TRIGGERS
        )