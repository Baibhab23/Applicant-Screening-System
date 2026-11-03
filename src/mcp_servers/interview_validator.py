from mcp.server.fastmcp import FastMCP

mcp = FastMCP("interview_validator")


@mcp.tool()
def get_scoring_rubric(role: str) -> dict:
    """Get the evaluation rubric for a role.
    Call this before evaluating interview responses to understand what a good answer looks like."""
    rubrics = {
        "software_engineer": {
            "technical_depth": (
                "Candidate names root cause, not just symptoms. Uses specific tools, "
                "algorithms, complexity classes, or measured metrics."
            ),
            "problem_solving": (
                "Structured approach: diagnose → hypothesise → test → measure. Shows iteration."
            ),
            "communication": (
                "Cause-and-effect language. Explains tradeoffs. Quantifies outcomes "
                "(latency, throughput, error rate)."
            ),
            "cultural_fit": (
                "Ownership language. Collaborates. Learns from failures."
            ),
            "red_flags": (
                "Vague generalities, no metrics, cannot explain how the candidate "
                "reached a conclusion, keyword listing without context."
            ),
        },
        "data_scientist": {
            "technical_depth": (
                "Statistical rigour: bias-variance tradeoff, overfitting, "
                "confidence intervals, or ablations."
            ),
            "problem_solving": (
                "Frames problem as hypothesis. Defines success metric before modelling. "
                "Validates on held-out data."
            ),
            "communication": (
                "Can explain model to a non-technical stakeholder. Quantifies impact."
            ),
            "red_flags": (
                "Cannot explain model choice, no mention of validation, "
                "uses accuracy as the sole metric."
            ),
        },
    }
    key = role.lower().replace(" ", "_")
    return {"role": role, "rubric": rubrics.get(key, rubrics["software_engineer"])}


@mcp.tool()
def get_job_requirements(role: str) -> dict:
    """Get standard job requirements for a role.
    Use this to compare candidate experience against expectations during resume screening."""
    requirements = {
        "software_engineer": {
            "required_experience": "3+ years",
            "required_skills": ["Python", "JavaScript", "SQL"],
            "preferred_skills": ["AWS", "Docker", "Kubernetes"],
            "education": "Bachelor's degree in CS or related field",
            "responsibilities": [
                "Design and build scalable backend services",
                "Write clean, tested, well-documented code",
                "Participate in code review and architecture discussions",
            ],
        },
        "data_scientist": {
            "required_experience": "2+ years",
            "required_skills": ["Python", "SQL", "Machine Learning", "Statistics"],
            "preferred_skills": ["Spark", "Airflow", "dbt", "MLflow"],
            "education": "Bachelor's degree in Statistics, Mathematics, or CS",
            "responsibilities": [
                "Build and deploy predictive models",
                "Run A/B tests and interpret results",
                "Communicate findings to stakeholders",
            ],
        },
    }
    key = role.lower().replace(" ", "_")
    return {"role": role, "requirements": requirements.get(key, requirements["software_engineer"])}


@mcp.tool()
def get_interview_questions(role: str, difficulty: str = "medium") -> dict:
    """Get standard interview questions for a role and difficulty level."""
    questions_db = {
        "software_engineer": {
            "easy": [
                "Tell me about yourself.",
                "Why are you interested in this position?",
                "What is your experience with version control?",
            ],
            "medium": [
                "Describe a challenging project you worked on.",
                "How do you approach debugging complex issues?",
                "Explain the difference between REST and GraphQL.",
            ],
            "hard": [
                "Design a scalable system for real-time chat.",
                "Explain microservices architecture and its tradeoffs.",
                "How would you identify and fix a slow database query?",
            ],
        },
        "data_scientist": {
            "medium": [
                "Explain the bias-variance tradeoff.",
                "How do you handle missing data?",
                "Describe your experience with A/B testing.",
            ],
        },
    }
    role_questions = questions_db.get(role.lower().replace(" ", "_"), {})
    questions = role_questions.get(difficulty, [])
    return {"role": role, "difficulty": difficulty, "questions": questions, "count": len(questions)}


if __name__ == "__main__":
    mcp.run(transport="sse")
