import re
from dataclasses import dataclass


@dataclass
class MaskingResult:
    """
    Result of protected-term masking.

    masked_text:
        Text sent to the translation provider.

    protected_terms:
        Mapping between placeholders and their original terms.
    """

    masked_text: str
    protected_terms: dict[str, str]


class ProtectedTermMasker:
    """
    Protects important terms from being modified by translation.

    Example:

        "Take 500 mg paracetamol"

    becomes something like:

        "Take 500 mg __PROTECTED_TERM_0__"

    The original term can then be restored after translation.
    """

    DEFAULT_TERMS = [
        "paracetamol",
        "acetaminophen",
        "ibuprofen",
        "metformin",
        "insulin",
        "ayurveda",
        "ayurvedic",
        "siddha",
        "unani",
        "homeopathy",
    ]

    def __init__(self, protected_terms: list[str] | None = None):
        terms = protected_terms or self.DEFAULT_TERMS

        # Longest terms first prevents shorter terms from matching
        # inside longer protected terms.
        self.protected_terms = sorted(
            set(terms),
            key=len,
            reverse=True,
        )

    def mask(self, text: str) -> MaskingResult:
        """
        Replace protected terms with stable placeholders.
        """

        if not text.strip():
            return MaskingResult(
                masked_text=text,
                protected_terms={},
            )

        masked_text = text
        replacements: dict[str, str] = {}

        for index, term in enumerate(self.protected_terms):
            pattern = re.compile(
                rf"\b{re.escape(term)}\b",
                re.IGNORECASE,
            )

            if pattern.search(masked_text):
                placeholder = f"__PROTECTED_TERM_{index}__"

                masked_text = pattern.sub(
                    placeholder,
                    masked_text,
                )

                replacements[placeholder] = term

        return MaskingResult(
            masked_text=masked_text,
            protected_terms=replacements,
        )

    def unmask(
        self,
        text: str,
        protected_terms: dict[str, str],
    ) -> str:
        """
        Restore the original protected terms.
        """

        restored_text = text

        for placeholder, original_term in protected_terms.items():
            restored_text = restored_text.replace(
                placeholder,
                original_term,
            )

        return restored_text