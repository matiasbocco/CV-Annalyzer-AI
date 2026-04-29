"""Generate 10 realistic fake CVs as PDFs in /test_cvs/ using reportlab."""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

BLUE      = colors.HexColor("#1a3a6b")
LIGHT_BLUE = colors.HexColor("#2c5f9e")
GRAY      = colors.HexColor("#555555")
LIGHT_GRAY = colors.HexColor("#888888")
RULE_COLOR = colors.HexColor("#ccd6e8")

def build_styles():
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle("name",
            fontSize=22, fontName="Helvetica-Bold",
            textColor=BLUE, spaceAfter=2, leading=26),
        "title": ParagraphStyle("title",
            fontSize=11, fontName="Helvetica",
            textColor=LIGHT_BLUE, spaceAfter=6, leading=14),
        "contact": ParagraphStyle("contact",
            fontSize=8.5, fontName="Helvetica",
            textColor=GRAY, spaceAfter=10, leading=12),
        "section_header": ParagraphStyle("section_header",
            fontSize=10, fontName="Helvetica-Bold",
            textColor=BLUE, spaceBefore=10, spaceAfter=3,
            leading=13, textTransform="uppercase", letterSpacing=0.8),
        "job_title": ParagraphStyle("job_title",
            fontSize=10, fontName="Helvetica-Bold",
            textColor=colors.black, spaceBefore=6, spaceAfter=1, leading=13),
        "company": ParagraphStyle("company",
            fontSize=9, fontName="Helvetica",
            textColor=LIGHT_BLUE, spaceAfter=1, leading=12),
        "date_range": ParagraphStyle("date_range",
            fontSize=8.5, fontName="Helvetica",
            textColor=LIGHT_GRAY, spaceAfter=3, leading=11),
        "bullet": ParagraphStyle("bullet",
            fontSize=9, fontName="Helvetica",
            textColor=GRAY, leftIndent=12, bulletIndent=0,
            spaceBefore=1, spaceAfter=1, leading=12,
            bulletText="•"),
        "body": ParagraphStyle("body",
            fontSize=9, fontName="Helvetica",
            textColor=GRAY, spaceAfter=4, leading=13),
        "skill_label": ParagraphStyle("skill_label",
            fontSize=9, fontName="Helvetica-Bold",
            textColor=colors.black, spaceAfter=2, leading=12),
        "skill_value": ParagraphStyle("skill_value",
            fontSize=9, fontName="Helvetica",
            textColor=GRAY, spaceAfter=2, leading=12),
        "summary": ParagraphStyle("summary",
            fontSize=9.5, fontName="Helvetica",
            textColor=GRAY, spaceAfter=6, leading=14, firstLineIndent=0),
    }


def section(title, styles):
    items = []
    items.append(Spacer(1, 4))
    items.append(Paragraph(title, styles["section_header"]))
    items.append(HRFlowable(width="100%", thickness=0.8,
                             color=RULE_COLOR, spaceAfter=4))
    return items


def experience_block(job, company, period, location, bullets, styles):
    items = []
    items.append(Paragraph(job, styles["job_title"]))
    items.append(Paragraph(company, styles["company"]))
    items.append(Paragraph(f"{period}  ·  {location}", styles["date_range"]))
    for b in bullets:
        items.append(Paragraph(b, styles["bullet"]))
    return items


def skills_table(groups, styles, doc_width):
    """Two-column key: value table for skills."""
    rows = []
    for label, value in groups:
        rows.append([
            Paragraph(label, styles["skill_label"]),
            Paragraph(value, styles["skill_value"]),
        ])
    t = Table(rows, colWidths=[doc_width * 0.30, doc_width * 0.68])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def build_pdf(path, profile, styles, doc_width):
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    story = []

    # Header
    story.append(Paragraph(profile["name"], styles["name"]))
    story.append(Paragraph(profile["title"], styles["title"]))
    story.append(Paragraph(profile["contact"], styles["contact"]))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=BLUE, spaceAfter=6))

    # Profile summary
    story += section("Profile Summary", styles)
    story.append(Paragraph(profile["summary"], styles["summary"]))

    # Work experience
    story += section("Work Experience", styles)
    for exp in profile["experience"]:
        story += experience_block(
            exp["job"], exp["company"], exp["period"],
            exp["location"], exp["bullets"], styles)

    # Education
    story += section("Education", styles)
    for edu in profile["education"]:
        story.append(Paragraph(edu["degree"], styles["job_title"]))
        story.append(Paragraph(edu["school"], styles["company"]))
        story.append(Paragraph(edu["period"], styles["date_range"]))
        if edu.get("note"):
            story.append(Paragraph(edu["note"], styles["body"]))

    # Technical skills
    story += section("Technical Skills", styles)
    story.append(skills_table(profile["skills"], styles, doc_width))

    # Languages
    story += section("Languages", styles)
    story.append(skills_table(profile["languages"], styles, doc_width))

    # Projects
    story += section("Projects", styles)
    for proj in profile["projects"]:
        story.append(Paragraph(proj["name"], styles["job_title"]))
        story.append(Paragraph(proj["desc"], styles["body"]))

    doc.build(story)


