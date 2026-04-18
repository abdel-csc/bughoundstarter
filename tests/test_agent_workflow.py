from bughound_agent import BugHoundAgent
from llm_client import MockClient


def test_workflow_runs_in_offline_mode_and_returns_shape():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)
    assert isinstance(result, dict)
    assert "issues" in result
    assert "fixed_code" in result
    assert "risk" in result
    assert "logs" in result
    assert isinstance(result["issues"], list)
    assert isinstance(result["fixed_code"], str)
    assert isinstance(result["risk"], dict)
    assert isinstance(result["logs"], list)
    assert len(result["logs"]) > 0


def test_offline_mode_detects_print_issue():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)
    assert any(issue.get("type") ==
               "Code Quality" for issue in result["issues"])


def test_offline_mode_proposes_logging_fix_for_print():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)
    fixed = result["fixed_code"]
    assert "logging" in fixed
    assert "logging.info(" in fixed


def test_mock_client_uses_heuristics_directly():
    # After our fix, MockClient is blocked from LLM path entirely
    # so the agent should go straight to heuristic analyzer
    agent = BugHoundAgent(client=MockClient())
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)
    assert any(issue.get("type") ==
               "Code Quality" for issue in result["issues"])
    assert any("offline mode" in entry.get("message", "")
               for entry in result["logs"])


def test_no_autofix_when_diff_is_too_large():
    # Many substitutions should block auto-fix even if line count barely changes
    agent = BugHoundAgent(client=None)
    lines = ["def f():"]
    for i in range(20):
        lines.append(f"    print('line {i}')")
    lines.append("    return True")
    code = "\n".join(lines)
    result = agent.run(code)
    assert result["risk"]["should_autofix"] is False
    assert any(
        "Too many substitutions" in r for r in result["risk"]["reasons"])
