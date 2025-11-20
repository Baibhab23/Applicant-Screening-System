from typing import Dict, List

def score_interview(candidate_responses: dict, scoring_criteria: dict) -> dict:
    """Scores an interview based on candidate responses and predefined criteria."""
    scores = {}
    total_score = 0
    max_score = 0

    for question, criteria in scoring_criteria.items():
        response = candidate_responses.get(question, "")
        
        # Calculate score based on keyword matching
        keywords = criteria.get('keywords', [])
        max_points = criteria.get('max_points', 10)
        
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in response.lower())
        question_score = min((keyword_matches / len(keywords)) * max_points if keywords else 0, max_points)
        
        scores[question] = {
            'score': round(question_score, 2),
            'max_score': max_points,
            'keywords_matched': keyword_matches,
            'total_keywords': len(keywords)
        }
        
        total_score += question_score
        max_score += max_points

    overall_percentage = (total_score / max_score * 100) if max_score > 0 else 0

    return {
        'question_scores': scores,
        'total_score': round(total_score, 2),
        'max_score': max_score,
        'overall_percentage': round(overall_percentage, 2),
        'recommendation': get_recommendation(overall_percentage)
    }


def get_recommendation(percentage: float) -> str:
    """Get hiring recommendation based on score percentage"""
    if percentage >= 80:
        return "STRONG_HIRE"
    elif percentage >= 70:
        return "HIRE"
    elif percentage >= 60:
        return "MAYBE"
    else:
        return "NO_HIRE"


def generate_report(interview_score: dict) -> str:
    """Generate a detailed interview report"""
    report = f"""
INTERVIEW EVALUATION REPORT
{'=' * 50}

Overall Score: {interview_score['total_score']}/{interview_score['max_score']} ({interview_score['overall_percentage']}%)
Recommendation: {interview_score['recommendation']}

Question-by-Question Breakdown:
{'-' * 50}
"""
    
    for question, details in interview_score['question_scores'].items():
        report += f"""
Question: {question}
Score: {details['score']}/{details['max_score']}
Keywords Matched: {details['keywords_matched']}/{details['total_keywords']}
"""
    
    report += f"\n{'=' * 50}\n"
    return report