"""
Seed Apply Flow database with realistic recruitment agency data matching the customer business model.

Entities:
- 3 Clients: ABC Staffing, Talent Hub, NextHire
- 5 Users:
  * Admin: admin@applyflow.com / admin123
  * Employee: harish@applyflow.com / harish123 (Assigned: ABC Staffing, Talent Hub)
  * Employee: recruiter2@applyflow.com / recruiter123 (Assigned: NextHire)
  * Client: john@abcstaffing.com / client123 (ABC Staffing)
  * Client: sarah@talenthub.com / client123 (Talent Hub)
- 8 Requirements across Clients for target companies (TCS, Infosys, Amazon, Google, etc.)
- 100 Resumes linked to Requirements
- 60 Applications
- Targets
- Activity Logs
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from app.core.database import async_session_factory, Base, engine
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
from app.modules.targets.models import Target
from app.modules.activity_logs.models import ActivityLog
from app.modules.attendance.models import Attendance
from app.modules.notifications.models import Notification


CANDIDATE_FIRST_NAMES = [
    "Harish", "Aarav", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Rohan",
    "Kavya", "Aditya", "Neha", "Siddharth", "Pooja", "Arjun", "Divya", "Karan",
    "Meera", "Varun", "Ritu", "Deepak", "Swati", "Manish", "Shreya", "Amit",
    "Nisha", "Gaurav", "Tanvi", "Sanjay", "Anjali", "Naveen", "Ishaan", "Tara"
]

CANDIDATE_LAST_NAMES = [
    "Sharma", "Patel", "Reddy", "Verma", "Iyer", "Nair", "Gupta", "Kumar",
    "Singh", "Mehta", "Joshi", "Bose", "Rao", "Deshmukh", "Chopra", "Das",
    "Kapoor", "Bhat", "Kulkarni", "Menon", "Saxena", "Choudhury", "Pillai", "Shah"
]


async def seed_database():
    print("🌱 Seeding Apply Flow database with new business model...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


    async with async_session_factory() as db:
        # Clear existing tables in correct FK order
        await db.execute(delete(ActivityLog))
        await db.execute(delete(Target))
        await db.execute(delete(Application))
        await db.execute(delete(Resume))
        await db.execute(delete(Requirement))
        await db.execute(delete(EmployeeClient))
        await db.execute(delete(User))
        await db.execute(delete(Client))
        await db.flush()

        # 1. Create Clients (Our Customers)
        clients_data = [
            {
                "company_name": "ABC Staffing",
                "contact_person": "John Doe",
                "email": "john@abcstaffing.com",
                "phone": "+1-555-0101",
            },
            {
                "company_name": "Talent Hub",
                "contact_person": "Sarah Connor",
                "email": "sarah@talenthub.com",
                "phone": "+1-555-0102",
            },
            {
                "company_name": "NextHire",
                "contact_person": "David Miller",
                "email": "david@nexthire.com",
                "phone": "+1-555-0103",
            },
        ]
        client_map = {}
        for c in clients_data:
            client = Client(
                company_name=c["company_name"],
                contact_person=c["contact_person"],
                email=c["email"],
                phone=c["phone"],
                status="active",
            )
            db.add(client)
            await db.flush()
            client_map[c["company_name"]] = client

        print(f"  ✅ Created {len(client_map)} clients (ABC Staffing, Talent Hub, NextHire)")

        # 2. Create Users
        users_data = [
            {
                "name": "Admin User",
                "email": "admin@applyflow.com",
                "password": "admin123",
                "role": "admin",
                "client_id": None,
            },
            {
                "name": "Harish Recruiter",
                "email": "harish@applyflow.com",
                "password": "harish123",
                "role": "employee",
                "client_id": None,
            },
            {
                "name": "Recruiter Two",
                "email": "recruiter2@applyflow.com",
                "password": "recruiter123",
                "role": "employee",
                "client_id": None,
            },
            {
                "name": "Punith SubAdmin",
                "email": "punith@applyflow.com",
                "password": "punith123",
                "role": "sub_admin",
                "client_id": None,
            },
            {
                "name": "John Doe (ABC Staffing)",
                "email": "john@abcstaffing.com",
                "password": "client123",
                "role": "client",
                "client_id": client_map["ABC Staffing"].id,
            },
            {
                "name": "Sarah Connor (Talent Hub)",
                "email": "sarah@talenthub.com",
                "password": "client123",
                "role": "client",
                "client_id": client_map["Talent Hub"].id,
            },
        ]

        user_map = {}
        for u in users_data:
            user = User(
                name=u["name"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
                client_id=u["client_id"],
            )
            db.add(user)
            await db.flush()
            user_map[u["email"]] = user

        print(f"  ✅ Created {len(user_map)} users")

        # 3. Employee-Client Assignments
        # Harish is Primary for ABC Staffing, Supporting for Talent Hub
        # Recruiter2 is Primary for NextHire
        assignments = [
            (user_map["harish@applyflow.com"].id, client_map["ABC Staffing"].id, True, True),
            (user_map["harish@applyflow.com"].id, client_map["Talent Hub"].id, False, True),
            (user_map["recruiter2@applyflow.com"].id, client_map["NextHire"].id, True, True),
        ]
        for emp_id, c_id, is_prim, is_act in assignments:
            db.add(EmployeeClient(
                employee_id=emp_id,
                client_id=c_id,
                is_primary=is_prim,
                active=is_act,
            ))
        await db.flush()
        print("  ✅ Created employee-client mappings with primary & active status")

        # 3.1 Sub-Admin Assignments (Punith -> ABC Staffing and Harish)
        from app.modules.users.models import SubAdminAssignment
        db.add(SubAdminAssignment(
            sub_admin_id=user_map["punith@applyflow.com"].id,
            client_id=client_map["ABC Staffing"].id,
            employee_id=user_map["harish@applyflow.com"].id,
            active=True,
        ))
        await db.flush()
        print("  ✅ Created Sub-Admin delegations (Punith -> ABC Staffing)")

        # 4. Create Requirements
        reqs_data = [
            # ABC Staffing
            {"client": "ABC Staffing", "company": "TCS", "role": "Java Developer", "role_code": "TCS-JAVA-01"},
            {"client": "ABC Staffing", "company": "Infosys", "role": "Python Developer", "role_code": "INF-PY-02"},
            {"client": "ABC Staffing", "company": "Amazon", "role": "SDE II", "role_code": "AMZ-SDE-03"},
            # Talent Hub
            {"client": "Talent Hub", "company": "Amazon", "role": "Frontend Engineer", "role_code": "AMZ-FE-01"},
            {"client": "Talent Hub", "company": "Google", "role": "Backend Engineer", "role_code": "GOOG-BE-02"},
            {"client": "Talent Hub", "company": "Microsoft", "role": "DevOps Engineer", "role_code": "MSFT-DO-03"},
            # NextHire
            {"client": "NextHire", "company": "Deloitte", "role": "Cloud Architect", "role_code": "DEL-CA-01"},
            {"client": "NextHire", "company": "Wipro", "role": "QA Engineer", "role_code": "WIP-QA-02"},
        ]

        requirement_list = []
        for r in reqs_data:
            req = Requirement(
                client_id=client_map[r["client"]].id,
                company=r["company"],
                role=r["role"],
                role_code=r["role_code"],
                status="active",
            )
            db.add(req)
            await db.flush()
            requirement_list.append(req)

        print(f"  ✅ Created {len(requirement_list)} requirements across clients")

        # 5. Create 100 Resumes
        resumes = []
        now = datetime.now(timezone.utc)
        for i in range(1, 101):
            req = random.choice(requirement_list)
            client = client_map["ABC Staffing"] if req.client_id == client_map["ABC Staffing"].id else (
                client_map["Talent Hub"] if req.client_id == client_map["Talent Hub"].id else client_map["NextHire"]
            )
            uploader = user_map["harish@applyflow.com"] if client.company_name in ["ABC Staffing", "Talent Hub"] else user_map["recruiter2@applyflow.com"]

            first = random.choice(CANDIDATE_FIRST_NAMES)
            last = random.choice(CANDIDATE_LAST_NAMES)
            candidate_name = f"{first} {last}"
            tag = f"RES{1000 + i}"
            clean_role = req.role.replace(" ", "")
            filename = f"{req.company}_{clean_role}_{tag}.pdf"

            days_ago = random.randint(0, 14)
            upload_date = now - timedelta(days=days_ago, hours=random.randint(1, 12))

            resume = Resume(
                display_seq=i,
                candidate_name=candidate_name,
                company=req.company,
                role=req.role,
                resume_id_tag=tag,
                requirement_id=req.id,
                client_id=client.id,
                uploaded_by=uploader.id,
                resume_date=upload_date.date(),
                client_notes="5+ years experience in production environments.",
                is_note_shared=(i % 3 == 0),
                drive_file_id=f"gdrive_stub_id_{i}",
                original_filename=filename,
                upload_date=upload_date,
            )
            db.add(resume)
            resumes.append(resume)

        await db.flush()
        print(f"  ✅ Created {len(resumes)} resumes")

        # 6. Create 60 Applications
        app_count = 0
        statuses = ["draft", "submitted", "shortlisted", "rejected", "hold", "closed"]
        weights = [0.10, 0.40, 0.25, 0.10, 0.10, 0.05]

        for i, resume in enumerate(resumes[:60]):
            status = random.choices(statuses, weights=weights)[0]
            days_ago = random.randint(0, 10)
            applied_date = now - timedelta(days=days_ago, hours=random.randint(1, 8))

            app = Application(
                resume_id=resume.id,
                requirement_id=resume.requirement_id,
                employee_id=resume.uploaded_by,
                client_id=resume.client_id,
                status=status,
                applied_date=applied_date,
            )
            db.add(app)
            app_count += 1

        await db.flush()
        print(f"  ✅ Created {app_count} applications")

        # 7. Create Targets
        targets_data = [
            (user_map["harish@applyflow.com"].id, client_map["ABC Staffing"].id, 25),
            (user_map["harish@applyflow.com"].id, client_map["Talent Hub"].id, 15),
            (user_map["recruiter2@applyflow.com"].id, client_map["NextHire"].id, 30),
        ]
        today = datetime.now().date()
        for emp_id, c_id, tgt in targets_data:
            db.add(
                Target(
                    employee_id=emp_id,
                    client_id=c_id,
                    daily_target=tgt,
                    effective_date=today,
                )
            )
        await db.flush()
        print("  ✅ Created daily targets")

        # 8. Create Attendance
        from app.modules.attendance.models import Attendance
        db.add(
            Attendance(
                employee_id=user_map["harish@applyflow.com"].id,
                work_date=today,
                check_in=now - timedelta(hours=4),
                check_out=None,
                total_hours=None,
            )
        )
        await db.flush()
        print("  ✅ Created active attendance session for Harish")

        # 9. Create Notifications
        from app.modules.notifications.models import Notification
        notifs = [
            (user_map["harish@applyflow.com"].id, "Primary Client Assigned", "You are assigned as Primary Recruiter for ABC Staffing.", "client_assigned"),
            (user_map["harish@applyflow.com"].id, "Daily Target Updated", "Your daily target for ABC Staffing is 25 applications.", "target_achieved"),
            (user_map["admin@applyflow.com"].id, "Attendance Active", "Harish checked in at 09:15 AM.", "info"),
        ]
        for uid, title, msg, ntype in notifs:
            db.add(Notification(user_id=uid, title=title, message=msg, type=ntype, is_read=False))
        await db.flush()
        print("  ✅ Created initial notifications")

        # 10. Activity logs
        db.add(
            ActivityLog(
                user_id=user_map["admin@applyflow.com"].id,
                action="system_initialized",
                details={"version": "2.0.0", "business_model": "applyflow_mvp_v1.1_frozen"},
            )
        )
        await db.flush()
        await db.commit()

    print("\n🎉 Database seeded successfully with ApplyFlow MVP v1.1 Frozen Model!")
    print("\n📋 Login credentials:")
    print("  Admin:      admin@applyflow.com / admin123")
    print("  Employee:   harish@applyflow.com / harish123 (Assigned: ABC Staffing, Talent Hub)")
    print("  Employee 2: recruiter2@applyflow.com / recruiter123 (Assigned: NextHire)")
    print("  Client:     john@abcstaffing.com / client123 (ABC Staffing)")
    print("  Client:     sarah@talenthub.com / client123 (Talent Hub)")


if __name__ == "__main__":
    asyncio.run(seed_database())
