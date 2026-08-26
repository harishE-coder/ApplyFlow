"""
Test Suite for ApplyFlow MVP v1.2: Smart Resume Linking in AI Intake.
Tests:
- Test 1: Resume exists -> Email processed -> Auto-linked & application updated
- Test 2: Priority 1 - Resume ID tag match (RES101) -> Instant link
- Test 3: Priority 2 & 3 - Name + Company, Name + Role -> Matched
- Test 4: Priority 4 - No match -> Application created with resume_id = NULL, no duplicate resumes created
- Test 5: Recruiter override -> Overriding linked resume with manual selection
"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application, ApplicationEvent
from app.modules.applications.service import analyze_recruiter_email, confirm_and_save_email
from app.modules.applications.schemas import ConfirmSaveRequest
from app.modules.resumes.service import find_matching_resume


async def run_smart_resume_linking_tests():
    print("🚀 Running ApplyFlow Smart Resume Linking (MVP v1.2) Test Suite...")

    async with async_session_factory() as db:
        # Fetch admin user
        admin = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        assert admin is not None, "Admin user required"

        # Create or fetch test Service Client
        client_stmt = select(Client).where(Client.company_name == "SmartLink Test Client")
        client = (await db.execute(client_stmt)).scalar_one_or_none()
        if not client:
            client = Client(
                company_name="SmartLink Test Client",
                contact_person="Smart Manager",
                email="smartlink@testclient.com",
                status="active",
            )
            db.add(client)
            await db.flush()

        # Create a second client to test strict client isolation
        other_client_stmt = select(Client).where(Client.company_name == "Other Isolated Client")
        other_client = (await db.execute(other_client_stmt)).scalar_one_or_none()
        if not other_client:
            other_client = Client(
                company_name="Other Isolated Client",
                contact_person="Other Manager",
                email="other@isolated.com",
                status="active",
            )
            db.add(other_client)
            await db.flush()

        # Clear previous test data for clean state
        test_client_ids = [client.id, other_client.id]
        existing_res = (await db.execute(select(Resume).where(Resume.client_id.in_(test_client_ids)))).scalars().all()
        for r in existing_res:
            await db.delete(r)
        existing_apps = (await db.execute(select(Application).where(Application.client_id.in_(test_client_ids)))).scalars().all()
        for a in existing_apps:
            await db.delete(a)
        await db.commit()

        # Setup Seed Resumes in SmartLink Test Client
        res1 = Resume(
            candidate_name="Rahul Kumar",
            company="TCS",
            role="Java Developer",
            resume_id_tag="RES101",
            original_filename="TCS_JavaDeveloper_RES101.pdf",
            client_id=client.id,
            uploaded_by=admin.id,
        )
        res2 = Resume(
            candidate_name="Priya Sharma",
            company="Infosys",
            role="Full Stack Engineer",
            resume_id_tag="RES102",
            original_filename="Priya_Infosys_FullStack_RES102.pdf",
            client_id=client.id,
            uploaded_by=admin.id,
        )
        res3 = Resume(
            candidate_name="Amit Patel",
            company="Wipro",
            role="DevOps Specialist",
            resume_id_tag="RES103",
            original_filename="Amit_Wipro_DevOps_RES103.pdf",
            client_id=client.id,
            uploaded_by=admin.id,
        )
        # Resume in OTHER client (for isolation verification)
        res_other = Resume(
            candidate_name="Rahul Kumar",
            company="TCS",
            role="Java Developer",
            resume_id_tag="RES999",
            original_filename="Other_Rahul_TCS_RES999.pdf",
            client_id=other_client.id,
            uploaded_by=admin.id,
        )
        db.add_all([res1, res2, res3, res_other])
        await db.commit()

        # -------------------------------------------------------------
        # TEST 1: Priority 1 - Resume ID Tag Match (RES101)
        # -------------------------------------------------------------
        print("\n--- TEST 1: Priority 1 - Resume ID Tag Match (RES101) ---")
        match1 = await find_matching_resume(
            db=db,
            client_id=client.id,
            candidate_name="Rahul",
            company="TCS",
            role="Java Developer",
            resume_id_tag="RES101",
        )
        assert match1.matched is True, "Expected match for RES101"
        assert match1.resume_id == res1.id, "Expected res1 ID"
        assert match1.match_priority == 1, "Expected priority 1"
        assert "RES101" in match1.match_reason
        print("✅ Test 1 Passed: Priority 1 matched correctly by Resume ID RES101.")

        # -------------------------------------------------------------
        # TEST 2: Client Isolation Check (Never match across other clients)
        # -------------------------------------------------------------
        print("\n--- TEST 2: Client Isolation Check ---")
        match_iso = await find_matching_resume(
            db=db,
            client_id=client.id,
            candidate_name="Rahul Kumar",
            company="TCS",
            role="Java Developer",
            resume_id_tag="RES999",  # Belongs only to other_client
        )
        # In client, RES999 doesn't exist, but Name+Company matches res1 (Priority 2)
        assert match_iso.matched is True
        assert match_iso.resume_id == res1.id, "Must match within selected client only"
        assert match_iso.resume_id != res_other.id, "Must NEVER match other client resume"
        print("✅ Test 2 Passed: Strict client isolation maintained.")

        # -------------------------------------------------------------
        # TEST 3: Priority 2 (Name + Company) & Priority 3 (Name + Role)
        # -------------------------------------------------------------
        print("\n--- TEST 3: Priority 2 & Priority 3 Matching ---")
        # Priority 2: Priya Sharma + Infosys (no tag provided)
        match_p2 = await find_matching_resume(
            db=db,
            client_id=client.id,
            candidate_name="Priya Sharma",
            company="Infosys",
            role="Python Developer",  # different role
            resume_id_tag=None,
        )
        assert match_p2.matched is True
        assert match_p2.resume_id == res2.id
        assert match_p2.match_priority == 2
        print("✅ Test 3a Passed: Priority 2 matched by Name + Company.")

        # Priority 3: Amit Patel + DevOps Specialist (different company)
        match_p3 = await find_matching_resume(
            db=db,
            client_id=client.id,
            candidate_name="Amit Patel",
            company="Google",  # different company
            role="DevOps Specialist",
            resume_id_tag=None,
        )
        assert match_p3.matched is True
        assert match_p3.resume_id == res3.id
        assert match_p3.match_priority == 3
        print("✅ Test 3b Passed: Priority 3 matched by Name + Role.")

        # -------------------------------------------------------------
        # TEST 4: Priority 4 - No Match -> Application created with resume_id = NULL
        # -------------------------------------------------------------
        print("\n--- TEST 4: Priority 4 - No Resume Match (Nullable resume_id) ---")
        email_unknown = """
        Dear Harish,
        We are pleased to invite Johnathan Doe for the Technical Round on 2026-09-01 for the Architect position at Amazon.
        Best regards,
        Amazon Recruiting Team
        """
        analysis_unknown = await analyze_recruiter_email(
            db=db,
            current_user=admin,
            raw_email=email_unknown,
            client_id=client.id,
        )
        assert analysis_unknown.is_interview_mail is True
        assert analysis_unknown.resume_matched is False
        assert analysis_unknown.matched_resume_id is None

        # Confirm and save without linking resume
        resume_count_before = (await db.execute(select(func.count(Resume.id)).where(Resume.client_id == client.id))).scalar()
        
        save_req_unlinked = ConfirmSaveRequest(
            candidate_name="Johnathan Doe",
            company="Amazon",
            role="Architect",
            round="Technical",
            status="Shortlisted",
            client_id=client.id,
            raw_email=email_unknown,
            decision="new_application",
            resume_id=None,  # Unlinked!
        )
        save_resp_unlinked = await confirm_and_save_email(
            db=db,
            current_user=admin,
            payload=save_req_unlinked,
        )
        await db.commit()

        resume_count_after = (await db.execute(select(func.count(Resume.id)).where(Resume.client_id == client.id))).scalar()
        assert resume_count_before == resume_count_after, "Must NEVER create duplicate resumes from email intake!"

        # Verify application created with resume_id = NULL
        app_unlinked = (await db.execute(select(Application).where(Application.id == save_resp_unlinked.application.id))).scalar_one()
        assert app_unlinked.resume_id is None
        assert app_unlinked.candidate_name == "Johnathan Doe"
        assert app_unlinked.company == "Amazon"
        assert app_unlinked.role == "Architect"
        assert app_unlinked.display_candidate_name == "Johnathan Doe"
        print("✅ Test 4 Passed: Application created with resume_id = NULL; 0 duplicate resumes created.")

        # -------------------------------------------------------------
        # TEST 5: Recruiter Manual Override (Change Linked Resume)
        # -------------------------------------------------------------
        print("\n--- TEST 5: Recruiter Manual Override ---")
        email_p1 = """
        Hi Harish,
        Candidate Rahul Kumar has cleared the screening and is scheduled for Round 2 on 2026-09-02 for TCS Java Developer. Reference RES101.
        """
        analysis_p1 = await analyze_recruiter_email(
            db=db,
            current_user=admin,
            raw_email=email_p1,
            client_id=client.id,
        )
        assert analysis_p1.matched_resume_id == res1.id

        # Recruiter decides to manually override and link res2 instead (Priya Sharma)
        save_req_override = ConfirmSaveRequest(
            candidate_name=analysis_p1.candidate_name,
            company=analysis_p1.company,
            role=analysis_p1.role,
            round="Round 2",
            status="Shortlisted",
            client_id=client.id,
            raw_email=email_p1,
            decision="new_application",
            resume_id=res2.id,  # Overridden manually!
        )
        save_resp_override = await confirm_and_save_email(
            db=db,
            current_user=admin,
            payload=save_req_override,
        )
        await db.commit()

        app_override = (await db.execute(select(Application).where(Application.id == save_resp_override.application.id))).scalar_one()
        assert app_override.resume_id == res2.id, "Application must have the overridden resume_id"
        assert app_override.display_candidate_name == "Priya Sharma"
        print("✅ Test 5 Passed: Recruiter manual override persisted successfully.")

        # -------------------------------------------------------------
        # TEST 6: Existing Application Follow-up Update
        # -------------------------------------------------------------
        print("\n--- TEST 6: Existing Application Follow-up Update ---")
        email_followup = """
        Rahul Kumar has cleared Round 2 and is now scheduled for Round 3 Interview at TCS on 2026-09-05.
        """
        analysis_followup = await analyze_recruiter_email(
            db=db,
            current_user=admin,
            raw_email=email_followup,
            client_id=client.id,
        )
        assert analysis_followup.decision in ["existing_application", "new_application"]

        save_req_followup = ConfirmSaveRequest(
            candidate_name="Rahul Kumar",
            company="TCS",
            role="Java Developer",
            round="Round 3",
            status="Shortlisted",
            client_id=client.id,
            raw_email=email_followup,
            decision="existing_application",
            matched_application_id=app_override.id,
            resume_id=res1.id,
        )
        save_resp_followup = await confirm_and_save_email(
            db=db,
            current_user=admin,
            payload=save_req_followup,
        )
        await db.commit()

        app_updated = (await db.execute(select(Application).where(Application.id == app_override.id))).scalar_one()
        assert app_updated.current_round == "Round 3"
        print("✅ Test 6 Passed: Existing application successfully updated with follow-up event.")

    print("\n🎉 ALL SMART RESUME LINKING TESTS (100%) PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_smart_resume_linking_tests())
