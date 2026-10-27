from flask import Flask, request, jsonify
import asyncio
import json as _json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from utils.llm_client import LLMClient
from agents.screening_agent import ScreeningAgent
from agents.validation_agent import ValidationAgent
from tools.resume_parser import ResumeParser

from mcp import ClientSession
from mcp.client.sse import sse_client
from utils.config_loader import load_mcp_config

mcp_cfg = load_mcp_config()
MCP_URL = mcp_cfg["mcpServers"]["interview_validator"]["url"]

USE_MCP = True

app = Flask(__name__)

# In-memory storage
applicants_store = {}
interviews_store = {}
recommendations_store = {}
next_id = 1

# Initialize LLM Client (provider controlled by LLM_PROVIDER env var)
llm_client = LLMClient()

screening_agent = ScreeningAgent()
validation_agent = ValidationAgent()


@app.route('/')
def home():
    provider = os.getenv("LLM_PROVIDER", "ollama")
    return jsonify({
        "message": "Welcome to the Applicant Screening and Interview Validation System",
        "llm_provider": provider,
        "endpoints": {
            "/screen": "POST - Screen a candidate's resume",
            "/validate": "POST - Validate interview responses",
            "/recommend/<id>": "POST - Generate final recommendation",
            "/applicants": "GET - Get all applicants",
            "/applicant/<id>": "GET - Get specific applicant profile",
        },
    })


@app.route('/screen', methods=['POST'])
def screen_applicant():
    global next_id
    try:
        data = request.json
        resume_text = data.get('resume_text', '')
        job_requirements = data.get('job_requirements', None)

        if not resume_text:
            return jsonify({"error": "resume_text is required"}), 400

        parser = ResumeParser(resume_text)
        parsed_data = parser.parse()

        screening_result = asyncio.run(
            screening_agent.process_resume(resume_text, job_requirements)
        )

        screening_score = screening_result.get('final_score', 70)
        ai_eval = screening_result.get('ai_evaluation', {})

        applicant_id = next_id
        next_id += 1

        applicants_store[applicant_id] = {
            "id": applicant_id,
            "name": parsed_data.get('name', 'Unknown'),
            "email": parsed_data.get('email', ''),
            "phone": parsed_data.get('phone', ''),
            "resume_text": resume_text,
            "parsed_data": {**parsed_data, "ai_evaluation": ai_eval},
            "screening_score": screening_score,
            "status": "screened",
        }

        return jsonify({
            "status": "success",
            "applicant_id": applicant_id,
            "parsed_data": parsed_data,
            "screening_score": screening_score,
            "ai_evaluation": ai_eval,
            "recommendation": ai_eval.get('recommendation', 'MAYBE'),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/validate', methods=['POST'])
def validate_interview():
    global next_id
    try:
        data = request.json
        applicant_id = data.get('applicant_id')
        interview_data = data.get('interview_data', {})

        if not applicant_id:
            return jsonify({"error": "applicant_id is required"}), 400

        applicant = applicants_store.get(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404

        candidate_profile = {
            "name": applicant.get('name'),
            "experience": applicant.get('parsed_data', {}).get('experience', []),
            "skills": applicant.get('parsed_data', {}).get('skills', []),
        }

        validation_result = validation_agent.run_validation(interview_data, candidate_profile)
        ai_eval = validation_result.get('ai_evaluation', {})
        interview_score = validation_result.get('final_score', 75)

        mcp_validation = None
        mcp_score = None

        if USE_MCP:
            try:
                async def call_mcp():
                    async with sse_client(MCP_URL) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            tools = await session.list_tools()
                            tool_names = {t.name for t in tools.tools}

                            v = s = None

                            if "validate_interview" in tool_names:
                                v_resp = await session.call_tool(
                                    "validate_interview",
                                    {"candidate_id": str(applicant_id), "interview_data": interview_data},
                                )
                                if v_resp.content:
                                    v = _json.loads(v_resp.content[0].text)

                            if "score_interview" in tool_names:
                                s_resp = await session.call_tool(
                                    "score_interview",
                                    {
                                        "candidate_id": str(applicant_id),
                                        "interview_responses": [
                                            {"question": q, "response": r}
                                            for q, r in interview_data.get("responses", {}).items()
                                        ],
                                    },
                                )
                                if s_resp.content:
                                    s = _json.loads(s_resp.content[0].text)

                            return v, s

                mcp_validation, mcp_score = asyncio.run(call_mcp())

                if mcp_score and "score" in mcp_score:
                    interview_score = round(0.6 * interview_score + 0.4 * mcp_score["score"], 2)

            except Exception as e:
                print("[MCP ERROR]", e)

        interview_id = next_id
        next_id += 1

        interviews_store[interview_id] = {
            "id": interview_id,
            "applicant_id": applicant_id,
            "interview_data": interview_data,
            "validation_results": {
                "ai_evaluation": ai_eval,
                "mcp_validation": mcp_validation,
                "mcp_score": mcp_score,
            },
            "interview_score": interview_score,
        }

        applicants_store[applicant_id]["status"] = "interviewed"

        return jsonify({
            "status": "success",
            "interview_id": interview_id,
            "interview_score": interview_score,
            "ai_evaluation": ai_eval,
            "mcp_validation": mcp_validation,
            "mcp_score": mcp_score,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/recommend/<int:applicant_id>', methods=['POST'])
def generate_recommendation(applicant_id):
    global next_id
    try:
        applicant = applicants_store.get(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404

        applicant_interviews = [
            i for i in interviews_store.values() if i["applicant_id"] == applicant_id
        ]

        if not applicant_interviews:
            return jsonify({"error": "No interview found"}), 404

        latest_interview = applicant_interviews[-1]

        resume_evaluation = applicant.get("parsed_data", {}).get("ai_evaluation", {})
        interview_evaluation = latest_interview.get("validation_results", {}).get("ai_evaluation", {})

        final_recommendation = asyncio.run(
            llm_client.generate_final_recommendation(
                resume_evaluation,
                interview_evaluation,
                {
                    "name": applicant.get("name"),
                    "email": applicant.get("email"),
                    "screening_score": applicant.get("screening_score"),
                    "interview_score": latest_interview.get("interview_score"),
                },
            )
        )

        final_score = final_recommendation.get("confidence_score", 75)
        decision = final_recommendation.get("decision", "HIRE")

        rec_id = next_id
        next_id += 1

        recommendations_store[rec_id] = {
            "id": rec_id,
            "applicant_id": applicant_id,
            "interview_id": latest_interview["id"],
            "final_score": final_score,
            "recommendation": decision,
            "reasoning": final_recommendation.get("detailed_reasoning", ""),
        }

        return jsonify({
            "status": "success",
            "recommendation_id": rec_id,
            "final_recommendation": final_recommendation,
            "provider": os.getenv("LLM_PROVIDER", "ollama"),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/applicants', methods=['GET'])
def get_applicants():
    try:
        status = request.args.get("status")
        filtered = (
            [a for a in applicants_store.values() if a.get("status") == status]
            if status
            else list(applicants_store.values())
        )
        return jsonify({"status": "success", "count": len(filtered), "applicants": filtered})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/applicant/<int:applicant_id>', methods=['GET'])
def get_applicant_profile(applicant_id):
    try:
        applicant = applicants_store.get(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404

        return jsonify({
            "status": "success",
            "profile": {
                "applicant": applicant,
                "interviews": [i for i in interviews_store.values() if i["applicant_id"] == applicant_id],
                "recommendations": [r for r in recommendations_store.values() if r["applicant_id"] == applicant_id],
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
