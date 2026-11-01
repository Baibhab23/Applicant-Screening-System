from __future__ import annotations

import asyncio
import json as _json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, g, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException

from mcp import ClientSession
from mcp.client.sse import sse_client

from agents.screening_agent import ScreeningAgent
from agents.validation_agent import ValidationAgent
from models.db import (
    get_audit_log,
    get_applicant,
    get_interviews_for_applicant,
    get_recommendations_for_applicant,
    init_db,
    insert_applicant,
    insert_interview,
    insert_recommendation,
    list_applicants,
    log_audit,
    update_applicant_status,
)
from tools.resume_parser import ResumeParser
from utils.auth import issue_token, require_auth
from utils.config_loader import load_mcp_config
from utils.llm_client import LLMClient

# ── configuration ─────────────────────────────────────────────────────────────

mcp_cfg = load_mcp_config()
MCP_URL = mcp_cfg["mcpServers"]["interview_validator"]["url"]
USE_MCP = True

# Maximum resume / interview payload in bytes (1 MB).
# Large payloads burn tokens and can slow the LLM; this is the system boundary.
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_BYTES", str(1 * 1024 * 1024)))

# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Rate limiting: keyed by remote IP.
# Screening and validation are expensive (LLM calls); tighter limits prevent abuse.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ── initialisation ────────────────────────────────────────────────────────────

init_db()

llm_client = LLMClient()
screening_agent = ScreeningAgent()
validation_agent = ValidationAgent()


# ── helpers ───────────────────────────────────────────────────────────────────

def _current_user_id() -> str:
    return (g.current_user or {}).get("sub", "anonymous") if hasattr(g, "current_user") else "anonymous"


# ── auth endpoint ─────────────────────────────────────────────────────────────

@app.route("/auth/token", methods=["POST"])
@limiter.limit("10 per minute")
def get_token():
    """Exchange an API key for a short-lived JWT."""
    data = request.json or {}
    api_key = data.get("api_key", "")
    if not api_key:
        return jsonify({"error": "api_key is required"}), 400
    token = issue_token(api_key)
    if token is None:
        return jsonify({"error": "Invalid API key"}), 401
    return jsonify({"token": token})


# ── home ──────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    provider = os.getenv("LLM_PROVIDER", "ollama")
    return jsonify({
        "message": "Applicant Screening and Interview Validation System",
        "llm_provider": provider,
        "endpoints": {
            "POST /auth/token":         "Exchange API key for JWT",
            "POST /screen":             "Screen a candidate's resume",
            "POST /validate":           "Validate interview responses",
            "POST /recommend/<id>":     "Generate final recommendation",
            "GET  /applicants":         "List all applicants",
            "GET  /applicant/<id>":     "Get specific applicant profile",
            "GET  /audit":              "Audit log (admin only)",
        },
    })


# ── screen ────────────────────────────────────────────────────────────────────

@app.route("/screen", methods=["POST"])
@limiter.limit("20 per hour")
@require_auth()
def screen_applicant():
    try:
        data = request.json
        resume_text = data.get("resume_text", "")
        job_requirements = data.get("job_requirements", None)

        if not resume_text:
            return jsonify({"error": "resume_text is required"}), 400

        parser = ResumeParser(resume_text)
        parsed_data = parser.parse()

        screening_result = asyncio.run(
            screening_agent.process_resume(resume_text, job_requirements)
        )

        if screening_result.get("evaluation_status") == "failed":
            log_audit("screen_failed", _current_user_id(), {
                "error": screening_result.get("ai_evaluation", {}).get("evaluation_error"),
            })
            return jsonify({
                "error": "LLM evaluation failed — the model did not return a parseable response",
                "evaluation_error": screening_result.get("ai_evaluation", {}).get("evaluation_error"),
            }), 422

        screening_score = screening_result.get("final_score")
        ai_eval = screening_result.get("ai_evaluation", {})

        applicant_id = insert_applicant(
            name=parsed_data.get("name", "Unknown"),
            email=parsed_data.get("email", ""),
            phone=parsed_data.get("phone", ""),
            resume_text=resume_text,
            parsed_data={**parsed_data, "ai_evaluation": ai_eval},
            screening_score=screening_score,
        )

        log_audit("screen_success", _current_user_id(), {
            "applicant_id": applicant_id,
            "screening_score": screening_score,
            "recommendation": ai_eval.get("recommendation"),
        })

        return jsonify({
            "status": "success",
            "applicant_id": applicant_id,
            "parsed_data": parsed_data,
            "screening_score": screening_score,
            "ai_evaluation": ai_eval,
            "recommendation": ai_eval.get("recommendation", "MAYBE"),
        })

    except HTTPException:
        raise
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── validate ──────────────────────────────────────────────────────────────────

