import os
import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Agent, Post, RoutingLog

# Load .env from project root or backend folder automatically
root_env = Path(__file__).resolve().parent.parent / ".env"
local_env = Path(__file__).resolve().parent / ".env"
if root_env.exists():
    load_dotenv(dotenv_path=root_env)
elif local_env.exists():
    load_dotenv(dotenv_path=local_env)

# Embedding model (all-MiniLM-L6-v2 is fast and runs locally)
embedder = SentenceTransformer("all-MiniLM-L6-v2")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_active_groq_model() -> str:
    """Automatically selects an active chat model available on the user's Groq API key."""
    try:
        models = [
            m.id for m in groq_client.models.list().data
            if "whisper" not in m.id.lower() and "guard" not in m.id.lower() and "tts" not in m.id.lower()
        ]
        for preferred in [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3-32b",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
        ]:
            if preferred in models:
                return preferred
        if models:
            return models[0]
    except Exception:
        pass
    return "openai/gpt-oss-20b"

def get_embedding(text: str) -> list[float]:
    return embedder.encode(text).tolist()

def evaluate_relevance_with_llm(post_title: str, post_content: str, company_name: str, manifesto: str) -> dict:
    """Stage 3: LLM Judge to compute final joint relevance score (0.0 to 1.0)."""
    prompt = f"""
    You are a B2B AI Network Relevance Judge.
    Evaluate if the target company agent would find the incoming post relevant for a business partnership, cross-promotion, or strategic reply.

    Incoming Post:
    Title: {post_title}
    Content: {post_content}

    Target Company: {company_name}
    Target Interest Manifesto: {manifesto}

    Return ONLY a valid JSON object with two keys:
    - "score": a float between 0.0 and 1.0 (e.g., 0.85 for strong synergy like food delivery + UPI payment, 0.15 for unrelated like food + automobiles)
    - "reason": a short 1-sentence explanation.
    """
    try:
        active_model = get_active_groq_model()
        response = groq_client.chat.completions.create(
            model=active_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "score": float(result.get("score", 0.0)),
            "reason": result.get("reason", "Evaluated by LLM Judge.")
        }
    except Exception as e:
        return {"score": 0.0, "reason": f"LLM Judge error: {str(e)}"}

def route_post(db: Session, post: Post) -> list[dict]:
    """Executes the 3-Stage Relevance Routing Pipeline."""
    # Stage 1: Fast SQL Metadata Guardrails (Exclude author and low-trust agents)
    eligible_agents = db.query(Agent).filter(
        Agent.id != post.author_agent_id,
        Agent.trust_score >= 0.5
    ).all()

    if not eligible_agents:
        return []

    post_vec = np.array(json.loads(post.post_embedding)).reshape(1, -1)
    candidates = []

    # Stage 2: Dense Vector Similarity Search
    for agent in eligible_agents:
        agent_vec = np.array(json.loads(agent.interest_embedding)).reshape(1, -1)
        sim_score = float(cosine_similarity(post_vec, agent_vec)[0][0])
        candidates.append((agent, sim_score))

    # Sort by vector similarity and take Top 5 candidates
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = candidates[:5]

    notified_agents = []

    # Stage 3: High-Precision LLM Reranker (Threshold >= 0.70)
    for agent, vec_score in top_candidates:
        if vec_score < 0.05:
            # Drop obvious mismatches early to save LLM tokens
            log = RoutingLog(
                post_id=post.id,
                target_agent_id=agent.id,
                vector_score=round(vec_score, 3),
                rerank_score=0.0,
                status="DROPPED",
                reason="Dropped at Stage 2 (Low semantic vector similarity)."
            )
            db.add(log)
            continue

        judge_result = evaluate_relevance_with_llm(
            post.title, post.content, agent.company_name, agent.interest_manifesto
        )
        rerank_score = judge_result["score"]
        reason = judge_result["reason"]

        if rerank_score >= 0.70:
            status = "NOTIFIED"
            notified_agents.append(agent)
        else:
            status = "DROPPED"

        log = RoutingLog(
            post_id=post.id,
            target_agent_id=agent.id,
            vector_score=round(vec_score, 3),
            rerank_score=round(rerank_score, 3),
            status=status,
            reason=reason
        )
        db.add(log)

    db.commit()
    return notified_agents