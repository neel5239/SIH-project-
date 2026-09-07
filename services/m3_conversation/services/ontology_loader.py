from pathlib import Path
from typing import Any

import yaml


class OntologyLoader:
    """Loads M3 dialogue definitions from YAML ontology files."""

    def __init__(self, ontology_dir: str | Path | None = None):
        if ontology_dir is None:
            ontology_dir = Path(__file__).resolve().parent.parent / "ontology"

        self.ontology_dir = Path(ontology_dir)
        self._questions: list[dict[str, Any]] = []
        self._questions_by_id: dict[str, dict[str, Any]] = {}

    def load(self) -> list[dict[str, Any]]:
        """Load all YAML ontology files."""

        if not self.ontology_dir.exists():
            raise FileNotFoundError(
                f"Ontology directory does not exist: {self.ontology_dir}"
            )

        questions: list[dict[str, Any]] = []

        for path in sorted(self.ontology_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}

            file_questions = data.get("questions", [])

            if not isinstance(file_questions, list):
                raise ValueError(
                    f"'questions' must be a list in {path}"
                )

            for question in file_questions:
                self._validate_question(question, path)
                questions.append(question)

        self._questions = questions
        self._questions_by_id = {
            question["id"]: question
            for question in questions
        }

        return list(self._questions)

    def get_all_questions(self) -> list[dict[str, Any]]:
        if not self._questions:
            self.load()

        return list(self._questions)

    def get_question(self, question_id: str) -> dict[str, Any] | None:
        if not self._questions:
            self.load()

        return self._questions_by_id.get(question_id)

    def get_questions_for_section(
        self,
        section: str,
    ) -> list[dict[str, Any]]:
        if not self._questions:
            self.load()

        return [
            question
            for question in self._questions
            if question.get("section") == section
        ]

    @staticmethod
    def _validate_question(
        question: Any,
        source_path: Path,
    ) -> None:
        if not isinstance(question, dict):
            raise ValueError(
                f"Question must be an object in {source_path}"
            )

        required_fields = [
            "id",
            "section",
            "text_en",
            "value_type",
            "priority",
            "mandatory",
        ]

        for field in required_fields:
            if field not in question:
                raise ValueError(
                    f"Question in {source_path} is missing '{field}'"
                )

        if not isinstance(question["id"], str):
            raise ValueError(
                f"Question id must be a string in {source_path}"
            )

        if not isinstance(question["text_en"], str):
            raise ValueError(
                f"text_en must be a string for {question['id']}"
            )