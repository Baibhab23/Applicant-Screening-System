import os
import json
from langchain_core.messages import HumanMessage, SystemMessage


class LLMClient:
    """
    LLM client supporting Ollama (free/local), Groq (free cloud), and OpenAI.
    Set LLM_PROVIDER env var to "ollama" (default), "groq", or "openai".
    """

    def __init__(self, model_name: str = None):
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        if model_name is None:
            model_name = os.getenv("LLM_MODEL", self._default_model())

        self.model_name = model_name
        self.llm = self._init_llm()
        print(f"LLM initialized: provider={self.provider}, model={self.model_name}")

    def _default_model(self) -> str:
        defaults = {
            "ollama": "llama3.1",
            "groq": "llama-3.1-8b-instant",
            "openai": "gpt-4o-mini",
        }
        return defaults.get(self.provider, "llama3.1")

    def _init_llm(self):
        if self.provider == "ollama":
            from langchain_ollama import ChatOllama
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            return ChatOllama(
                model=self.model_name,
                base_url=base_url,
                temperature=0.7,
            )

        elif self.provider == "groq":
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY must be set when using Groq provider")
            return ChatGroq(
                model=self.model_name,
                api_key=api_key,
                temperature=0.7,
                max_tokens=4000,
            )

        elif self.provider == "openai":
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY must be set when using OpenAI provider")
            return ChatOpenAI(
                model=self.model_name,
                api_key=api_key,
                temperature=0.7,
                max_tokens=4000,
            )

        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER: '{self.provider}'. "
                "Choose from: ollama, groq, openai"
            )

    async def send_request(self, user_message: str, system_message: str = None) -> str:
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=user_message))
        response = await self.llm.ainvoke(messages)
        return response.content

    def _parse_json_response(self, content: str, fallback: dict) -> dict:
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
            raise ValueError("No JSON object found in response")
        except Exception as e:
            print(f"Warning: Could not parse JSON response: {e}")
            return {**fallback, "reasoning": content}

    async def evaluate_resume(self, resume_text: str, job_requirements: dict) -> dict:
        system_prompt = """You are an expert HR recruiter evaluating candidate resumes.
Analyze the resume and provide your evaluation in JSON format with these keys:
- match_score (0-100)
- strengths (list of strings)
- weaknesses (list of strings)
- experience_level (string)
- skills_match (0-100)
- recommendation (HIRE/MAYBE/REJECT)
- reasoning (string)"""

        user_prompt = f"""Job Requirements:\n{job_requirements}\n\nResume:\n{resume_text}\n\nProvide detailed evaluation in JSON format."""

        response = await self.send_request(user_prompt, system_prompt)
        return self._parse_json_response(response, {
            "match_score": 70,
            "strengths": ["Professional experience", "Relevant skills"],
            "weaknesses": ["Limited specific details"],
            "experience_level": "Mid-level",
            "skills_match": 65,
            "recommendation": "MAYBE",
        })

    async def evaluate_interview(self, interview_data: dict, candidate_profile: dict) -> dict:
        system_prompt = """You are an expert technical interviewer.
Evaluate the candidate's interview responses in JSON format with these keys:
- technical_score (0-100)
- communication_score (0-100)
- problem_solving_score (0-100)
- cultural_fit_score (0-100)
- overall_score (0-100)
- recommendation (STRONG_HIRE/HIRE/MAYBE/NO_HIRE)
- key_insights (list of strings)
- concerns (list of strings)"""

        user_prompt = f"""Candidate Profile:\n{candidate_profile}\n\nInterview Responses:\n{interview_data}\n\nProvide detailed evaluation in JSON format."""

        response = await self.send_request(user_prompt, system_prompt)
        return self._parse_json_response(response, {
            "technical_score": 75,
            "communication_score": 80,
            "problem_solving_score": 70,
            "cultural_fit_score": 85,
            "overall_score": 77.5,
            "recommendation": "HIRE",
            "key_insights": ["Strong technical background"],
            "concerns": [],
        })

    async def generate_final_recommendation(
        self,
        resume_evaluation: dict,
        interview_evaluation: dict,
        candidate_data: dict,
    ) -> dict:
        system_prompt = """You are a senior hiring manager making final hiring decisions.
Provide your recommendation in JSON format with these keys:
- decision (STRONG_HIRE/HIRE/MAYBE/REJECT)
- confidence_score (0-100)
- key_strengths (list of strings)
- key_concerns (list of strings)
- next_steps (list of strings)
- detailed_reasoning (string)"""

        user_prompt = f"""Resume Evaluation:\n{resume_evaluation}\n\nInterview Evaluation:\n{interview_evaluation}\n\nCandidate Data:\n{candidate_data}\n\nMake final hiring recommendation in JSON format."""

        response = await self.send_request(user_prompt, system_prompt)
        return self._parse_json_response(response, {
            "decision": "HIRE",
            "confidence_score": 80,
            "key_strengths": ["Strong technical skills", "Good communication"],
            "key_concerns": ["Limited experience in specific areas"],
            "next_steps": ["Conduct final reference check"],
        })

    def get_llm(self):
        return self.llm
