import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_servers.interview_validator import validate_interview, score_interview, get_interview_questions


def test_validate_interview_valid():
    interview_data = {
        "responses": {
            "Q1": "I have five years of Python experience building scalable microservices.",
            "Q2": "I led a team of four engineers on a successful cloud migration project.",
            "Q3": "I use test-driven development and CI/CD pipelines in every project.",
        }
    }
    result = validate_interview(candidate_id="test-1", interview_data=interview_data)
    assert result["is_valid"] is True
    assert "checks" in result


def test_validate_interview_insufficient_responses():
    interview_data = {"responses": {"Q1": "Short"}}
    result = validate_interview(candidate_id="test-2", interview_data=interview_data)
    assert result["checks"]["sufficient_responses"] is False


def test_score_interview_returns_score():
    responses = [
        {"question": "Q1", "response": "I identified the root cause by profiling memory allocation across request cycles, which led to a 40% latency reduction."},
        {"question": "Q2", "response": "The tradeoff was between consistency and availability; therefore I designed the architecture to favour availability because the failure mode was recoverable."},
    ]
    result = score_interview(candidate_id="test-3", interview_responses=responses)
    assert "score" in result
    assert result["score"] >= 0


def test_score_interview_penalises_keyword_stuffing():
    # Dense keyword padding should score lower than a substantive answer
    # of similar length due to the stuffing penalty.
    padded = {"question": "Q1", "response": (
        "root cause root cause bottleneck bottleneck algorithm algorithm "
        "latency latency refactor refactor constraint constraint benchmark "
        "because because therefore therefore however however identified identified "
        "measured measured discovered discovered reduced reduced improved improved "
    )}
    substantive = {"question": "Q1", "response": (
        "I identified the root cause of the bottleneck by running a profiler "
        "and measuring latency at each layer. The algorithm had O(n²) complexity "
        "which I refactored to O(n log n), because the constraint was response time "
        "under 200ms. This resulted in a measurable 60% improvement in p95 latency."
    )}
    padded_result = score_interview(candidate_id="pad", interview_responses=[padded])
    substantive_result = score_interview(candidate_id="sub", interview_responses=[substantive])
    assert substantive_result["score"] >= padded_result["score"]


def test_score_interview_rewards_reasoning_over_verbs():
    # A technically precise answer without generic action verbs should
    # outscore a verb-heavy answer with no causal reasoning.
    verb_heavy = {"question": "Q1", "response": "I implemented and developed and managed and executed and delivered and coordinated and organised the project successfully with my team."}
    reasoned = {"question": "Q1", "response": "The system was failing because of a race condition in the cache invalidation layer. I identified the root cause through concurrency analysis, therefore I redesigned the architecture to use a write-through strategy, which reduced failure modes significantly."}
    verb_result = score_interview(candidate_id="v", interview_responses=[verb_heavy])
    reasoned_result = score_interview(candidate_id="r", interview_responses=[reasoned])
    assert reasoned_result["score"] > verb_result["score"]


def test_get_interview_questions():
    result = get_interview_questions(role="software_engineer", difficulty="medium")
    assert "questions" in result
    assert len(result["questions"]) > 0
