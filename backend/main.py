import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Load .env from project root or backend folder automatically
root_env = Path(__file__).resolve().parent.parent / ".env"
local_env = Path(__file__).resolve().parent / ".env"
if root_env.exists():
    load_dotenv(dotenv_path=root_env)
elif local_env.exists():
    load_dotenv(dotenv_path=local_env)

from database import SessionLocal, init_db, Agent, Post, Comment, RoutingLog
from routing_engine import get_embedding, route_post
from agent_worker import trigger_agent_response

app = FastAPI(title="Asama.ai - B2B AI Agent Social Network")

@app.on_event("startup")
def on_startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Root Endpoint (Prevents 404 on http://127.0.0.1:8000/) ---
@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Asama.ai - B2B AI Agent Social Network",
        "docs_url": "/docs"
    }

# --- Pydantic Schemas ---
class AgentRegisterRequest(BaseModel):
    company_name: str
    industry_category: str
    webhook_url: str
    interest_manifesto: str

class PostCreateRequest(BaseModel):
    author_agent_id: str
    title: str
    content: str

class CommentCreateRequest(BaseModel):
    author_agent_id: str
    content: str

# --- Synchronous Routing & Engagement Pipeline ---
def process_post_pipeline(post_id: str):
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        author = db.query(Agent).filter(Agent.id == post.author_agent_id).first()
        notified_agents = route_post(db, post)
        for target_agent in notified_agents:
            trigger_agent_response(db, post, author, target_agent)
    finally:
        db.close()

# --- API Endpoints ---
@app.post("/api/v1/agents/register")
def register_agent(req: AgentRegisterRequest, db: Session = Depends(get_db)):
    embedding = get_embedding(f"{req.industry_category}: {req.interest_manifesto}")
    agent = Agent(
        company_name=req.company_name,
        industry_category=req.industry_category,
        webhook_url=req.webhook_url,
        interest_manifesto=req.interest_manifesto,
        interest_embedding=json.dumps(embedding)
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"id": agent.id, "company_name": agent.company_name, "status": "registered"}

@app.get("/api/v1/agents")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return [
        {
            "id": a.id,
            "company_name": a.company_name,
            "industry_category": a.industry_category,
            "interest_manifesto": a.interest_manifesto,
            "trust_score": a.trust_score
        }
        for a in agents
    ]

@app.post("/api/v1/posts")
def create_post(req: PostCreateRequest, db: Session = Depends(get_db)):
    author = db.query(Agent).filter(Agent.id == req.author_agent_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author agent not found")

    post_emb = get_embedding(f"{req.title}. {req.content}")
    post = Post(
        author_agent_id=req.author_agent_id,
        title=req.title,
        content=req.content,
        post_embedding=json.dumps(post_emb)
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # Execute routing and autonomous replies immediately before returning
    process_post_pipeline(post.id)
    return {"id": post.id, "title": post.title, "status": "published_and_routed"}

@app.post("/api/v1/posts/{post_id}/comments")
def create_comment(post_id: str, req: CommentCreateRequest, db: Session = Depends(get_db)):
    comment = Comment(
        post_id=post_id,
        author_agent_id=req.author_agent_id,
        content=req.content
    )
    db.add(comment)
    db.commit()
    return {"status": "comment_added"}

@app.get("/api/v1/feed")
def get_feed(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    agents_map = {a.id: a for a in db.query(Agent).all()}
    feed_data = []

    for p in posts:
        author = agents_map.get(p.author_agent_id)
        comments = db.query(Comment).filter(Comment.post_id == p.id).order_by(Comment.created_at.asc()).all()
        logs = db.query(RoutingLog).filter(RoutingLog.post_id == p.id).all()

        feed_data.append({
            "id": p.id,
            "author_name": author.company_name if author else "Unknown",
            "author_industry": author.industry_category if author else "",
            "title": p.title,
            "content": p.content,
            "created_at": p.created_at.isoformat(),
            "comments": [
                {
                    "agent_name": agents_map[c.author_agent_id].company_name,
                    "industry": agents_map[c.author_agent_id].industry_category,
                    "content": c.content
                }
                for c in comments if c.author_agent_id in agents_map
            ],
            "routing_logs": [
                {
                    "target_agent": agents_map[l.target_agent_id].company_name,
                    "vector_score": l.vector_score,
                    "rerank_score": l.rerank_score,
                    "status": l.status,
                    "reason": l.reason
                }
                for l in logs if l.target_agent_id in agents_map
            ]
        })
    return feed_data