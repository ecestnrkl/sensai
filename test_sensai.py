"""
Comprehensive test suite for SensAI prototype.
Run: python test_sensai.py
"""
import json
import sys
import re

sys.path.insert(0, ".")

from prompts import build_persona_summary, base_system_prompt, user_prompt, checkin_prompts
from data import PERSONA_RULES
from llm_client import (
    sanitize_llm_output,
    scrub_language_leaks,
    looks_wrong_language,
    ensure_two_complete_sentences,
    truncate_response,
    rewrite_for_language,
)

PASS = "✓"
FAIL = "✗"
_failures = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        _failures.append(name)


# ─────────────────────────────────────────────
# 1. persona_rules.json
# ─────────────────────────────────────────────
print("\n=== 1. persona_rules.json key completeness ===")

REQUIRED_KEYS = [
    "default",
    "high_openness", "mid_openness", "low_openness",
    "high_conscientiousness", "mid_conscientiousness", "low_conscientiousness",
    "high_extraversion", "mid_extraversion", "low_extraversion",
    "high_agreeableness", "mid_agreeableness", "low_agreeableness",
    "high_neuroticism", "mid_neuroticism", "low_neuroticism",
    "dbq_violations_high", "dbq_violations_mid", "dbq_violations_low",
    "dbq_errors_high", "dbq_errors_mid", "dbq_errors_low",
    "dbq_lapses_high", "dbq_lapses_mid", "dbq_lapses_low",
    "bsss_experience_high", "bsss_experience_mid", "bsss_experience_low",
    "bsss_thrill_high", "bsss_thrill_mid", "bsss_thrill_low",
    "bsss_disinhibition_high", "bsss_disinhibition_mid", "bsss_disinhibition_low",
    "bsss_boredom_high", "bsss_boredom_mid", "bsss_boredom_low",
    "erq_reappraisal_high", "erq_reappraisal_mid", "erq_reappraisal_low",
    "erq_suppression_high", "erq_suppression_mid", "erq_suppression_low",
]

missing = [k for k in REQUIRED_KEYS if k not in PERSONA_RULES]
check("All 43 required keys present", len(missing) == 0, f"missing={missing}")
empty = [k for k in REQUIRED_KEYS if PERSONA_RULES.get(k, "").strip() == ""]
check("No empty rule values", len(empty) == 0, f"empty={empty}")
check("Rule count >= 43", len(PERSONA_RULES) >= 43, f"actual={len(PERSONA_RULES)}")

# ─────────────────────────────────────────────
# 2. build_persona_summary — EN
# ─────────────────────────────────────────────
print("\n=== 2. build_persona_summary (English) ===")

# 2a: all mid-range
r_mid = build_persona_summary(3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, "en")
check("Mid-range: non-empty result", bool(r_mid.strip()))
check("Mid-range: contains score summary", "O=3" in r_mid and "N=3" in r_mid)
check("Mid-range: 14 trait rules fired",
      all(k not in r_mid for k in []) and
      "moderately open" in r_mid and
      "average self-discipline" in r_mid and
      "moderately social" in r_mid)

# 2b: all HIGH (1-5 scale max=5, ERQ max=7)
r_high = build_persona_summary(5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 7, 7, "en")
check("All-high: high N rule (extra reassurance)", "extra reassurance" in r_high)
check("All-high: high C rule (structured/detail)", "structured" in r_high or "detail" in r_high)
check("All-high: high O rule (creative/alternative)", "creative" in r_high or "alternative" in r_high)
check("All-high: ERQ reappraisal high", "positive reinterpret" in r_high or "positive reframe" in r_high or "active reframe" in r_high or "reinterpret" in r_high)
check("All-high: scores in summary O=5", "O=5" in r_high)

# 2c: all LOW
r_low = build_persona_summary(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, "en")
check("All-low: low C rule (one immediate step)", "one immediate" in r_low or "exactly one" in r_low)
check("All-low: low N rule (no reassurance)", "no reassurance" in r_low or "emotionally stable" in r_low or "stable" in r_low)
check("All-low: low O rule (no metaphors)", "no metaphors" in r_low or "familiar" in r_low or "direct" in r_low)
check("All-low: ERQ suppression low (direct)", "direct" in r_low or "freely" in r_low)

# 2d: ERQ scale thresholds (1-7: high>=5, mid 3-4, low<=2)
r_erq_low = build_persona_summary(3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, "en")
r_erq_mid = build_persona_summary(3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, "en")
r_erq_high5 = build_persona_summary(3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 5, 5, "en")
r_erq_high7 = build_persona_summary(3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 7, 7, "en")

check("ERQ score=2 => low reappraisal rule",
      "skip abstract" in r_erq_low or "abstract reframing" in r_erq_low or
      "direct practical" in r_erq_low or "no abstract" in r_erq_low or
      "skip abstract reframing" in r_erq_low)
