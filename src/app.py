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
from utils.llm_client import LLMClient

# ── configuration ─────────────────────────────────────────────────────────────

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

        interview_id = insert_interview(
            applicant_id=applicant_id,
            interview_data=interview_data,
            validation_results={"ai_evaluation": ai_eval},
            interview_score=interview_score,
        )

        update_applicant_status(applicant_id, "interviewed")

        log_audit("validate_success", _current_user_id(), {
            "applicant_id": applicant_id,
            "interview_id": interview_id,
            "interview_score": interview_score,
        })

        return jsonify({
            "status": "success",
            "interview_id": interview_id,
            "interview_score": interview_score,
            "ai_evaluation": ai_eval,
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
