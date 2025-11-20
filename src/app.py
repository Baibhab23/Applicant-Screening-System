from flask import Flask, request, jsonify
import asyncio
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from utils.llm_client import LLMClient
from agents.screening_agent import ScreeningAgent
from agents.validation_agent import ValidationAgent
from tools.resume_parser import ResumeParser

app = Flask(__name__)

# In-memory storage
applicants_store = {}
interviews_store = {}
recommendations_store = {}
next_id = 1

# Initialize LLM Client with GPT-4o (SAP AI Core)
llm_client = LLMClient("gpt-4o")

# Initialize agents WITHOUT MCP server dependency
screening_agent = ScreeningAgent(model_name="gpt-4o")
validation_agent = ValidationAgent(model_name="gpt-4o")
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to the Applicant Screening and Interview Validation System (AI-Powered)",
        "llm_model": "gpt-4o",
        "endpoints": {
            "/screen": "POST - Screen a candidate's resume",
            "/validate": "POST - Validate interview responses",
            "/recommend/<id>": "POST - Generate final recommendation",
            "/applicants": "GET - Get all applicants",
            "/applicant/<id>": "GET - Get specific applicant profile"
        }
    })

@app.route('/screen', methods=['POST'])
def screen_applicant():
    """Screen a candidate's resume using AI"""
    global next_id
    try:
        data = request.json
        resume_text = data.get('resume_text', '')
        job_requirements = data.get('job_requirements', None)
        
        if not resume_text:
            return jsonify({"error": "resume_text is required"}), 400
        
        # Parse resume
        parser = ResumeParser(resume_text)
        parsed_data = parser.parse()
        
        # Run AI-powered screening
        screening_result = asyncio.run(
            screening_agent.process_resume(resume_text, job_requirements)
        )
        
        # Get real AI-powered score
        screening_score = screening_result.get('final_score', 70)
        ai_eval = screening_result.get('ai_evaluation', {})
        
        # Save to in-memory store
        applicant_id = next_id
        next_id += 1
        
        applicants_store[applicant_id] = {
            "id": applicant_id,
            "name": parsed_data.get('name', 'Unknown'),
            "email": parsed_data.get('email', ''),
            "phone": parsed_data.get('phone', ''),
            "resume_text": resume_text,
            "parsed_data": {
                **parsed_data,
                "ai_evaluation": ai_eval
            },
            "screening_score": screening_score,
            "status": "screened"
        }
        
        return jsonify({
            "status": "success",
            "applicant_id": applicant_id,
            "parsed_data": parsed_data,
            "screening_score": screening_score,
            "ai_evaluation": ai_eval,
            "recommendation": ai_eval.get('recommendation', 'MAYBE')
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/validate', methods=['POST'])
def validate_interview():
    """Validate interview responses using AI"""
    global next_id
    try:
        data = request.json
        applicant_id = data.get('applicant_id')
        interview_data = data.get('interview_data', {})
        
        if not applicant_id:
            return jsonify({"error": "applicant_id is required"}), 400
        
        # Get candidate profile from store
        applicant = applicants_store.get(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404
        
        candidate_profile = {
            "name": applicant.get('name'),
            "experience": applicant.get('parsed_data', {}).get('experience', []),
            "skills": applicant.get('parsed_data', {}).get('skills', [])
        }
        
        # Run AI-powered validation
        validation_result = validation_agent.run_validation(interview_data, candidate_profile)
        
        # Get real AI-powered score
        interview_score = validation_result.get('final_score', 75)
        ai_eval = validation_result.get('ai_evaluation', {})
        
        # Save interview to in-memory store
        interview_id = next_id
        next_id += 1
        
        interviews_store[interview_id] = {
            "id": interview_id,
            "applicant_id": applicant_id,
            "interview_data": interview_data,
            "validation_results": {
                "ai_evaluation": ai_eval,
                "mcp_validation": validation_result.get('mcp_validation')
            },
            "interview_score": interview_score
        }
        
        # Update applicant status
        applicants_store[applicant_id]['status'] = 'interviewed'
        
        return jsonify({
            "status": "success",
            "interview_id": interview_id,
            "interview_score": interview_score,
            "ai_evaluation": ai_eval,
            "recommendation": ai_eval.get('recommendation', 'HIRE')
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/recommend/<int:applicant_id>', methods=['POST'])
def generate_recommendation(applicant_id):
    """Generate final recommendation using AI"""
    global next_id
    try:
        # Get applicant
        applicant = applicants_store.get(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404
        
        # Get interviews for this applicant
        applicant_interviews = [
            interview for interview in interviews_store.values()
            if interview['applicant_id'] == applicant_id
        ]
        
        if not applicant_interviews:
            return jsonify({"error": "No interview found for this applicant"}), 404
        
        latest_interview = applicant_interviews[-1]
        
        # Get evaluation data
        parsed_data = applicant.get('parsed_data', {})
        resume_evaluation = parsed_data.get('ai_evaluation', {})
        
        validation_results = latest_interview.get('validation_results', {})
        interview_evaluation = validation_results.get('ai_evaluation', {})
        
        # Use AI to generate final recommendation
        final_recommendation = asyncio.run(
            llm_client.generate_final_recommendation(
                resume_evaluation,
                interview_evaluation,
                {
                    "name": applicant.get('name'),
                    "email": applicant.get('email'),
                    "screening_score": applicant.get('screening_score'),
                    "interview_score": latest_interview.get('interview_score')
                }
            )
        )
        
        final_score = final_recommendation.get('confidence_score', 75)
        decision = final_recommendation.get('decision', 'HIRE')
        
        # Save recommendation to in-memory store
        rec_id = next_id
        next_id += 1
        
        recommendations_store[rec_id] = {
            "id": rec_id,
            "applicant_id": applicant_id,
            "interview_id": latest_interview['id'],
            "final_score": final_score,
            "recommendation": decision,
            "reasoning": final_recommendation.get('detailed_reasoning', '')
        }
        
        return jsonify({
            "status": "success",
            "recommendation_id": rec_id,
            "final_recommendation": final_recommendation,
            "model_used": "gpt-4o"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/applicants', methods=['GET'])
def get_applicants():
    """Get all applicants"""
    try:
        status = request.args.get('status')
        
        if status:
            applicants = [
                app for app in applicants_store.values()
                if app.get('status') == status
            ]
        else:
            applicants = list(applicants_store.values())
        
        return jsonify({
            "status": "success",
            "count": len(applicants),
            "applicants": applicants
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/applicant/<int:applicant_id>', methods=['GET'])
def get_applicant_profile(applicant_id):
    """Get complete applicant profile"""
    try:
        applicant = applicants_store.get(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404
        
        # Get interviews for this applicant
        applicant_interviews = [
            interview for interview in interviews_store.values()
            if interview['applicant_id'] == applicant_id
        ]
        
        # Get recommendations for this applicant
        applicant_recommendations = [
            rec for rec in recommendations_store.values()
            if rec['applicant_id'] == applicant_id
        ]
        
        profile = {
            "applicant": applicant,
            "interviews": applicant_interviews,
            "recommendations": applicant_recommendations
        }
        
        return jsonify({
            "status": "success",
            "profile": profile
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)