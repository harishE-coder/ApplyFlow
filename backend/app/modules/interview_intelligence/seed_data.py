"""
Golden seed training data for bootstrap model training.
Provides diverse, realistic recruiter email templates for all 13 label categories.
"""

from app.modules.interview_intelligence.schemas import EmailCategory

GOLDEN_SEED_TEMPLATES = [
    # 1. INTERVIEW
    {
        "label": EmailCategory.INTERVIEW.value,
        "email": {
            "subject": "Interview Invitation: Amazon Software Development Engineer (SDE II)",
            "sender_email": "recruiting@amazon.jobs",
            "sender_domain": "amazon.jobs",
            "links": ["https://amazon.zoom.us/j/123456789", "https://calendly.com/amazon-tech/sde2"],
            "attachment_names": ["interview_guide.pdf", "invite.ics"],
            "body": "Hi Harish, we were very impressed by your background and would like to invite you for a 60-minute Technical Round 1 with one of our Senior Principal Engineers. Please choose a slot from the calendar link or join Zoom.",
        },
    },
    {
        "label": EmailCategory.INTERVIEW.value,
        "email": {
            "subject": "Google Interview Schedule - Senior Software Engineer",
            "sender_email": "tech-recruiting@google.com",
            "sender_domain": "google.com",
            "links": ["https://meet.google.com/xyz-abcd-efg"],
            "attachment_names": ["google_interview_prep.pdf"],
            "body": "Dear candidate, your technical interview is scheduled for Friday at 3:00 PM PST. The session will cover algorithms, data structures, and system design.",
        },
    },
    {
        "label": EmailCategory.INTERVIEW.value,
        "email": {
            "subject": "Microsoft Technical Interview Round 2",
            "sender_email": "recruiter@microsoft.com",
            "sender_domain": "microsoft.com",
            "links": ["https://teams.microsoft.com/l/meetup-join/19928374"],
            "attachment_names": ["invite.ics"],
            "body": "Congratulations on completing Round 1! We are pleased to advance you to Technical Round 2 with our engineering manager on Microsoft Teams.",
        },
    },

    # 2. HR_SCREENING
    {
        "label": EmailCategory.HR_SCREENING.value,
        "email": {
            "subject": "Initial Recruiter Chat - ApplyFlow / Meta",
            "sender_email": "talent@meta.com",
            "sender_domain": "meta.com",
            "links": ["https://calendly.com/recruiter-sarah/30min"],
            "attachment_names": [],
            "body": "Hello, thanks for applying for our Full Stack Developer position. I'd love to schedule a quick 20-30 minute phone/video screen to discuss your background and compensation expectations.",
        },
    },
    {
        "label": EmailCategory.HR_SCREENING.value,
        "email": {
            "subject": "HR Screening Call - Stripe Frontend Engineer",
            "sender_email": "hr@stripe.com",
            "sender_domain": "stripe.com",
            "links": ["https://calendly.com/stripe-hr/screening"],
            "attachment_names": [],
            "body": "Hi there, I am an HR recruiter at Stripe. I reviewed your resume and would like to set up an introductory chat about our culture, team structure, and your career goals.",
        },
    },

    # 3. TECHNICAL_ASSESSMENT
    {
        "label": EmailCategory.TECHNICAL_ASSESSMENT.value,
        "email": {
            "subject": "Snowflake Online Technical Assessment - HackerRank",
            "sender_email": "no-reply@hackerrank.com",
            "sender_domain": "hackerrank.com",
            "links": ["https://hackerrank.com/tests/snowflake-sde-oa-992"],
            "attachment_names": [],
            "body": "You have been invited by Snowflake to complete an online coding assessment on HackerRank. You will have 90 minutes to complete 3 programming questions. The link expires in 5 days.",
        },
    },
    {
        "label": EmailCategory.TECHNICAL_ASSESSMENT.value,
        "email": {
            "subject": "CodeSignal General Coding Assessment Invitation",
            "sender_email": "evaluations@codesignal.com",
            "sender_domain": "codesignal.com",
            "links": ["https://codesignal.com/assessment/token_xyz123"],
            "attachment_names": [],
            "body": "Uber has requested you take the CodeSignal General Coding Assessment (GCA). Please click below to start your timed proctored coding test.",
        },
    },
    {
        "label": EmailCategory.TECHNICAL_ASSESSMENT.value,
        "email": {
            "subject": "Codility Coding Challenge: Backend Developer",
            "sender_email": "testing@codility.com",
            "sender_domain": "codility.com",
            "links": ["https://codility.com/challenge/applyflow_test"],
            "attachment_names": [],
            "body": "Welcome to the automated programming test for Backend Developer. Ensure you have a stable internet connection before beginning.",
        },
    },

    # 4. TAKE_HOME
    {
        "label": EmailCategory.TAKE_HOME.value,
        "email": {
            "subject": "Take-Home Coding Challenge: Full-Stack Engineer",
            "sender_email": "engineering@linear.app",
            "sender_domain": "linear.app",
            "links": ["https://github.com/linear-challenges/fullstack-assignment"],
            "attachment_names": ["take_home_instructions.pdf"],
            "body": "Thank you for speaking with our team. For the next step, please find the take-home project attached. You have 72 hours to build the prototype and submit a pull request.",
        },
    },
    {
        "label": EmailCategory.TAKE_HOME.value,
        "email": {
            "subject": "Design & Architecture Assignment - Vercel",
            "sender_email": "recruiting@vercel.com",
            "sender_domain": "vercel.com",
            "links": ["https://github.com/vercel/frontend-takehome"],
            "attachment_names": ["spec.pdf"],
            "body": "Please complete the attached take-home architectural assignment. Build a Next.js application that renders real-time analytics. Return your solution by Monday.",
        },
    },

    # 5. INTERVIEW_CONFIRMATION
    {
        "label": EmailCategory.INTERVIEW_CONFIRMATION.value,
        "email": {
            "subject": "Confirmed: Technical Interview on Thursday, Sep 4 at 11:00 AM",
            "sender_email": "calendar-notification@google.com",
            "sender_domain": "google.com",
            "links": ["https://meet.google.com/confirm-12345"],
            "attachment_names": ["invite.ics"],
            "body": "This is a confirmation that your interview with Dave (Staff Engineer) has been successfully booked for Thursday at 11:00 AM EST. The calendar invitation is attached.",
        },
    },

    # 6. INTERVIEW_RESCHEDULE
    {
        "label": EmailCategory.INTERVIEW_RESCHEDULE.value,
        "email": {
            "subject": "Reschedule Request: Amazon Technical Interview",
            "sender_email": "recruiter@amazon.jobs",
            "sender_domain": "amazon.jobs",
            "links": ["https://calendly.com/reschedule/amazon-sde"],
            "attachment_names": [],
            "body": "Unfortunately, our interviewer has an urgent conflict and needs to reschedule your upcoming technical interview. Please choose a new time slot at your earliest convenience.",
        },
    },

    # 7. INTERVIEW_CANCELLED
    {
        "label": EmailCategory.INTERVIEW_CANCELLED.value,
        "email": {
            "subject": "Cancelled: Frontend Developer Interview",
            "sender_email": "notifications@greenhouse.io",
            "sender_domain": "greenhouse.io",
            "links": [],
            "attachment_names": [],
            "body": "We are writing to notify you that the scheduled interview has been cancelled due to the role being filled internally or placed on indefinite hiring freeze.",
        },
    },

    # 8. RECRUITER_FOLLOWUP
    {
        "label": EmailCategory.RECRUITER_FOLLOWUP.value,
        "email": {
            "subject": "Following up on your Datadog application",
            "sender_email": "alex@datadog.com",
            "sender_domain": "datadog.com",
            "links": [],
            "attachment_names": [],
            "body": "Hi, just following up to check on your availability this week and see if you had any questions regarding the team or role before we finalize the upcoming rounds.",
        },
    },

    # 9. APPLICATION_UPDATE
    {
        "label": EmailCategory.APPLICATION_UPDATE.value,
        "email": {
            "subject": "Application Status Update: Apple Software Engineer",
            "sender_email": "jobs@apple.com",
            "sender_domain": "apple.com",
            "links": ["https://jobs.apple.com/profile/status"],
            "attachment_names": [],
            "body": "Thank you for submitting your application. We wanted to let you know that your resume has been passed along to the hiring team for further review.",
        },
    },

    # 10. RESPONSE_REQUEST
    {
        "label": EmailCategory.RESPONSE_REQUEST.value,
        "email": {
            "subject": "Action Required: Please provide transcripts and work authorization",
            "sender_email": "onboarding@bloomberg.com",
            "sender_domain": "bloomberg.com",
            "links": ["https://careers.bloomberg.com/portal/upload-docs"],
            "attachment_names": [],
            "body": "Before we can proceed to the final hiring committee, please upload your official university transcripts and proof of work authorization using the link above.",
        },
    },

    # 11. REJECTION
    {
        "label": EmailCategory.REJECTION.value,
        "email": {
            "subject": "Thank you for your interest in Netflix",
            "sender_email": "talent@netflix.com",
            "sender_domain": "netflix.com",
            "links": [],
            "attachment_names": [],
            "body": "Thank you for taking the time to interview with Netflix. While we were impressed by your skills, we have decided to move forward with another candidate whose background more closely matches our immediate needs.",
        },
    },
    {
        "label": EmailCategory.REJECTION.value,
        "email": {
            "subject": "Your application to Spotify",
            "sender_email": "no-reply@spotify.com",
            "sender_domain": "spotify.com",
            "links": [],
            "attachment_names": [],
            "body": "We appreciate your interest in Spotify. Unfortunately, after careful consideration, we will not be moving forward with your application at this time.",
        },
    },

    # 12. NON_IT
    {
        "label": EmailCategory.NON_IT.value,
        "email": {
            "subject": "Store Associate Opportunity - Retail Mart",
            "sender_email": "jobs@retailmart.com",
            "sender_domain": "retailmart.com",
            "links": [],
            "attachment_names": [],
            "body": "We have open shifts for cashier and floor associates at our downtown warehouse. No technical experience required. Walk-in interviews every Monday.",
        },
    },

    # 13. OTHER
    {
        "label": EmailCategory.OTHER.value,
        "email": {
            "subject": "Your monthly cloud billing invoice",
            "sender_email": "billing@cloudflare.com",
            "sender_domain": "cloudflare.com",
            "links": ["https://dash.cloudflare.com/billing"],
            "attachment_names": ["invoice_aug2026.pdf"],
            "body": "Your invoice for Cloudflare R2 and Workers services is attached. The total amount has been charged to your default payment card.",
        },
    },
]