@app.route("/validate", methods=["POST"])
@limiter.limit("20 per hour")
@require_auth()
def validate_interview():
    try:
        data = request.json
        applicant_id = data.get("applicant_id")
        interview_data = data.get("interview_data", {})

        if not applicant_id:
            return jsonify({"error": "applicant_id is required"}), 400

        applicant = get_applicant(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404

        candidate_profile = {
            "name": applicant.get("name"),
            "experience": applicant.get("parsed_data", {}).get("experience", []),
            "skills": applicant.get("parsed_data", {}).get("skills", []),
        }

        validation_result = validation_agent.run_validation(interview_data, candidate_profile)

        if validation_result.get("evaluation_status") == "failed":
            log_audit("validate_failed", _current_user_id(), {
                "applicant_id": applicant_id,
                "error": validation_result.get("ai_evaluation", {}).get("evaluation_error"),
            })
            return jsonify({
                "error": "LLM evaluation failed — the model did not return a parseable response",
                "evaluation_error": validation_result.get("ai_evaluation", {}).get("evaluation_error"),
            }), 422

        ai_eval = validation_result.get("ai_evaluation", {})
        interview_score = validation_result.get("final_score")

        # Track which scoring components actually ran. If MCP is unavailable,
        # mark the evaluation PARTIAL so the recruiter knows the combined score
        # was not produced as expected — not silently substitute LLM-only scoring.
        evaluation_components = {
            "llm_interview_eval": True,
            "mcp_structural_validation": False,
            "mcp_structural_scoring": False,
        }
        mcp_validation = None
        mcp_score = None
        mcp_error = None
        score_blending_note = None

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

                if mcp_validation:
                    evaluation_components["mcp_structural_validation"] = True
                if mcp_score and "score" in mcp_score:
                    evaluation_components["mcp_structural_scoring"] = True

                if mcp_score and "score" in mcp_score and interview_score is not None:
                    # The 60/40 split combines two scores that are not on the same
                    # distribution: the LLM score is a holistic semantic judgment while
                    # the MCP score counts structural signals. The weights have not been
                    # validated against hiring outcomes. Treat the blended score as a
                    # rough composite until calibrated against labelled data.
                    LLM_WEIGHT = 0.6
                    MCP_WEIGHT = 0.4
                    interview_score = round(
                        LLM_WEIGHT * interview_score + MCP_WEIGHT * mcp_score["score"], 2
                    )
                    score_blending_note = (
                        f"Blended score: {LLM_WEIGHT:.0%} LLM (semantic) + "
                        f"{MCP_WEIGHT:.0%} MCP (structural). "
                        "Weights are unvalidated — do not use this number as the sole basis for a decision."
                    )

            except Exception as e:
                mcp_error = str(e)
                print("[MCP ERROR]", e)

        # If MCP was expected but did not fully run, mark the evaluation PARTIAL.
        evaluation_partial = USE_MCP and not all(evaluation_components.values())

        interview_id = insert_interview(
            applicant_id=applicant_id,
            interview_data=interview_data,
            validation_results={
                "ai_evaluation": ai_eval,
                "mcp_validation": mcp_validation,
                "mcp_score": mcp_score,
            },
            interview_score=interview_score,
            evaluation_partial=evaluation_partial,
            evaluation_components=evaluation_components,
            mcp_error=mcp_error,
        )

        update_applicant_status(applicant_id, "interviewed")

        log_audit("validate_success", _current_user_id(), {
            "applicant_id": applicant_id,
            "interview_id": interview_id,
            "interview_score": interview_score,
            "evaluation_partial": evaluation_partial,
            "evaluation_components": evaluation_components,
        })

        return jsonify({
            "status": "success",
            "interview_id": interview_id,
            "interview_score": interview_score,
            "ai_evaluation": ai_eval,
            "mcp_validation": mcp_validation,
            "mcp_score": mcp_score,
            "evaluation_partial": evaluation_partial,
            "evaluation_components": evaluation_components,
            "mcp_error": mcp_error,
            "score_blending_note": score_blending_note,
        })

    except HTTPException:
        raise
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── recommend ─────────────────────────────────────────────────────────────────

@app.route("/recommend/<int:applicant_id>", methods=["POST"])
@limiter.limit("20 per hour")
@require_auth()
def generate_recommendation(applicant_id):
    try:
        applicant = get_applicant(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404

        applicant_interviews = get_interviews_for_applicant(applicant_id)
        if not applicant_interviews:
            return jsonify({"error": "No interview found"}), 404

        latest_interview = applicant_interviews[-1]

        resume_evaluation = applicant.get("parsed_data", {}).get("ai_evaluation", {})
        interview_evaluation = latest_interview.get("validation_results", {}).get("ai_evaluation", {})
        mcp_score_data = latest_interview.get("validation_results", {}).get("mcp_score")

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

        if final_recommendation.get("evaluation_status") == "failed":
            log_audit("recommend_failed", _current_user_id(), {
                "applicant_id": applicant_id,
                "error": final_recommendation.get("evaluation_error"),
            })
            return jsonify({
                "error": "LLM evaluation failed — the model did not return a parseable response",
                "evaluation_error": final_recommendation.get("evaluation_error"),
            }), 422

        final_score = final_recommendation.get("confidence_score")
        decision = final_recommendation.get("decision")

        rec_id = insert_recommendation(
            applicant_id=applicant_id,
            interview_id=latest_interview["id"],
            final_score=final_score,
            recommendation=decision,
            reasoning=final_recommendation.get("detailed_reasoning", ""),
        )

        log_audit("recommend_success", _current_user_id(), {
            "applicant_id": applicant_id,
            "recommendation_id": rec_id,
            "decision": decision,
            "confidence_score": final_score,
        })

        return jsonify({
            "status": "success",
            "recommendation_id": rec_id,
            "final_recommendation": final_recommendation,
            "mcp_score_breakdown": mcp_score_data,
            "provider": os.getenv("LLM_PROVIDER", "ollama"),
        })

    except HTTPException:
        raise
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── read endpoints ─────────────────────────────────────────────────────────────

@app.route("/applicants", methods=["GET"])
@require_auth()
def get_applicants():
    try:
        status = request.args.get("status")
        applicants = list_applicants(status_filter=status)
        return jsonify({"status": "success", "count": len(applicants), "applicants": applicants})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/applicant/<int:applicant_id>", methods=["GET"])
@require_auth()
def get_applicant_profile(applicant_id):
    try:
        applicant = get_applicant(applicant_id)
        if not applicant:
            return jsonify({"error": "Applicant not found"}), 404

        return jsonify({
            "status": "success",
            "profile": {
                "applicant": applicant,
                "interviews": get_interviews_for_applicant(applicant_id),
                "recommendations": get_recommendations_for_applicant(applicant_id),
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/audit", methods=["GET"])
@require_auth(roles=["admin"])
def get_audit():
    """Audit log for administrators — records who triggered each evaluation and when."""
    try:
        limit = min(int(request.args.get("limit", 100)), 500)
        return jsonify({"status": "success", "entries": get_audit_log(limit)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(413)
def payload_too_large(e):
    return jsonify({
        "error": "Request payload exceeds maximum allowed size",
        "max_bytes": MAX_CONTENT_LENGTH,
    }), 413


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded", "detail": str(e.description)}), 429


if __name__ == "__main__":
    app.run(debug=True, port=5000)
