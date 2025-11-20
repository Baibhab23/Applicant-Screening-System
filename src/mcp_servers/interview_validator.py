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
    """Score the interview based on candidate responses."""
    
    if not interview_responses:
        return {
            "candidate_id": candidate_id,
            "status": "error",
            "message": "No interview responses provided",
            "score": 0
        }
    
    # Calculate score based on response quality
    total_score = 0
    max_score = len(interview_responses) * 10
    
    for response in interview_responses:
        response_text = response.get("response", "")
        
        # Score factors
        length_score = min(len(response_text) / 100, 1) * 3  # Max 3 points for length
        keyword_score = 0
        
        # Check for quality keywords
        quality_keywords = ["experience", "project", "team", "implemented", "developed", "managed"]
        keyword_matches = sum(1 for kw in quality_keywords if kw.lower() in response_text.lower())
        keyword_score = min(keyword_matches, 4)  # Max 4 points for keywords
        
        # Completeness score
        completeness_score = 3 if len(response_text) > 200 else 1
        
        response_score = length_score + keyword_score + completeness_score
        total_score += response_score
    
    percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    
    return {
        "candidate_id": candidate_id,
        "status": "scored",
        "score": round(percentage, 2),
        "total_points": round(total_score, 2),
        "max_points": max_score,
        "recommendation": "HIRE" if percentage >= 70 else "MAYBE" if percentage >= 50 else "REJECT"
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