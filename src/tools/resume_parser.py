import re
from typing import List, Dict

class ResumeParser:
    def __init__(self, resume_text: str):
        self.resume_text = resume_text

    def extract_name(self) -> str:
        """Extract name from resume (first line or pattern match)"""
        lines = self.resume_text.split('\n')
        # Try first non-empty line
        for line in lines:
            line = line.strip()
            if line and len(line.split()) <= 4 and not '@' in line and not any(char.isdigit() for char in line):
                return line
        return "Unknown"

    def extract_email(self) -> str:
        """Extract email address"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, self.resume_text)
        return match.group(0) if match else ""

    def extract_phone(self) -> str:
        """Extract phone number"""
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        match = re.search(phone_pattern, self.resume_text)
        return match.group(0) if match else ""

    def extract_experience(self) -> List[Dict[str, str]]:
        """Extract work experience"""
        experience = []
        lines = self.resume_text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['engineer', 'developer', 'manager', 'analyst', 'designer', 'lead']):
                experience.append({
                    "title": line.strip(),
                    "description": line.strip()
                })
        return experience

    def extract_skills(self) -> List[str]:
        """Extract skills"""
        skills = []
        tech_keywords = ['python', 'java', 'javascript', 'react', 'aws', 'docker', 'kubernetes', 
                        'sql', 'nosql', 'node', 'angular', 'vue', 'git', 'ci/cd', 'typescript',
                        'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust']
        
        text_lower = self.resume_text.lower()
        for skill in tech_keywords:
            if skill in text_lower:
                skills.append(skill.title())
        
        return list(set(skills))

    def parse(self) -> Dict[str, any]:
        """Parse all information from resume"""
        return {
            "name": self.extract_name(),
            "email": self.extract_email(),
            "phone": self.extract_phone(),
            "experience": self.extract_experience(),
            "skills": self.extract_skills(),
            "raw_text": self.resume_text
        }