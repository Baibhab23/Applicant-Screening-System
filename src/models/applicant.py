from typing import List, Dict
from datetime import datetime

class Applicant:
    def __init__(self, name: str, experience: int, skills: list, email: str = "", phone: str = ""):
        self.name = name
        self.experience = experience
        self.skills = skills
        self.email = email
        self.phone = phone
        self.created_at = datetime.now()
        self.status = "pending"
        self.screening_score = None
        self.interview_score = None

    def __repr__(self):
        return f"Applicant(name={self.name}, experience={self.experience}, skills={self.skills})"

    def add_skill(self, skill: str):
        """Add a skill to the applicant's skill list"""
        if skill not in self.skills:
            self.skills.append(skill)

    def remove_skill(self, skill: str):
        """Remove a skill from the applicant's skill list"""
        if skill in self.skills:
            self.skills.remove(skill)

    def set_screening_score(self, score: float):
        """Set the screening score"""
        self.screening_score = score

    def set_interview_score(self, score: float):
        """Set the interview score"""
        self.interview_score = score

    def update_status(self, status: str):
        """Update applicant status: pending, screened, interviewed, hired, rejected"""
        valid_statuses = ["pending", "screened", "interviewed", "hired", "rejected"]
        if status in valid_statuses:
            self.status = status

    def get_overall_score(self) -> float:
        """Calculate overall score from screening and interview"""
        if self.screening_score and self.interview_score:
            return (self.screening_score + self.interview_score) / 2
        elif self.screening_score:
            return self.screening_score
        elif self.interview_score:
            return self.interview_score
        return 0.0

    def to_dict(self) -> Dict:
        """Convert applicant to dictionary"""
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "experience": self.experience,
            "skills": self.skills,
            "status": self.status,
            "screening_score": self.screening_score,
            "interview_score": self.interview_score,
            "overall_score": self.get_overall_score(),
            "created_at": self.created_at.isoformat()
        }