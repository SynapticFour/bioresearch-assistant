"""Custom Presidio recognizers for clinical texts (e.g. German patient IDs)."""

from presidio_analyzer import Pattern, PatternRecognizer

# Entity type for German patient/case identifiers
GERMAN_PATIENT_ID_ENTITY = "MEDICAL_RECORD_NUMBER"


class GermanPatientIDRecognizer(PatternRecognizer):
    """Recognizes German patient/case IDs as MEDICAL_RECORD_NUMBER."""

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="PATIENTEN_ID",
                regex=r"(?i)patienten?[-\s]?id\s*:?\s*\d{3,8}",
                score=0.9,
            ),
            Pattern(
                name="FALLNUMMER",
                regex=r"(?i)fallnummer\s*:?\s*\d{3,8}",
                score=0.9,
            ),
            Pattern(
                name="P_ID_SHORT",
                regex=r"\b[Pp]-\d{4,8}\b",
                score=0.85,
            ),
        ]
        super().__init__(
            supported_entity="MEDICAL_RECORD_NUMBER",
            patterns=patterns,
            supported_language="de",
            name="GermanPatientIDRecognizer",
        )


# Words that must not be tagged as PERSON (filtered in service after analysis)
GERMAN_PERSON_DENY_SET = frozenset(
    [
        "keine",
        "daten",
        "hier",
        "der",
        "die",
        "das",
        "und",
        "oder",
        "nicht",
        "mit",
        "von",
        "für",
    ]
)
