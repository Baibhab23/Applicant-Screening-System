from typing import Dict
from datetime import datetime

class Interview:
    def __init__(self, candidate_id: str, responses: dict = None, scores: dict = None, validation_results: dict = None):
        self.candidate_id = candidate_id
        self.responses = responses or {}
        self.scores = scores or {}
        self.validation_results = validation_results or {}
        self.conducted_at = datetime.now()
        self.status = "scheduled"

    def add_response(self, question_id: str, response: str):
        """Add or update a response to a question"""
        self.responses[question_id] = response

    def update_score(self, criterion: str, score: float):
        """Update score for a specific criterion"""
        self.scores[criterion] = score

    def set_validation_result(self, key: str, result: bool):
        """Set validation result for a specific check"""
        self.validation_results[key] = result

    def get_summary(self) -> Dict:
        """Get interview summary"""
        total_score = sum(self.scores.values()) / len(self.scores) if self.scores else 0
        
        return {
            "candidate_id": self.candidate_id,
            "status": self.status,
            "conducted_at": self.conducted_at.isoformat(),
            "total_questions": len(self.responses),
            "total_score": round(total_score, 2),
            "scores": self.scores,
            "validation_results": self.validation_results,
            "recommendation": self.get_recommendation(total_score)
        }

    def get_recommendation(self, score: float) -> str:
        """Get recommendation based on overall score"""
        if score >= 80:
            return "STRONG_HIRE"
        elif score >= 70:
            return "HIRE"
        elif score >= 60:
            return "MAYBE"
        else:
            return "NO_HIRE"

    def mark_completed(self):
        """Mark interview as completed"""
        self.status = "completed"

    def to_dict(self) -> Dict:
        """Convert interview to dictionary"""
        return {
            "candidate_id": self.candidate_id,
            "responses": self.responses,
            "scores": self.scores,
            "validation_results": self.validation_results,
            "status": self.status,
            "conducted_at": self.conducted_at.isoformat(),
            "summary": self.get_summary()
        }