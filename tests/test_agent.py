from src.agent import RecommenderAgent


def test_agent_matches_a_clear_request_with_high_confidence():
    agent = RecommenderAgent()
    result = agent.run("upbeat pop for a workout")
    assert result.recommendations[0][0]["genre"] == "pop"
    assert result.passed is True
    assert result.confidence >= 0.65


def test_agent_self_corrects_with_a_retry_when_energy_is_unspecified():
    """'some jazz' gives no energy cue; the agent should re-center energy and
    need more than one attempt to reach a confident answer."""
    agent = RecommenderAgent()
    result = agent.run("some jazz")
    assert result.recommendations[0][0]["genre"] == "jazz"
    assert result.attempts >= 2          # it had to revise
    assert result.passed is True


def test_agent_handles_empty_input_without_crashing():
    agent = RecommenderAgent()
    result = agent.run("")
    assert len(result.recommendations) == 5   # still returns something usable
    assert result.passed is False             # but honestly flags low confidence
    assert result.advisory is not None


def test_agent_respects_the_retry_cap():
    agent = RecommenderAgent()
    result = agent.run("qwerty nonsense")
    assert result.attempts <= 3               # never loops forever
