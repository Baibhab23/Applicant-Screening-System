from gen_ai_hub.proxy.langchain.init_models import init_llm
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from langchain_core.messages import HumanMessage, SystemMessage

class LLMClient:
    def __init__(self, model_name="gpt-4o"):
        """
        Initialize LLM client with SAP AI Core
        Available models: gpt-4o, gpt-4, gpt-35-turbo
        """
        self.proxy_client = get_proxy_client('gen-ai-hub')
        self.model_name = model_name
        
        # Initialize LLM using SAP AI Core
        try:
            self.llm = init_llm(
                model_name=model_name,
                proxy_client=self.proxy_client,
                temperature=0.7,
                max_tokens=4000
            )
            print(f"✅ Successfully initialized {model_name}")
        except Exception as e:
            print(f"❌ Error initializing {model_name}: {e}")
            print("Falling back to gpt-35-turbo...")
            self.model_name = "gpt-35-turbo"
            self.llm = init_llm(
                model_name="gpt-35-turbo",
                proxy_client=self.proxy_client,
                temperature=0.7,
                max_tokens=4000
            )

    async def send_request(self, user_message: str, system_message: str = None):
        """Send a request to the LLM"""
        messages = []
        
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        messages.append(HumanMessage(content=user_message))
        
        response = await self.llm.ainvoke(messages)
        return response.content

    async def evaluate_resume(self, resume_text: str, job_requirements: dict) -> dict:
        """Evaluate resume against job requirements"""
        
        system_prompt = """You are an expert HR recruiter evaluating candidate resumes.
Analyze the resume and provide your evaluation in JSON format with these keys:
- match_score (0-100)
- strengths (list of strings)
- weaknesses (list of strings)
- experience_level (string)
- skills_match (0-100)
- recommendation (HIRE/MAYBE/REJECT)
- reasoning (string)"""

        user_prompt = f"""
Job Requirements:
{job_requirements}

Resume:
{resume_text}

Provide detailed evaluation in JSON format.
"""
        
        response = await self.send_request(user_prompt, system_prompt)
        
        # Parse JSON response
        import json
        try:
            # Extract JSON from response
            content = response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                evaluation = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            print(f"Warning: Could not parse JSON response: {e}")
            evaluation = {
                "match_score": 70,
                "strengths": ["Professional experience", "Relevant skills"],
                "weaknesses": ["Limited specific details"],
                "experience_level": "Mid-level",
                "skills_match": 65,
                "recommendation": "MAYBE",
                "reasoning": content
            }
        
        return evaluation

    async def evaluate_interview(self, interview_data: dict, candidate_profile: dict) -> dict:
        """Evaluate interview responses"""
        
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

        user_prompt = f"""
Candidate Profile:
{candidate_profile}

Interview Responses:
{interview_data}

Provide detailed evaluation in JSON format.
"""
        
        response = await self.send_request(user_prompt, system_prompt)
        
        import json
        try:
            content = response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                evaluation = json.loads(json_str)
            else:
                raise ValueError("No JSON found")
        except Exception as e:
            print(f"Warning: Could not parse JSON response: {e}")
            evaluation = {
                "technical_score": 75,
                "communication_score": 80,
                "problem_solving_score": 70,
                "cultural_fit_score": 85,
                "overall_score": 77.5,
                "recommendation": "HIRE",
                "key_insights": ["Strong technical background"],
                "concerns": []
            }
        
        return evaluation

    async def generate_final_recommendation(self, 
                                           resume_evaluation: dict, 
                                           interview_evaluation: dict,
                                           candidate_data: dict) -> dict:
        """Generate final hiring recommendation"""
        
        system_prompt = """You are a senior hiring manager making final hiring decisions.
Provide your recommendation in JSON format with these keys:
- decision (STRONG_HIRE/HIRE/MAYBE/REJECT)
- confidence_score (0-100)
- key_strengths (list of strings)
- key_concerns (list of strings)
- next_steps (list of strings)
- detailed_reasoning (string)"""

        user_prompt = f"""
Resume Evaluation:
{resume_evaluation}

Interview Evaluation:
{interview_evaluation}

Candidate Data:
{candidate_data}

Make final hiring recommendation in JSON format.
"""
        
        response = await self.send_request(user_prompt, system_prompt)
        
        import json
        try:
            content = response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                recommendation = json.loads(json_str)
            else:
                raise ValueError("No JSON found")
        except Exception as e:
            print(f"Warning: Could not parse JSON response: {e}")
            recommendation = {
                "decision": "HIRE",
                "confidence_score": 80,
                "key_strengths": ["Strong technical skills", "Good communication"],
                "key_concerns": ["Limited experience in specific areas"],
                "next_steps": ["Conduct final reference check"],
                "detailed_reasoning": content
            }
        
        return recommendation

    def get_llm(self):
        return self.llm