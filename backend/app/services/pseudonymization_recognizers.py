"""Custom Presidio recognizers for clinical texts (e.g. German patient IDs)."""

from presidio_analyzer import Pattern, PatternRecognizer

# Entity type for German patient/case identifiers
GERMAN_PATIENT_ID_ENTITY = "MEDICAL_RECORD_NUMBER"

DEFAULT_PATIENT_ID_PATTERNS = [
    Pattern(
        name="PATIENTEN_ID",
        regex=r"(?i)patienten?[-\s]?(?:id|nr|nummer)\s*:?\s*[\w-]{3,15}",
        score=0.9,
    ),
    Pattern(
        name="FALLNUMMER",
        regex=r"(?i)fallnummer\s*:?\s*[\w-]{3,15}",
        score=0.9,
    ),
    Pattern(
        name="P_ID_SHORT",
        regex=r"\b[Pp]-\d{4,8}\b",
        score=0.85,
    ),
    Pattern(
        name="LAB_ID",
        # Format: L-2024-98765
        regex=r"\b[A-Z]-\d{4}-\d{4,8}\b",
        score=0.85,
    ),
    Pattern(
        name="PATIENTENNUMMER_LABEL",
        regex=r"(?i)patientennummer\s*:?\s*[\w-]{3,15}",
        score=0.90,
    ),
]


class GermanPatientIDRecognizer(PatternRecognizer):
    """Recognizes German patient/case IDs."""

    def __init__(
        self,
        extra_patterns: list[Pattern] | None = None,
    ) -> None:
        patterns = list(DEFAULT_PATIENT_ID_PATTERNS)
        if extra_patterns:
            patterns.extend(extra_patterns)
        super().__init__(
            supported_entity="MEDICAL_RECORD_NUMBER",
            patterns=patterns,
            supported_language="de",
            name="GermanPatientIDRecognizer",
        )


class GermanDateRecognizer(PatternRecognizer):
    """Erkennt deutsche Datumsformate: 15.03.1970, 22.01.2024"""

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="DE_DATE_DMY",
                regex=r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b",
                score=0.85,
            ),
            Pattern(
                name="DE_DATE_WRITTEN",
                regex=(
                    r"\b\d{1,2}\.\s?(?:Januar|Februar|März|April|Mai|Juni|"
                    r"Juli|August|September|Oktober|November|Dezember)"
                    r"\s?\d{2,4}\b"
                ),
                score=0.90,
            ),
        ]
        super().__init__(
            supported_entity="DATE_TIME",
            patterns=patterns,
            supported_language="de",
            name="GermanDateRecognizer",
        )


class GermanPhoneRecognizer(PatternRecognizer):
    """Erkennt deutsche Telefonnummern: 0711-123456, +49 711 123456"""

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="DE_PHONE_LOCAL",
                regex=r"\b0\d{2,5}[\s\-/]\d{3,8}\b",
                score=0.85,
            ),
            Pattern(
                name="DE_PHONE_INTL",
                regex=r"\+49[\s\-]?\d{2,5}[\s\-]?\d{3,8}\b",
                score=0.90,
            ),
        ]
        super().__init__(
            supported_entity="PHONE_NUMBER",
            patterns=patterns,
            supported_language="de",
            name="GermanPhoneRecognizer",
        )


class GermanMedicalLicenseRecognizer(PatternRecognizer):
    """Erkennt Arzt-Nummern: Ärztin 4711, Arzt-Nr 12345"""

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="DE_ARZT_NR",
                regex=r"(?:Ärztin|Arzt(?:-Nr)?\.?)\s+\d{4,7}\b",
                score=0.85,
            ),
            Pattern(
                name="DE_LANR",
                regex=r"\bLANR\s*:?\s*\d{9}\b",
                score=0.95,
            ),
        ]
        super().__init__(
            supported_entity="MEDICAL_LICENSE",
            patterns=patterns,
            supported_language="de",
            name="GermanMedicalLicenseRecognizer",
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
