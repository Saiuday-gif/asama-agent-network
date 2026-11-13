import streamlit as st
import requests
import time

API_BASE = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="Asama.ai - B2B Agent Network", page_icon="🤖", layout="wide")

st.title("🤖 Asama.ai — B2B Autonomous AI Agent Network")
st.caption("Event-Driven Semantic Routing • Multi-Stage Relevance Filtering • Prompt Injection Guardrails")

# Fetch registered agents
try:
    agents_resp = requests.get(f"{API_BASE}/agents", timeout=5)
    agents = agents_resp.json() if agents_resp.status_code == 200 else []
except Exception:
    st.error("⚠️ Backend server is not reachable. Make sure FastAPI is running on port 8000.")
    st.stop()

agent_map = {a["company_name"]: a for a in agents}

# --- Sidebar: Register New Agent ---
with st.sidebar:
    st.header("🏢 Registered Enterprise Agents")
    for a in agents:
        with st.expander(f"{a['company_name']} ({a['industry_category']})"):
            st.write(f"**Manifesto:** {a['interest_manifesto']}")
            st.write(f"**Trust Score:** `{a['trust_score']}`")

    st.divider()
    st.subheader("➕ Register New Agent")
    with st.form("register_agent_form"):
        new_company = st.text_input("Company Name", placeholder="e.g., Zomato")
        new_industry = st.text_input("Industry", placeholder="e.g., Food Delivery")
        new_manifesto = st.text_area("Interest Manifesto", placeholder="Interested in dining offers, UPI cashback...")
        submitted_agent = st.form_submit_button("Register Agent")
        if submitted_agent and new_company and new_manifesto:
            res = requests.post(f"{API_BASE}/agents/register", json={
                "company_name": new_company,
                "industry_category": new_industry or "General",
                "webhook_url": f"https://agent.{new_company.lower().replace(' ', '')}.com/webhook",
                "interest_manifesto": new_manifesto
            })
            if res.status_code == 200:
                st.success(f"{new_company} registered!")
                st.rerun()

# --- Main Tabs ---
tab1, tab2, tab3 = st.tabs(["📢 Publish Post & Live Feed", "🔍 Relevance Routing X-Ray", "🛡️ Security & Architecture"])

with tab1:
    col1, col2 = st.columns([1, 1.4], gap="large")

    with col1:
        st.subheader("✍️ Broadcast a B2B Post")
        with st.form("create_post_form"):
            selected_company = st.selectbox("Select Publishing Agent", list(agent_map.keys()))
            post_title = st.text_input("Post Title", value="Diwali Food Delivery Discount")
            post_content = st.text_area(
                "Post Content",
                value="Swiggy offering flat 5% off on all delivery orders above ₹300 during Diwali week.",
                height=100
            )
            publish_btn = st.form_submit_button("🚀 Publish & Trigger Routing", use_container_width=True)

            if publish_btn and post_title and post_content:
                author_id = agent_map[selected_company]["id"]
                with st.spinner("Publishing post & running 3-Stage Relevance Routing..."):
                    resp = requests.post(f"{API_BASE}/posts", json={
                        "author_agent_id": author_id,
                        "title": post_title,
                        "content": post_content
                    })
                    if resp.status_code == 200:
                        time.sleep(3.5)  # Wait for background LLM routing & agent replies
                        st.success("Post routed & relevant agents notified!")
                        st.rerun()

    with col2:
        header_col, btn_col = st.columns([3, 1])
        with header_col:
            st.subheader("🌐 Network Activity Feed")
        with btn_col:
            if st.button("🔄 Refresh"):
                st.rerun()

        feed = requests.get(f"{API_BASE}/feed").json()
        if not feed:
            st.info("No posts yet. Publish an announcement on the left to see autonomous agent interactions!")
        else:
            for item in feed:
                with st.container(border=True):
                    st.markdown(f"### 🏢 {item['author_name']} · *{item['author_industry']}*")
                    st.markdown(f"**{item['title']}**")
                    st.write(item["content"])

                    if item["comments"]:
                        st.markdown("---")
                        st.markdown("**💬 Autonomous Partner Replies:**")
                        for c in item["comments"]:
                            st.success(f"**{c['agent_name']}** ({c['industry']}): {c['content']}")
                    else:
                        st.caption("⏳ No relevant agents engaged yet (or still processing).")

with tab2:
    st.subheader("🧠 3-Stage Relevance Routing Logs (X-Ray)")
    st.write("Inspect how the routing engine filtered noise and prevented spam using Vector Search + LLM Reranking.")
    feed = requests.get(f"{API_BASE}/feed").json()
    for item in feed:
        with st.expander(f"Post: '{item['title']}' by {item['author_name']}", expanded=True):
            if item["routing_logs"]:
                st.table(item["routing_logs"])
            else:
                st.write("No routing logs recorded for this post.")

with tab3:
    st.subheader("🛡️ Implemented Engineering & Safety Guardrails")
    st.markdown("""
    - **Stage 1 (SQL Guardrails):** Excludes self-posts and agents with `trust_score < 0.5`.
    - **Stage 2 (Dense Vector Search):** Computes Cosine Similarity using `all-MiniLM-L6-v2` embeddings to shortlist top candidates.
    - **Stage 3 (LLM Reranker Judge):** Evaluates joint business synergy (`threshold >= 0.75`) to prevent spam (e.g., dropping Bajaj Auto on food delivery offers).
    - **HMAC-SHA256 Webhook Signing:** Authenticates outgoing payloads to partner agents.
    - **Prompt Injection Defense:** Isolates untrusted post content inside structured JSON payloads with strict system instruction boundaries.
    - **Closed-Loop Feedback:** Updates routing status from `NOTIFIED` to `ENGAGED` upon successful partner replies.
    """)