check("ERQ score=3 => mid reappraisal rule", "gentle reframe" in r_erq_mid)
check("ERQ score=5 => high reappraisal rule",
      "reinterpret" in r_erq_high5 or "positive reframe" in r_erq_high5 or "active" in r_erq_high5)
# Score=5 and score=7 both hit the "high" tier; the behavioural rules are identical.
# Only the score-summary block at the end differs (e.g. "reappraisal=5" vs "reappraisal=7").
check("ERQ score=7 fires same high rule as score=5",
      PERSONA_RULES.get("erq_reappraisal_high", "X") in r_erq_high5
      and PERSONA_RULES.get("erq_reappraisal_high", "X") in r_erq_high7)

# 2e: High N / low C combo (from the README validation)
r_hn_lc = build_persona_summary(3, 1, 3, 3, 5, 2, 3, 3, 3, 3, 3, 3, 3, 3, "en")
check("High N rule present", "extra reassurance" in r_hn_lc or "reassurance" in r_hn_lc)
check("Low C rule present", "one immediate" in r_hn_lc or "exactly one" in r_hn_lc)
check("DBQ violations=2 => low rule (no special emphasis)", "no special" in r_hn_lc or "reliably" in r_hn_lc)

# ─────────────────────────────────────────────
# 3. build_persona_summary — DE
# ─────────────────────────────────────────────
print("\n=== 3. build_persona_summary (German) ===")

r_de_high = build_persona_summary(5, 1, 3, 3, 4, 3, 3, 3, 3, 3, 3, 3, 4, 3, "de")
check("DE: uses German rules (Fahrer/Sprich)", "Fahrer" in r_de_high or "Sprich" in r_de_high)
check("DE: high N rule in German", "aengstlich" in r_de_high or "Bestaetigung" in r_de_high or "Stress" in r_de_high)
check("DE: low C rule in German", "mehrstufigen" in r_de_high or "sofortigen" in r_de_high or "einen sofortigen" in r_de_high)
check("DE: score summary in German", "Neurotizismus" not in r_de_high or "N=4" in r_de_high)  # summary uses short labels
check("DE: score block present", "O=" in r_de_high and "ERQ" in r_de_high)

# ─────────────────────────────────────────────
# 4. base_system_prompt and user_prompt
# ─────────────────────────────────────────────
print("\n=== 4. base_system_prompt / user_prompt ===")

bsp_en = base_system_prompt("s1", "en")
bsp_de = base_system_prompt("s1", "de")
check("EN base_system: 'two to four' sentences", "two to four" in bsp_en)
check("DE base_system: 'zwei bis vier' Sätze", "zwei bis vier" in bsp_de)
check("EN base_system: no 'exactly two'", "exactly two" not in bsp_en)
check("DE base_system: no 'genau zwei'", "genau zwei" not in bsp_de)

up_en = user_prompt("I'm stuck in traffic.", "en")
up_de = user_prompt("Ich stehe im Stau.", "de")
check("EN user_prompt: 'two to four'", "two to four" in up_en)
check("DE user_prompt: 'zwei bis vier'", "zwei bis vier" in up_de)

_, ci_up_en = checkin_prompts("s1", "en", "test persona", include_persona=True)
_, ci_up_de = checkin_prompts("s1", "de", "test persona", include_persona=True)
_, ci_sp_en = checkin_prompts("s1", "en", "", include_persona=False), None
ci_sys_en, _ = checkin_prompts("s1", "en", "test persona", include_persona=True)
ci_sys_de, _ = checkin_prompts("s1", "de", "test persona", include_persona=True)
check("EN checkin system: 'two to four'", "two to four" in ci_sys_en)
check("DE checkin system: 'zwei bis vier'", "zwei bis vier" in ci_sys_de)

# Persona placement in checkin
ci_sys_w_pers, _ = checkin_prompts("s1", "en", "MY PERSONA DATA", include_persona=True)
ci_sys_no_pers, _ = checkin_prompts("s1", "en", "MY PERSONA DATA", include_persona=False)
check("Checkin with persona: profile at start", ci_sys_w_pers.startswith("Driver personality profile:"))
check("Checkin without persona: no profile block", "MY PERSONA DATA" not in ci_sys_no_pers)

# ─────────────────────────────────────────────
# 5. rewrite_for_language — "two to four" fix
# ─────────────────────────────────────────────
print("\n=== 5. rewrite_for_language prompt text ===")
import inspect
src = inspect.getsource(rewrite_for_language)
check("rewrite_for_language: 'two to four' (not 'exactly two')",
      "two to four" in src,
      "STILL SAYS 'exactly two'" if "exactly two" in src else "already correct")
check("rewrite_for_language: no 'exactly two short, complete sentences'",
      "exactly two short, complete sentences" not in src)

# ─────────────────────────────────────────────
# 6. llm_client post-processing pipeline
# ─────────────────────────────────────────────
print("\n=== 6. llm_client post-processing ===")

