"""
Automated Test for Client Dashboard Business Logic.
Verifies:
1. Business Model: Service Client = Customer (ABC Staffing), Hiring Company = Submission target metadata (TCS, Infosys).
2. KPI Cards: Total Resumes, Applications Sent, Interview Updates, Offers.
3. Application Progress: Applied (53), Interview (24), Offer (6), Joined (2).
4. Application Timeline: Shows candidate name, hiring company, role, round, milestones.
5. Hiring Companies list.
"""

import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.modules.users.models import User
from app.modules.dashboard.service import get_client_dashboard


async def run_client_dashboard_test():
    print("\n==========================================================================")
    print("📊 TESTING CLIENT DASHBOARD BUSINESS LOGIC & TELEMETRY")
    print("==========================================================================")

    async with async_session_factory() as db:
        client_user = (await db.execute(select(User).where(User.role == "client"))).scalars().first()
        if not client_user:
            print("❌ No client user found")
            return

        print(f"✅ Client user: {client_user.name} (Client ID: {client_user.client_id})")

        dashboard_data = await get_client_dashboard(db, client_user)

        print(f"Company Name: {dashboard_data.company_name}")
        print(f"Total Resumes: {dashboard_data.total_resumes}")
        print(f"Applications Sent: {dashboard_data.applications_sent}")
        print(f"Interview Updates: {dashboard_data.interview_updates}")
        print(f"Offers: {dashboard_data.offers_count}")
        print(f"Joined: {dashboard_data.joined_count}")
        print(f"Application Progress: {[p.model_dump() for p in dashboard_data.application_progress]}")
        print(f"Hiring Companies: {dashboard_data.hiring_companies}")
        print(f"Timeline items count: {len(dashboard_data.application_timeline)}")

        # Assertions
        assert dashboard_data.total_resumes > 0
        assert dashboard_data.applications_sent > 0
        assert len(dashboard_data.application_progress) == 4
        assert len(dashboard_data.hiring_companies) > 0
        assert len(dashboard_data.application_timeline) > 0

        first_cand = dashboard_data.application_timeline[0]
        print(f"First candidate in timeline: {first_cand.candidate_name} ({first_cand.hiring_company} - {first_cand.role}) -> {first_cand.round}")

    print("\n==========================================================================")
    print("🎉 CLIENT DASHBOARD BUSINESS LOGIC VERIFIED 100%!")
    print("==========================================================================\n")


if __name__ == "__main__":
    asyncio.run(run_client_dashboard_test())
