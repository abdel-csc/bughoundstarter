# BugHound Mini Model Card (Reflection)

Fill this out after you run BugHound in **both** modes (Heuristic and Gemini).

---

## 1) What is this system?

**Name:** BugHound
**Purpose:** Analyze a Python snippet, propose a fix, and run reliability checks before suggesting whether the fix should be auto-applied.
**Intended users:** Students learning agentic workflows and AI reliability concepts.

---

## 2) How does it work?

BugHound runs a five-step agentic loop. First, it **plans** by logging that it is about to scan the code. Then it **analyzes** the code for issues, either using pattern matching in heuristic mode or sending the code to Gemini and parsing the JSON response. Next it **acts** by proposing a fix, again either heuristically or via Gemini. Then it **tests** the fix by running it through the risk assessor, which scores the change and flags specific concerns. Finally it **reflects** by deciding whether the fix is safe enough to auto-apply or whether a human should review it first.

In heuristic mode, both analysis and fixing are done with regex and string matching locally with no API calls. In Gemini mode, the model handles analysis and fix generation, but the risk assessment always runs locally regardless of mode.

---

## 3) Inputs and outputs

**Inputs:**
- Short Python scripts with print statements, bare except blocks, and TODO comments
- Functions with multiple issues mixed together (mixed_issues.py)
- A function with 20 consecutive print statements to test guardrail behavior

**Outputs:**
- Detected issues: Code Quality (print statements), Reliability (bare except), Maintainability (TODO comments)
- Proposed fixes: print replaced with logging.info, bare except replaced with except Exception as e
- Risk reports ranged from MEDIUM (score 45, single low issue) to HIGH (score 0, multiple stacked deductions)

---

## 4) Reliability and safety rules

**Rule 1: High severity issue deducts 40 points from the score**
This check matters because high severity issues like bare excepts can silently swallow exceptions and hide real failures in production code. A false positive: any bare except gets flagged equally, even in legacy scripts where broad exception handling is intentional. A false negative: if the issue is labeled "Medium" when it should be "High," the deduction is only 20 points and the agent may underestimate the actual risk.

**Rule 2: Return statement removal deducts 30 points**
This check matters because removing a return changes a function's behavior, turning a value-returning function into one that implicitly returns None. A false positive: if the fix rewrites the logic so a return is no longer needed (such as raising an exception instead), this rule still fires even though the behavior is preserved. A false negative: if the fix rewrites the return as a different expression, the string "return" is still present and the rule does not catch the change.

---

## 5) Observed failure modes

**1. MockClient bypassing the offline check**
Input: any code snippet with MockClient passed as the client.
What went wrong: the original `_can_call_llm()` returned True for MockClient because it has a `complete` method. The agent tried to use it as a real LLM, got back non-JSON, logged a fallback, and then ran heuristics anyway. The fix should have been heuristics from the start. This was fixed by checking the client class name directly.

**2. Risk score and level inconsistency on mixed_issues.py**
Input: mixed_issues.py with print, bare except, and TODO.
What went wrong: the score stacked deductions down to 0 but the UI still showed the numeric score as 0 next to level HIGH. This looks like a scoring bug to a user who does not understand the clamping logic. A score of 0 reads as "no score computed" rather than "maximum deductions applied."

---

## 6) Heuristic vs Gemini comparison

Since testing was done in heuristic mode only (no API key), this comparison is based on the system design rather than live Gemini output.

Heuristics consistently caught print statements, bare excepts, and TODO comments across every input. These are reliable because they are simple string and regex checks with no ambiguity. Gemini would be expected to detect a broader range of issues such as undefined variables, type mismatches, and logic errors that heuristics cannot see. However, Gemini introduces parsing risk. Say for instance the model returns extra text or malformed JSON, the agent falls back to heuristics anyway, making the Gemini path less predictable. The risk scorer behaved consistently across both modes since it runs locally regardless of which analyzer was used.

---

## 7) Human-in-the-loop decision

**Scenario:** A function with a bare except wrapping 30 lines of business logic. The fix modifies the exception handler but the surrounding logic is complex enough that subtle control flow changes could break behavior in ways the risk assessor cannot detect.

**Trigger:** Block auto-fix when the number of print statements or substitutions being replaced exceeds 5, or when a high severity issue is present alongside structural changes.

**Where to implement it:** The risk assessor is the right place since it already centralizes all safety decisions. Adding it to the agent workflow would scatter the logic and make it harder to test in isolation.

**Message to show the user:** "This fix affects too many locations or modifies high-risk patterns. Please review the diff manually before applying."

---

## 8) Improvement idea

Add a check in `_heuristic_analyze` that flags functions longer than 20 lines with no docstring. Long undocumented functions are a maintainability risk that the current heuristics miss entirely. This check would be cheap to implement, fully offline, and unlikely to produce false positives on well-structured code. It would also give BugHound something meaningful to flag on inputs that currently come back clean, making the tool more useful on real codebases rather than only these basic examples. I feel like students will be able to use this project as a baseline for debugging with AI moving forward.