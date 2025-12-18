import json
from pathlib import Path
from typing import Any, Dict, List, Union

from settings import PERSONA_RULES_PATH, SCENARIO_PATH


def load_json(path: Path) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


SCENARIOS: List[Dict[str, Any]] = load_json(SCENARIO_PATH)  # type: ignore[assignment]
PERSONA_RULES: Dict[str, Any] = load_json(PERSONA_RULES_PATH)  # type: ignore[assignment]

SCENARIO_LOOKUP: Dict[str, Dict[str, Any]] = {item["id"]: item for item in SCENARIOS}
SCENARIO_LABEL_TO_ID = {
    f"{item['title']} ({item['id']})": item["id"] for item in SCENARIOS
}


def get_scenario_text(scenario_id: str, language: str) -> str:
    scenario = SCENARIO_LOOKUP.get(scenario_id)
    if not scenario:
        return ""
    if language == "de":
        text_de = scenario.get("text_de")
        if text_de:
            return str(text_de)
    text = scenario.get("text", "")
    return str(text)