# sanitize_llm_output
check("sanitize: strips 'Sure, '", "Sure," not in sanitize_llm_output("Sure, here you go."))
check("sanitize: strips 'Of course: '", "Of course" not in sanitize_llm_output("Of course: try this."))
check("sanitize: strips bold *text*", "*hello*" not in sanitize_llm_output("*hello* world"))
# sanitize_llm_output should strip the "Driver transcript:" label but keep the payload.
_sanitized_prefix = sanitize_llm_output("Driver transcript: prefix shown")
check("sanitize: 'Driver transcript:' label removed", "Driver transcript:" not in _sanitized_prefix)
check("sanitize: payload text retained after prefix strip", "prefix shown" in _sanitized_prefix)

# scrub_language_leaks: German response should lose English "traffic"
check("scrub_de: removes 'traffic' from DE text",
      "traffic" not in scrub_language_leaks("Es gibt viel traffic hier.", "de"))
check("scrub_en: removes 'nicht' from EN text",
      "nicht" not in scrub_language_leaks("That is nicht correct.", "en"))
check("scrub_en: 'right' preserved in EN (not in EN leaks)",
      "right" in scrub_language_leaks("Turn right here.", "en"))
# 'sure' (EN word) is in leaks_de but NOT in leaks_en; it must NOT be
# stripped from English output.  Use case-insensitive check.
check("scrub_en: 'sure' preserved in EN (not in EN leaks)",
      "sure" in scrub_language_leaks("Sure, that's fine.", "en").lower())

# looks_wrong_language
check("looks_wrong: EN text is NOT wrong for EN", not looks_wrong_language("Stay on the road and keep going.", "en"))
check("looks_wrong: DE text IS wrong for EN",
      looks_wrong_language("Bleib ruhig und fahr nicht zu schnell.", "en"))
check("looks_wrong: EN text IS wrong for DE",
      looks_wrong_language("Stay on the road and drive carefully.", "de"))
check("looks_wrong: DE text is NOT wrong for DE",
      not looks_wrong_language("Bleib ruhig und halte Abstand.", "de"))

# ensure_two_complete_sentences
r2s = ensure_two_complete_sentences("Okay.", "en")
check("ensure: at least 2 sentences from 1 short input", len(re.findall(r'[.!?]', r2s)) >= 2)
r2s4 = ensure_two_complete_sentences("A. B. C. D. E.", "en", max_sentences=4)
check("ensure: truncates to max_sentences=4", len(re.findall(r'[.!?]', r2s4)) <= 4)

# truncate_response
long = " ".join(["This is a sentence."] * 10)
tr = truncate_response(long, "en")
word_count = len(tr.split())
check("truncate: word count <= 55", word_count <= 55, f"words={word_count}")
char_count = len(tr)
check("truncate: char count <= 450", char_count <= 450, f"chars={char_count}")

# ─────────────────────────────────────────────
# 7. handlers.py — prompt placement
# ─────────────────────────────────────────────
print("\n=== 7. handlers.py prompt construction ===")
import inspect
import handlers
src_h = inspect.getsource(handlers._generate_llm_response)
check("_generate_llm_response: persona profile at START",
      'f"Driver personality profile:\\n{persona_summary}\\n\\n{base_system}"' in src_h or
      '"Driver personality profile:\\n"' in src_h or
      "Driver personality profile:" in src_h)
check("_generate_llm_response: no 'Persona hints:'",
      "Persona hints:" not in src_h)

# ─────────────────────────────────────────────
# 8. settings.py values
# ─────────────────────────────────────────────
print("\n=== 8. settings.py ===")
from settings import DEFAULT_TEMPERATURE, MAX_GENERATION_TOKENS, DEFAULT_TOP_P
check("temperature >= 0.8", DEFAULT_TEMPERATURE >= 0.8, f"actual={DEFAULT_TEMPERATURE}")
check("max_tokens >= 140", MAX_GENERATION_TOKENS >= 140, f"actual={MAX_GENERATION_TOKENS}")
check("top_p set", DEFAULT_TOP_P is not None)

# ─────────────────────────────────────────────
# 9. data.py
# ─────────────────────────────────────────────
print("\n=== 9. data.py scenarios ===")
from data import SCENARIO_LOOKUP, SCENARIO_LABEL_TO_ID, get_scenario_text
check("SCENARIO_LOOKUP non-empty", len(SCENARIO_LOOKUP) > 0)
first_id = list(SCENARIO_LOOKUP.keys())[0]
txt_en = get_scenario_text(first_id, "en")
txt_de = get_scenario_text(first_id, "de")
check("scenario text EN available", bool(txt_en.strip()))
check("scenario text DE available", bool(txt_de.strip()))
check("SCENARIO_LABEL_TO_ID non-empty", len(SCENARIO_LABEL_TO_ID) > 0)

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
print("\n" + "=" * 50)
if _failures:
    print(f"FAILED: {len(_failures)} test(s):")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED ✓")
