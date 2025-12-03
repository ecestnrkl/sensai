import json
from pathlib import Path
from typing import Dict, List

from settings import PERSONA_RULES_PATH, SCENARIO_PATH


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


SCENARIOS: List[Dict[str, str]] = load_json(SCENARIO_PATH)
PERSONA_RULES: Dict[str, str] = load_json(PERSONA_RULES_PATH)

SCENARIO_LOOKUP = {item["id"]: item for item in SCENARIOS}
SCENARIO_LABEL_TO_ID = {
    f"{item['title']} ({item['id']})": item["id"] for item in SCENARIOS
}


def get_scenario_text(scenario_id: str, language: str) -> str:
    scenario = SCENARIO_LOOKUP.get(scenario_id)
    if not scenario:
        return ""
    if language == "de" and scenario.get("text_de"):
        return scenario["text_de"]
    return scenario.get("text", "")
