from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


@dataclass(frozen=True)
class DualCode:
    namaste_code: str
    namaste_term: str
    icd11_tm2_code: str
    icd11_tm2_term: str
    icd11_bio_code: str | None = None
    match_type: str = "exact"
    confidence: float = 1.0
    source: str = "curated_mapping"


class DualCodingService:
    """
    Conservative NAMASTE <-> ICD-11 TM2 mapper.

    Safety rules:
    - Never invent a code.
    - Exact/normalized matches are preferred.
    - Fuzzy matching is only accepted above the configured threshold.
    - An unsuccessful mapping returns None.
    """

    def __init__(
        self,
        mapping_path: str | Path | None = None,
        fuzzy_threshold: float = 0.90,
    ):
        if mapping_path is None:
            mapping_path = (
                Path(__file__).resolve().parents[1]
                / "ontology"
                / "namaste_icd11_map.csv"
            )

        self.mapping_path = Path(mapping_path)
        self.fuzzy_threshold = fuzzy_threshold
        self._entries = self._load_mapping()

    @staticmethod
    def _normalize(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9\\s-]", "", value)
        value = re.sub(r"\\s+", " ", value)
        return value

    def _load_mapping(self) -> list[DualCode]:
        if not self.mapping_path.exists():
            return []

        entries: list[DualCode] = []

        with self.mapping_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            required = {
                "namaste_code",
                "namaste_term",
                "icd11_tm2_code",
                "icd11_tm2_term",
                "icd11_bio_code",
            }

            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError(
                    "NAMASTE/ICD-11 mapping CSV has missing columns"
                )

            for row in reader:
                namaste_code = (row.get("namaste_code") or "").strip()
                namaste_term = (row.get("namaste_term") or "").strip()
                icd11_code = (row.get("icd11_tm2_code") or "").strip()
                icd11_term = (row.get("icd11_tm2_term") or "").strip()

                # Invalid/empty mappings are ignored rather than fabricated.
                if not (
                    namaste_code
                    and namaste_term
                    and icd11_code
                    and icd11_term
                ):
                    continue

                entries.append(
                    DualCode(
                        namaste_code=namaste_code,
                        namaste_term=namaste_term,
                        icd11_tm2_code=icd11_code,
                        icd11_tm2_term=icd11_term,
                        icd11_bio_code=(
                            (row.get("icd11_bio_code") or "").strip()
                            or None
                        ),
                    )
                )

        return entries

    def lookup(
        self,
        term: str,
    ) -> DualCode | None:
        """
        Map a NAMASTE term to ICD-11 TM2.

        Returns None if the service cannot establish a sufficiently
        reliable mapping.
        """
        if not isinstance(term, str):
            return None

        normalized = self._normalize(term)

        if not normalized:
            return None

        # 1. Exact normalized match.
        for entry in self._entries:
            if self._normalize(entry.namaste_term) == normalized:
                return entry

        # 2. Fuzzy match.
        best_entry: DualCode | None = None
        best_score = 0.0

        for entry in self._entries:
            candidate = self._normalize(entry.namaste_term)

            score = SequenceMatcher(
                None,
                normalized,
                candidate,
            ).ratio()

            if score > best_score:
                best_score = score
                best_entry = entry

        if (
            best_entry is not None
            and best_score >= self.fuzzy_threshold
        ):
            return DualCode(
                namaste_code=best_entry.namaste_code,
                namaste_term=best_entry.namaste_term,
                icd11_tm2_code=best_entry.icd11_tm2_code,
                icd11_tm2_term=best_entry.icd11_tm2_term,
                icd11_bio_code=best_entry.icd11_bio_code,
                match_type="fuzzy",
                confidence=round(best_score, 4),
                source=best_entry.source,
            )

        return None

    def lookup_code(
        self,
        namaste_code: str,
    ) -> DualCode | None:
        if not isinstance(namaste_code, str):
            return None

        normalized = namaste_code.strip().lower()

        for entry in self._entries:
            if entry.namaste_code.lower() == normalized:
                return entry

        return None

    def all_mappings(self) -> list[DualCode]:
        return list(self._entries)
