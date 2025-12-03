from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
SCENARIO_PATH = BASE_DIR / "scenarios.json"
PERSONA_RULES_PATH = BASE_DIR / "persona_rules.json"
RESULTS_PATH = BASE_DIR / "results.csv"
TMP_DIR = BASE_DIR / "tmp_audio"
TMP_DIR.mkdir(exist_ok=True)

# Defaults
DEFAULT_ENDPOINT = "http://localhost:11434"
DEFAULT_MODEL = "llama2:7b-chat"
LANG_CHOICES = ["de", "en"]

# LLM parameters
MAX_GENERATION_TOKENS = 90
DEFAULT_TEMPERATURE = 0.6
DEFAULT_TOP_P = 0.9
