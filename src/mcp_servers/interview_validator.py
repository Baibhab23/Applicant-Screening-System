from mcp.server.fastmcp import FastMCP

mcp = FastMCP("interview_validator")

@mcp.tool()
def validate_interview(candidate_id: str, interview_data: dict) -> dict:
    """Validate the interview data for a given candidate."""
    
    validation_results = {
        "candidate_id": candidate_id,
        "is_valid": True,
        "checks": {}
    }
    
    # Check 1: Verify responses are not empty
    responses = interview_data.get("responses", {})
    validation_results["checks"]["has_responses"] = len(responses) > 0
    
    # Check 2: Verify minimum number of questions answered
    min_questions = 3
    validation_results["checks"]["sufficient_responses"] = len(responses) >= min_questions
    
    # Check 3: Check response quality (length)
    avg_response_length = sum(len(str(r)) for r in responses.values()) / len(responses) if responses else 0
    validation_results["checks"]["quality_responses"] = avg_response_length > 50
    
    # Overall validation
    validation_results["is_valid"] = all(validation_results["checks"].values())
    
    return validation_results


@mcp.tool()
def score_interview(candidate_id: str, interview_responses: list) -> dict:
    """Score interview responses for structural integrity.

    This scorer measures whether responses are substantive, causally structured,
    and technically grounded — not whether the candidate is a good hire. It is a
    pre-filter signal: a low score means the response is likely too thin to evaluate;
    a high score means there is enough substance for a human or LLM reviewer to assess.
    It cannot distinguish a genuinely expert answer from a keyword-aware non-answer,
    and its thresholds have not been calibrated against hiring outcomes.

    The returned `structural_signal` field (STRONG/ADEQUATE/WEAK) is intentionally
    distinct from the HIRE/MAYBE/REJECT vocabulary to prevent it from being used
    directly as a hiring decision.
    """

    if not interview_responses:
        return {
            "candidate_id": candidate_id,
            "status": "error",
            "message": "No interview responses provided",
            "score": 0,
        }

    # Domain-specific terms that signal technical depth — generic action verbs
    # (implemented, developed, managed) removed because they appear in nearly
    # every answer and reward verbosity over substance.
    HIGH_VALUE_TERMS = [
        "root cause", "trade-off", "tradeoff", "bottleneck", "profiler",
        "complexity", "architecture", "refactor", "latency", "edge case",
        "regression", "concurren", "algorithm", "benchmark", "constraint",
        "failure mode", "hypothesis", "measured", "scalab", "optimis", "optimiz",
    ]

    # Connectives that reward structured reasoning ("because X, therefore Y")
    # rather than keyword listing.
    REASONING_TERMS = [
        "because", "therefore", "however", "which caused", "resulted in",
        "identified", "discovered", "reduced", "improved", "analysed",
        "analyzed", "designed", "iterated", "led to", "in order to",
    ]

    # Keyword density above this threshold flags likely stuffing.
    STUFFING_DENSITY_THRESHOLD = 0.10

    total_score = 0
    max_score = len(interview_responses) * 10
    response_breakdowns = []

    for response in interview_responses:
        response_text = response.get("response", "")
        text_lower = response_text.lower()
        word_count = max(len(response_text.split()), 1)

        # 1. Length (max 2 pts) — rewards substance, not padding
        length_score = min(len(response_text) / 150, 1) * 2

        # 2. Technical depth (max 4 pts) — one point per unique high-value term
        depth_hits = sum(1 for kw in HIGH_VALUE_TERMS if kw in text_lower)
        depth_score = min(depth_hits, 4)

        # 3. Reasoning structure (max 3 pts) — rewards causal explanation
        reasoning_hits = sum(1 for kw in REASONING_TERMS if kw in text_lower)
        reasoning_score = min(reasoning_hits, 3)

        # 4. Coherence (max 1 pt) — penalises single-sentence non-answers
        sentence_count = text_lower.count(".") + text_lower.count("?") + text_lower.count("!")
        coherence_score = 1 if sentence_count >= 2 else 0

        # Stuffing penalty: if keyword hits are dense relative to total words,
        # the answer is likely padded rather than substantive — halve the score.
        total_hits = depth_hits + reasoning_hits
        density = total_hits / word_count
        stuffing_penalty = 0.5 if (density > STUFFING_DENSITY_THRESHOLD and total_hits > 3) else 1.0

        response_score = (length_score + depth_score + reasoning_score + coherence_score) * stuffing_penalty
        total_score += response_score

        response_breakdowns.append({
            "question": response.get("question", ""),
            "scores": {
                "length": round(length_score, 2),
                "technical_depth": round(depth_score, 2),
                "reasoning_structure": round(reasoning_score, 2),
                "coherence": coherence_score,
            },
            "stuffing_penalty_applied": stuffing_penalty < 1.0,
            "response_score": round(response_score, 2),
            "response_score_max": 10,
        })

    percentage = (total_score / max_score) * 100 if max_score > 0 else 0

    if percentage >= 70:
        structural_signal = "STRONG"
    elif percentage >= 50:
        structural_signal = "ADEQUATE"
    else:
        structural_signal = "WEAK"

    return {
        "candidate_id": candidate_id,
        "status": "scored",
        "score": round(percentage, 2),
        "total_points": round(total_score, 2),
        "max_points": max_score,
        "structural_signal": structural_signal,
        "response_breakdowns": response_breakdowns,
        "dimension_totals": {
            "length": round(sum(r["scores"]["length"] for r in response_breakdowns), 2),
            "technical_depth": round(sum(r["scores"]["technical_depth"] for r in response_breakdowns), 2),
            "reasoning_structure": round(sum(r["scores"]["reasoning_structure"] for r in response_breakdowns), 2),
            "coherence": round(sum(r["scores"]["coherence"] for r in response_breakdowns), 2),
        },
    }


@mcp.tool()
def get_interview_questions(role: str, difficulty: str = "medium") -> dict:
    """Get standard interview questions for a specific role."""
    
    questions_db = {
        "software_engineer": {
            "easy": [
                "Tell me about yourself",
                "Why are you interested in this position?",
                "What is your experience with version control?"
            ],
            "medium": [
                "Describe a challenging project you worked on",
                "How do you approach debugging complex issues?",
                "Explain the difference between REST and GraphQL"
            ],
            "hard": [
                "Design a scalable system for real-time chat",
                "Explain microservices architecture and trade-offs",
                "How would you optimize a slow database query?"
            ]
        },
        "data_scientist": {
            "medium": [
                "Explain the bias-variance tradeoff",
                "How do you handle missing data?",
                "Describe your experience with A/B testing"
            ]
        }
    }
    
    role_questions = questions_db.get(role.lower().replace(" ", "_"), {})
    questions = role_questions.get(difficulty, [])
    
    return {
        "role": role,
        "difficulty": difficulty,
        "questions": questions,
        "count": len(questions)
    }


if __name__ == "__main__":
    mcp.run(transport="sse")