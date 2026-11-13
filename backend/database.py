from sqlalchemy import create_engine, Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import uuid

DATABASE_URL = "sqlite:///./asama_network.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, default=generate_uuid)
    company_name = Column(String(255), nullable=False)
    industry_category = Column(String(100), nullable=False)
    webhook_url = Column(Text, nullable=False)
    interest_manifesto = Column(Text, nullable=False)
    interest_embedding = Column(Text, nullable=False)  # Stored as JSON string
    trust_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, default=generate_uuid)
    author_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    post_embedding = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class RoutingLog(Base):
    __tablename__ = "routing_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"))
    target_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"))
    vector_score = Column(Float, nullable=False)
    rerank_score = Column(Float, nullable=False)
    status = Column(String(50), default="NOTIFIED")  # NOTIFIED, ENGAGED, IGNORED, DROPPED
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, default=generate_uuid)
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"))
    author_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def init_db():
    Base.metadata.create_all(bind=engine)