# ---------------------------------------------------------------------------
# CV data
# ---------------------------------------------------------------------------

PROFILES = [
    # -----------------------------------------------------------------------
    # 1. Senior Backend Developer Python
    # -----------------------------------------------------------------------
    {
        "filename": "01_santiago_gomez_senior_backend.pdf",
        "name": "Santiago Gómez",
        "title": "Senior Backend Developer · Python",
        "contact": "santiago.gomez@email.com  ·  +54 9 11 4823-7610  ·  Buenos Aires, Argentina  ·  linkedin.com/in/santiagomez",
        "summary": (
            "Backend engineer with 8 years of experience designing and scaling distributed systems "
            "in high-traffic production environments. Deep expertise in Python, FastAPI, and Django. "
            "Led cross-functional teams of up to 6 engineers and drove migrations from monolith to microservices. "
            "Passionate about clean architecture, observability, and developer experience."
        ),
        "experience": [
            {
                "job": "Senior Backend Engineer",
                "company": "Mercado Digital S.A.",
                "period": "Mar 2021 – Present",
                "location": "Buenos Aires (hybrid)",
                "bullets": [
                    "Architected a real-time pricing microservice handling 12 000 req/s using FastAPI + Redis Streams.",
                    "Led migration of the monolithic checkout service to 4 independent microservices, reducing p99 latency by 34%.",
                    "Implemented blue-green deployments on EKS; zero-downtime releases across 3 production clusters.",
                    "Mentored 3 mid-level engineers through weekly code reviews and bi-weekly 1:1s.",
                ],
            },
            {
                "job": "Backend Developer",
                "company": "Softwave Latinoamérica",
                "period": "Jan 2019 – Feb 2021",
                "location": "Córdoba, Argentina",
                "bullets": [
                    "Built REST APIs with Django REST Framework for a fintech SaaS serving 40 000 SME clients.",
                    "Designed PostgreSQL schemas and query optimizations that cut report generation time by 60%.",
                    "Integrated AWS SQS/SNS for async notification pipelines; processed ~2 M events/day.",
                ],
            },
            {
                "job": "Python Developer",
                "company": "CodeFactory MX",
                "period": "Jun 2016 – Dec 2018",
                "location": "Remote (CDMX)",
                "bullets": [
                    "Developed Django web applications for e-commerce clients in the retail sector.",
                    "Containerised legacy applications using Docker, enabling consistent dev/prod parity.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Computer Science",
                "school": "Universidad de Buenos Aires (UBA)",
                "period": "2012 – 2016",
                "note": "Graduated with honors. Thesis on distributed consensus algorithms.",
            }
        ],
        "skills": [
            ("Languages", "Python (expert), SQL, Bash, Go (intermediate)"),
            ("Frameworks", "FastAPI, Django, Django REST Framework, Celery"),
            ("Databases", "PostgreSQL, Redis, MongoDB, DynamoDB"),
            ("Cloud & Infra", "AWS (EC2, RDS, S3, SQS, EKS), Docker, Kubernetes, Terraform"),
            ("Observability", "Prometheus, Grafana, OpenTelemetry, Datadog"),
            ("Practices", "TDD, DDD, Clean Architecture, CI/CD, Agile/Scrum"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Professional proficiency (C1)"),
            ("Portuguese", "Basic (A2)"),
        ],
        "projects": [
            {
                "name": "OpenQueue — Open-source task queue library",
                "desc": "Designed and published a lightweight async task queue for Python 3.11+, "
                        "built on asyncio and PostgreSQL LISTEN/NOTIFY. 340 GitHub stars.",
            },
            {
                "name": "PricingEngine prototype — internal R&D",
                "desc": "Proof-of-concept ML-augmented dynamic pricing engine using FastAPI + scikit-learn, "
                        "presented at an internal engineering summit.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 2. Semi-Senior Backend Developer Python
    # -----------------------------------------------------------------------
    {
        "filename": "02_valentina_rios_semisenioor_backend.pdf",
        "name": "Valentina Ríos",
        "title": "Semi-Senior Backend Developer · Python",
        "contact": "valentina.rios@email.com  ·  +57 310 452-8811  ·  Medellín, Colombia  ·  github.com/vale-rios",
        "summary": (
            "Backend developer with 4 years of experience building REST APIs and internal tools "
            "with Python and Flask. Comfortable owning features end-to-end: from database design "
            "to deployment. Currently expanding cloud skills toward AWS Solutions Architect certification."
        ),
        "experience": [
            {
                "job": "Backend Developer",
                "company": "Nexo Tecnología",
                "period": "Aug 2022 – Present",
                "location": "Medellín, Colombia (hybrid)",
                "bullets": [
                    "Built and maintained Flask APIs for a SaaS HR platform used by 200+ companies.",
                    "Designed MySQL schemas for payroll and attendance modules, improving query performance by 40%.",
                    "Set up CI/CD pipelines with GitHub Actions, reducing deployment friction for a team of 5.",
                    "Introduced unit and integration testing (pytest), raising code coverage from 18% to 71%.",
                ],
            },
            {
                "job": "Junior Python Developer",
                "company": "DataBridge Solutions",
                "period": "Mar 2020 – Jul 2022",
                "location": "Bogotá, Colombia",
                "bullets": [
                    "Developed ETL pipelines to ingest and normalize data from 12 third-party APIs.",
                    "Maintained internal Flask dashboards for operations teams.",
                    "Deployed applications on AWS EC2 using basic Nginx + Gunicorn setups.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Systems Engineering",
                "school": "Universidad EAFIT",
                "period": "2016 – 2020",
                "note": None,
            }
        ],
        "skills": [
            ("Languages", "Python, SQL, JavaScript (basic)"),
            ("Frameworks", "Flask, SQLAlchemy, pytest, Celery"),
            ("Databases", "MySQL, PostgreSQL, Redis"),
            ("Cloud & Infra", "AWS EC2/S3/RDS (basic), Docker, Nginx, GitHub Actions"),
            ("Practices", "REST API design, Git, Agile"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Intermediate (B2)"),
        ],
        "projects": [
            {
                "name": "Flask Boilerplate — open source",
                "desc": "Minimal Flask project template with JWT auth, SQLAlchemy, Alembic migrations, "
                        "and Docker Compose. Used as internal starter kit at Nexo.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 3. Junior Backend Developer Python
    # -----------------------------------------------------------------------
    {
        "filename": "03_mateo_herrera_junior_backend.pdf",
        "name": "Mateo Herrera",
        "title": "Junior Backend Developer · Python",
        "contact": "mateo.herrera95@gmail.com  ·  +54 9 351 612-4499  ·  Rosario, Argentina",
        "summary": (
            "Recently graduated full-stack bootcamp developer with 1.5 years of experience "
            "contributing to real projects as a freelancer and intern. "
            "Strong foundations in Python and FastAPI acquired through intensive study and personal projects. "
            "Eager to join a team where I can grow toward a mid-level role within 12–18 months."
        ),
        "experience": [
            {
                "job": "Backend Developer (Part-time / Freelance)",
                "company": "Agencia Web Creativa",
                "period": "Sep 2023 – Present",
                "location": "Remote",
                "bullets": [
                    "Built a FastAPI + SQLite REST API for a small e-commerce client (product catalog, cart, orders).",
                    "Deployed the app on a VPS using Docker and Nginx; maintained 99.5% uptime over 6 months.",
                    "Wrote API documentation with Swagger UI, adopted by the client's mobile team.",
                ],
            },
            {
                "job": "Intern — Backend",
                "company": "StartupRosario Incubadora",
                "period": "Mar 2023 – Aug 2023",
                "location": "Rosario, Argentina",
                "bullets": [
                    "Assisted senior developers in bug fixes and feature additions to a Django monolith.",
                    "Wrote unit tests for 2 modules, fixing 4 latent bugs in the process.",
                ],
            },
        ],
        "education": [
            {
                "degree": "Full-Stack Web Development Bootcamp",
                "school": "SoyHenry",
                "period": "Oct 2022 – Mar 2023",
                "note": "Completed 800-hour intensive program. Final project: collaborative task manager with FastAPI + React.",
            },
            {
                "degree": "Incomplete B.Sc. Information Systems (2 years completed)",
                "school": "Universidad Nacional de Rosario",
                "period": "2020 – 2022",
                "note": None,
            },
        ],
        "skills": [
            ("Languages", "Python, SQL, JavaScript (basic)"),
            ("Frameworks", "FastAPI, Django (basic), SQLAlchemy"),
            ("Databases", "PostgreSQL, SQLite"),
            ("Tools", "Docker, Git, GitHub, Postman, Linux CLI"),
            ("Practices", "REST APIs, OOP, basic TDD"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Intermediate (B1)"),
        ],
        "projects": [
            {
                "name": "TaskFlow — personal project",
                "desc": "Collaborative task manager with FastAPI backend, JWT authentication, "
                        "PostgreSQL, and a basic React frontend. Source on GitHub.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 4. Senior Frontend Developer React
    # -----------------------------------------------------------------------
    {
        "filename": "04_camila_vargas_senior_frontend.pdf",
        "name": "Camila Vargas",
        "title": "Senior Frontend Developer · React / TypeScript",
        "contact": "camila.vargas@email.com  ·  +56 9 8821-3344  ·  Santiago de Chile  ·  github.com/camilavargas",
        "summary": (
            "Frontend engineer with 7 years of experience building complex web applications "
            "at scale. Expert in React and TypeScript ecosystems. Track record of leading UI architecture "
            "decisions, establishing design systems, and improving Core Web Vitals. "
            "Comfortable working closely with product, design, and backend teams."
        ),
        "experience": [
            {
                "job": "Senior Frontend Engineer",
                "company": "Bsale Commerce",
                "period": "Feb 2021 – Present",
                "location": "Santiago (hybrid)",
                "bullets": [
                    "Led rebuild of the POS web app in Next.js + TypeScript, reducing bundle size by 45%.",
                    "Implemented a component design system (Radix UI + Tailwind) adopted across 3 product squads.",
                    "Set up Storybook + Chromatic visual regression testing, preventing 12 UI regressions in 6 months.",
                    "Mentored 2 junior frontend developers; ran bi-weekly frontend guild meetings.",
                ],
            },
            {
                "job": "Frontend Developer",
                "company": "Platanus Ventures",
                "period": "May 2019 – Jan 2021",
                "location": "Santiago, Chile",
                "bullets": [
                    "Built multiple React SPAs for portfolio startups, from MVP to product-market fit.",
                    "Integrated Redux Toolkit for state management on a logistics dashboard with real-time WebSocket updates.",
                    "Improved Lighthouse score from 52 to 91 by implementing code-splitting and image optimization.",
                ],
            },
            {
                "job": "Junior Frontend Developer",
                "company": "Nuevos Medios Digital",
                "period": "Jan 2017 – Apr 2019",
                "location": "Santiago, Chile",
                "bullets": [
                    "Developed responsive landing pages and React components for media industry clients.",
                    "Migrated jQuery-based UI to React 16 across 3 internal tools.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Computer Engineering",
                "school": "Pontificia Universidad Católica de Chile",
                "period": "2013 – 2016",
                "note": None,
            }
        ],
        "skills": [
            ("Languages", "TypeScript, JavaScript (ES2023+), HTML5, CSS3"),
            ("Frameworks & Libs", "React 18, Next.js 14, Redux Toolkit, Tanstack Query, Zod"),
            ("Styling", "Tailwind CSS, CSS Modules, Radix UI, Framer Motion"),
            ("Testing", "Jest, React Testing Library, Playwright, Storybook"),
            ("Tooling", "Vite, Webpack, ESLint, Prettier, Turborepo"),
            ("Practices", "Micro-frontends, accessibility (WCAG 2.1), CI/CD, Agile"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Fluent (C1)"),
        ],
        "projects": [
            {
                "name": "Chisel UI — open-source design system",
                "desc": "Accessible React component library built with Radix UI and Tailwind, "
                        "published on npm. 180 stars on GitHub.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 5. Semi-Senior Frontend Developer React
    # -----------------------------------------------------------------------
    {
        "filename": "05_lucas_mendez_semisenioor_frontend.pdf",
        "name": "Lucas Méndez",
        "title": "Semi-Senior Frontend Developer · React",
        "contact": "lucasmendez.dev@gmail.com  ·  +598 99 341-7720  ·  Montevideo, Uruguay",
        "summary": (
            "Frontend developer with 3 years of experience building React applications "
            "for startups and SMEs. Solid understanding of component architecture, "
            "REST API integration, and responsive design. Expanding TypeScript skills "
            "and looking to work in a product-focused team with a strong engineering culture."
        ),
        "experience": [
            {
                "job": "Frontend Developer",
                "company": "Urutech Solutions",
                "period": "Jan 2022 – Present",
                "location": "Montevideo (remote)",
                "bullets": [
                    "Built and maintained React dashboards for 3 B2B SaaS products in the logistics sector.",
                    "Integrated REST APIs and handled async state management using React Query.",
                    "Migrated class components to hooks across a legacy codebase, improving readability.",
                    "Introduced basic TypeScript adoption in 2 new modules.",
                ],
            },
            {
                "job": "Junior Frontend Developer",
                "company": "Agencia Pixel",
                "period": "Jun 2021 – Dec 2021",
                "location": "Montevideo, Uruguay",
                "bullets": [
                    "Developed responsive landing pages and interactive UI components in React.",
                    "Collaborated with designers to implement pixel-perfect mockups from Figma.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Information Technology",
                "school": "Universidad ORT Uruguay",
                "period": "2018 – 2021",
                "note": None,
            }
        ],
        "skills": [
            ("Languages", "JavaScript, TypeScript (intermediate), HTML5, CSS3"),
            ("Frameworks & Libs", "React, React Router, React Query, Context API"),
            ("Styling", "Tailwind CSS, SASS, CSS Modules"),
            ("Testing", "Jest, React Testing Library (basic)"),
            ("Tools", "Git, Figma, Vite, Webpack, Postman"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Upper-Intermediate (B2)"),
        ],
        "projects": [
            {
                "name": "Budget Tracker — personal project",
                "desc": "React + Firebase app for personal expense tracking with charts, "
                        "category filters, and monthly summaries.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 6. UX/UI Designer
    # -----------------------------------------------------------------------
    {
        "filename": "06_daniela_castillo_uxui_designer.pdf",
        "name": "Daniela Castillo",
        "title": "UX / UI Designer",
        "contact": "daniela.castillo@email.com  ·  +52 55 8812-3390  ·  Ciudad de México  ·  behance.net/danielacastillo",
        "summary": (
            "Product designer with 5 years of experience transforming complex problems "
            "into intuitive, accessible interfaces. Expert in design systems, user research, "
            "and rapid prototyping. Worked across fintech, edtech, and e-commerce verticals. "
            "Strong collaborator with engineering and product teams."
        ),
        "experience": [
            {
                "job": "Senior UX/UI Designer",
                "company": "Kueski Pay",
                "period": "Apr 2022 – Present",
                "location": "CDMX (hybrid)",
                "bullets": [
                    "Own the end-to-end design of the credit application flow; reduced drop-off by 27% after redesign.",
                    "Maintain a Figma design system (120+ components) used across web and mobile squads.",
                    "Conduct moderated usability tests (6–8 sessions per sprint) and synthesize findings for PMs.",
                    "Collaborate with iOS and Android developers to ensure design handoff quality.",
                ],
            },
            {
                "job": "UX/UI Designer",
                "company": "Aprende Institute",
                "period": "Jan 2020 – Mar 2022",
                "location": "CDMX, México",
                "bullets": [
                    "Redesigned the student LMS dashboard, improving task completion rate by 35% in user testing.",
                    "Created information architecture and wireframes for a new mobile app (50k+ downloads).",
                    "Conducted card sorting and tree testing sessions to validate navigation structure.",
                ],
            },
            {
                "job": "Junior UX Designer",
                "company": "Tienda Digital MX",
                "period": "Jun 2019 – Dec 2019",
                "location": "CDMX, México",
                "bullets": [
                    "Designed responsive e-commerce UI components and A/B tested product page layouts.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Graphic Design",
                "school": "Universidad Iberoamericana",
                "period": "2015 – 2019",
                "note": None,
            },
            {
                "degree": "UX Design Certificate",
                "school": "Google / Coursera",
                "period": "2020",
                "note": None,
            },
        ],
        "skills": [
            ("Design Tools", "Figma (advanced), FigJam, Adobe XD, Illustrator, Photoshop"),
            ("Prototyping", "Figma Interactive, Principle, Lottie animations"),
            ("Research Methods", "Moderated/unmoderated usability testing, card sorting, interviews"),
            ("Delivery", "Design systems, redline specs, Zeplin / Dev Mode handoff"),
            ("Analytics", "Hotjar, Google Analytics (basic), Mixpanel"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Professional proficiency (C1)"),
        ],
        "projects": [
            {
                "name": "AccessFirst — redesign case study",
                "desc": "Pro-bono redesign of a government services portal focused on WCAG 2.1 AA compliance. "
                        "Documented on Behance with 2 000+ views.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 7. Senior Data Scientist
    # -----------------------------------------------------------------------
    {
        "filename": "07_andres_paredes_senior_data_scientist.pdf",
        "name": "Andrés Paredes",
        "title": "Senior Data Scientist",
        "contact": "andres.paredes@email.com  ·  +54 9 11 5533-9912  ·  Buenos Aires, Argentina  ·  kaggle.com/andresparedes",
        "summary": (
            "Data scientist with 6 years of experience delivering end-to-end ML solutions "
            "from problem framing to production deployment. Expertise in predictive modelling, "
            "NLP, and recommendation systems. Published 2 papers in applied ML conferences. "
            "Strong communicator: translates complex results for non-technical stakeholders."
        ),
        "experience": [
            {
                "job": "Senior Data Scientist",
                "company": "Naranja X",
                "period": "Jun 2021 – Present",
                "location": "Buenos Aires (hybrid)",
                "bullets": [
                    "Built a real-time credit risk model (XGBoost + SHAP) that reduced default rate by 1.8 pp.",
                    "Led development of a product recommendation engine (collaborative filtering + content-based); lifted CTR by 22%.",
                    "Set up MLflow experiment tracking and model registry for 4 data science squads.",
                    "Designed A/B testing framework used across 15+ model experiments per quarter.",
                ],
            },
            {
                "job": "Data Scientist",
                "company": "Satellogic",
                "period": "Jan 2019 – May 2021",
                "location": "Buenos Aires, Argentina",
                "bullets": [
                    "Developed CNN-based image segmentation models for satellite imagery analysis (TensorFlow).",
                    "Built automated data pipelines with Apache Airflow and dbt; reduced processing time by 50%.",
                    "Collaborated with the engineering team to serve models via a FastAPI microservice.",
                ],
            },
            {
                "job": "Junior Data Analyst",
                "company": "Consultora Analytics BA",
                "period": "Mar 2018 – Dec 2018",
                "location": "Buenos Aires, Argentina",
                "bullets": [
                    "Built dashboards and statistical reports for retail and FMCG clients using Python and Tableau.",
                ],
            },
        ],
        "education": [
            {
                "degree": "M.Sc. Data Science",
                "school": "Universidad de San Andrés",
                "period": "2017 – 2018",
                "note": None,
            },
            {
                "degree": "B.Sc. Mathematics",
                "school": "Universidad de Buenos Aires (UBA)",
                "period": "2012 – 2016",
                "note": None,
            },
        ],
        "skills": [
            ("Languages", "Python (expert), R (intermediate), SQL"),
            ("ML / DL", "scikit-learn, XGBoost, LightGBM, TensorFlow, PyTorch, Hugging Face"),
            ("Data Engineering", "Apache Airflow, dbt, pandas, PySpark (basic)"),
            ("Experimentation", "A/B testing, causal inference, MLflow, Weights & Biases"),
            ("Databases", "PostgreSQL, BigQuery, Redshift"),
            ("Practices", "CRISP-DM, reproducible research, model interpretability (SHAP)"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Fluent (C1)"),
        ],
        "projects": [
            {
                "name": "ChurnPredictor OSS",
                "desc": "Open-source customer churn prediction toolkit built with scikit-learn, "
                        "including automated feature engineering and threshold optimization. 210 GitHub stars.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 8. Junior Data Analyst
    # -----------------------------------------------------------------------
    {
        "filename": "08_isabella_torres_junior_data_analyst.pdf",
        "name": "Isabella Torres",
        "title": "Junior Data Analyst",
        "contact": "isabella.torres@email.com  ·  +57 312 889-4450  ·  Bogotá, Colombia",
        "summary": (
            "Recent economics graduate with 1 year of professional experience in data analysis. "
            "Proficient in SQL and Excel for business reporting; currently developing Python skills "
            "through online coursework and personal projects. Detail-oriented, fast learner, "
            "and comfortable presenting findings to non-technical audiences."
        ),
        "experience": [
            {
                "job": "Junior Data Analyst",
                "company": "Rappi",
                "period": "Feb 2024 – Present",
                "location": "Bogotá (remote)",
                "bullets": [
                    "Build weekly and monthly performance reports for the Groceries vertical using SQL + Looker.",
                    "Maintain and improve 8 dashboards tracking GMV, order frequency, and churn KPIs.",
                    "Collaborate with the operations team to identify anomalies in delivery time metrics.",
                    "Automated a recurring Excel report using Python + openpyxl, saving 3 hours/week.",
                ],
            },
            {
                "job": "Data & Analytics Intern",
                "company": "Grupo Éxito",
                "period": "Jul 2023 – Jan 2024",
                "location": "Bogotá, Colombia",
                "bullets": [
                    "Assisted senior analysts with data extraction and cleansing for monthly sales reports.",
                    "Created pivot tables and visualizations in Excel for category managers.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Economics",
                "school": "Universidad de los Andes",
                "period": "2019 – 2023",
                "note": "Graduated with distinction. Thesis on demand elasticity in Colombian e-commerce.",
            }
        ],
        "skills": [
            ("Analytics", "SQL (intermediate), Excel (advanced), Google Sheets"),
            ("BI Tools", "Looker, Google Data Studio, Power BI (basic)"),
            ("Programming", "Python (basic: pandas, matplotlib), R (basic, from coursework)"),
            ("Other", "Statistics, data storytelling, PowerPoint"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Intermediate (B2)"),
        ],
        "projects": [
            {
                "name": "Colombia E-commerce Trends — thesis",
                "desc": "Econometric analysis of price elasticity in online grocery shopping "
                        "using 3 years of transaction data. Published in the UAndes working papers series.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 9. Marketing Specialist
    # -----------------------------------------------------------------------
    {
        "filename": "09_sofia_jimenez_marketing_specialist.pdf",
        "name": "Sofía Jiménez",
        "title": "Digital Marketing Specialist",
        "contact": "sofia.jimenez@email.com  ·  +52 33 9920-1157  ·  Guadalajara, México",
        "summary": (
            "Digital marketing professional with 4 years of experience driving growth "
            "across paid media, SEO, and content strategy for B2C and B2B brands. "
            "Managed combined monthly ad budgets of $120 000 USD. "
            "Data-driven approach: strong at translating campaign metrics into actionable strategy. "
            "No technical background; works closely with product and engineering teams to align efforts."
        ),
        "experience": [
            {
                "job": "Digital Marketing Specialist",
                "company": "Clip México",
                "period": "Mar 2022 – Present",
                "location": "Guadalajara (hybrid)",
                "bullets": [
                    "Manage Google Ads and Meta Ads campaigns with a combined budget of $80k/month; average ROAS of 3.8×.",
                    "Led SEO strategy that grew organic traffic by 145% in 18 months (from 22k to 54k monthly sessions).",
                    "Develop content calendar and oversee production of blog articles, case studies, and social content.",
                    "Coordinate with the product team on in-app messaging and push notification strategy.",
                ],
            },
            {
                "job": "Marketing Analyst",
                "company": "Agencia Amplifica",
                "period": "Jan 2020 – Feb 2022",
                "location": "Guadalajara, México",
                "bullets": [
                    "Planned and executed paid social campaigns (Meta, TikTok) for 8 SME clients.",
                    "Produced monthly performance reports and strategic recommendations for account managers.",
                    "Conducted keyword research and on-page SEO audits for 3 e-commerce clients.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Marketing",
                "school": "ITESM — Tecnológico de Monterrey",
                "period": "2016 – 2020",
                "note": None,
            },
            {
                "degree": "Google Ads Certifications (Search, Display, Video)",
                "school": "Google Skillshop",
                "period": "2021 (renewed 2024)",
                "note": None,
            },
        ],
        "skills": [
            ("Paid Media", "Google Ads, Meta Ads Manager, TikTok Ads, LinkedIn Ads"),
            ("SEO / Content", "SEMrush, Ahrefs, Google Search Console, content strategy"),
            ("Analytics", "Google Analytics 4, Looker Studio, Meta Business Suite"),
            ("CRM & Email", "HubSpot, Mailchimp, ActiveCampaign"),
            ("Other", "Canva (basic design), Notion, project coordination"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Fluent (C1)"),
        ],
        "projects": [
            {
                "name": "SEO content strategy — Clip blog",
                "desc": "Designed and executed 12-month content plan targeting 80 high-intent keywords. "
                        "Resulted in 30 top-10 Google rankings and a 145% increase in organic traffic.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # 10. Senior DevOps Engineer
    # -----------------------------------------------------------------------
    {
        "filename": "10_rodrigo_fernandez_senior_devops.pdf",
        "name": "Rodrigo Fernández",
        "title": "Senior DevOps / Platform Engineer",
        "contact": "rodrigo.fernandez@email.com  ·  +54 9 11 7723-0081  ·  Buenos Aires, Argentina  ·  github.com/rodferops",
        "summary": (
            "Platform engineer with 9 years of experience building and operating large-scale "
            "cloud infrastructure on AWS. Deep expertise in Kubernetes, Terraform, and GitOps workflows. "
            "Reduced infrastructure costs by 40% at current employer through rightsizing and spot instance strategies. "
            "Committed to reliability, security, and developer self-service."
        ),
        "experience": [
            {
                "job": "Senior DevOps / Platform Engineer",
                "company": "OLX Argentina",
                "period": "Apr 2020 – Present",
                "location": "Buenos Aires (remote-first)",
                "bullets": [
                    "Own multi-account AWS organisation (14 accounts, $2.1M annual spend); reduced cost by 40% YoY.",
                    "Manage 3 production EKS clusters (300+ pods) with Argo CD GitOps deployments.",
                    "Authored 60+ Terraform modules; migrated all infrastructure from ClickOps to IaC in 8 months.",
                    "Built internal developer platform (Backstage + custom plugins) adopted by 80+ engineers.",
                    "Set up centralised observability stack: Prometheus, Grafana, Loki, Tempo.",
                ],
            },
            {
                "job": "DevOps Engineer",
                "company": "Wolox — now Accenture",
                "period": "Jan 2017 – Mar 2020",
                "location": "Buenos Aires, Argentina",
                "bullets": [
                    "Delivered CI/CD pipelines (Jenkins, later GitHub Actions) for 20+ client projects.",
                    "Deployed containerised applications on AWS ECS and EKS; introduced Helm chart standards.",
                    "Implemented HashiCorp Vault for secrets management across 8 microservice architectures.",
                ],
            },
            {
                "job": "Linux Systems Administrator",
                "company": "Globalink ISP",
                "period": "Feb 2015 – Dec 2016",
                "location": "Buenos Aires, Argentina",
                "bullets": [
                    "Administered 200+ Linux servers (CentOS/Ubuntu); automated patching with Ansible.",
                    "Set up network monitoring with Nagios; reduced mean time to detect incidents by 35%.",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.Sc. Network Engineering",
                "school": "Universidad Tecnológica Nacional (UTN)",
                "period": "2010 – 2015",
                "note": None,
            },
            {
                "degree": "AWS Solutions Architect Professional",
                "school": "Amazon Web Services",
                "period": "2019 (renewed 2022)",
                "note": None,
            },
            {
                "degree": "Certified Kubernetes Administrator (CKA)",
                "school": "CNCF / Linux Foundation",
                "period": "2021",
                "note": None,
            },
        ],
        "skills": [
            ("Cloud", "AWS (EKS, EC2, RDS, S3, IAM, VPC, Cost Explorer — expert)"),
            ("Containers & Orchestration", "Kubernetes, Helm, Argo CD, Argo Workflows, Docker"),
            ("IaC", "Terraform, Terragrunt, Ansible, Pulumi (basic)"),
            ("CI/CD", "GitHub Actions, Jenkins, GitLab CI, Argo CD"),
            ("Observability", "Prometheus, Grafana, Loki, Tempo, Datadog, PagerDuty"),
            ("Security", "Vault, SOPS, OPA/Kyverno, AWS IAM, network policies"),
            ("Languages", "Bash, Python, Go (basic)"),
        ],
        "languages": [
            ("Spanish", "Native"),
            ("English", "Fluent (C1)"),
        ],
        "projects": [
            {
                "name": "TerraStack — internal IaC toolkit",
                "desc": "Collection of opinionated Terraform modules for AWS (VPC, EKS, RDS, S3, IAM) "
                        "with automated security scanning via Checkov. Open-sourced on GitHub.",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    out_dir = Path(__file__).parent / "test_cvs"
    out_dir.mkdir(exist_ok=True)

    styles = build_styles()
    # usable page width (A4 width minus margins)
    doc_width = A4[0] - 36 * mm

    generated = []
    for profile in PROFILES:
        path = out_dir / profile["filename"]
        build_pdf(path, profile, styles, doc_width)
        generated.append(path.name)
        print(f"  OK  {path.name}")

    print(f"\n{len(generated)} PDFs generated in: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
