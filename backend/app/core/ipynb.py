"""nbformat v4 helpers for JupyterLite-class compute notebooks (no server kernel)."""

from __future__ import annotations

import json

STARTER_PHENOPACKET_IPYNB = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (Pyodide)",
            "language": "python",
            "name": "python",
        },
        "language_info": {"name": "python"},
        "bra": {
            "kind": "jupyterlite-class",
            "note": "Runs in the browser. No DATABASE_URL. BLAST/WES stay BRA APIs.",
        },
    },
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Phenopacket JSON (browser)\n",
                "\n",
                "This notebook runs in the SPA via Pyodide. ",
                "It cannot see BRA database credentials. ",
                "Use BRA HTTP APIs for BLAST/WES — do not paste connection strings here.\n",
            ],
        },
        {
            "cell_type": "code",
            "metadata": {},
            "execution_count": None,
            "outputs": [],
            "source": [
                "import json\n",
                "packet = {\n",
                '    "id": "example-subject-1",\n',
                '    "subject": {"id": "P123", "sex": "FEMALE"},\n',
                '    "phenotypicFeatures": [{"type": {"id": "HP:0001250", "label": "Seizure"}}],\n',
                "}\n",
                "print(json.dumps(packet, indent=2))\n",
            ],
        },
    ],
}


def starter_ipynb_json() -> str:
    return json.dumps(STARTER_PHENOPACKET_IPYNB, indent=2)


def validate_ipynb(content: str) -> None:
    """Raise ValueError if content is not a nbformat v4 notebook."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError("ipynb content must be JSON") from e
    if not isinstance(data, dict):
        raise ValueError("ipynb content must be a JSON object")
    if data.get("nbformat") != 4:
        raise ValueError("ipynb nbformat must be 4")
    cells = data.get("cells")
    if not isinstance(cells, list):
        raise ValueError("ipynb must have a cells array")
