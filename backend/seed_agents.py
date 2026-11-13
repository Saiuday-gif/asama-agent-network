import json
from database import init_db, SessionLocal, Agent
from routing_engine import get_embedding

INITIAL_AGENTS = [
    {
        "company_name": "Swiggy",
        "industry_category": "Food Delivery & Quick Commerce",
        "webhook_url": "https://agent.swiggy.com/v1/events",
        "interest_manifesto": "Food delivery discounts, festive restaurant offers, payment gateway cashback tie-ups, and grocery quick-commerce promotions."
    },
    {
        "company_name": "PhonePe",
        "industry_category": "Payments & Fintech",
        "webhook_url": "https://agent.phonepe.com/v1/events",
        "interest_manifesto": "Digital UPI payments, e-commerce checkout offers, food delivery festive discounts, and merchant cashback partnerships."
    },
    {
        "company_name": "HDFC Bank",
        "industry_category": "Banking & Credit Cards",
        "webhook_url": "https://agent.hdfcbank.com/v1/events",
        "interest_manifesto": "Credit card instant discounts, debit card festive offers, retail shopping rewards, dining privileges, and EMI partnerships."
    },
    {
        "company_name": "Flipkart",
        "industry_category": "E-Commerce & Retail",
        "webhook_url": "https://agent.flipkart.com/v1/events",
        "interest_manifesto": "Big Billion Days sales, bank card instant discounts, UPI cashback deals, electronics launches, and logistics partnerships."
    },
    {
        "company_name": "Bajaj Auto",
        "industry_category": "Automobiles & Two-Wheelers",
        "webhook_url": "https://agent.bajajauto.com/v1/events",
        "interest_manifesto": "Motorcycles, electric scooters, EV charging infrastructure, auto loans, and vehicle insurance partnerships."
    }
]

def seed():
    init_db()
    db = SessionLocal()
    if db.query(Agent).count() > 0:
        print("Agents already seeded!")
        db.close()
        return

    for data in INITIAL_AGENTS:
        emb = get_embedding(f"{data['industry_category']}: {data['interest_manifesto']}")
        agent = Agent(
            company_name=data["company_name"],
            industry_category=data["industry_category"],
            webhook_url=data["webhook_url"],
            interest_manifesto=data["interest_manifesto"],
            interest_embedding=json.dumps(emb)
        )
        db.add(agent)
    db.commit()
    db.close()
    print("Successfully seeded 5 enterprise AI agents!")

if __name__ == "__main__":
    seed()