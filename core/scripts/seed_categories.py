"""
Idempotent seed script for the job_categories table.

Run from the project root:
    python -m core.scripts.seed_categories

Idempotency: each category is looked up by slug before insertion.
Existing rows are left untouched, so re-running is safe.
"""

import asyncio

from sqlalchemy import select

from core.db.database import AsyncSessionLocal
from core.db.models import JobCategory

SEED_CATEGORIES = [
    {
        "slug": "backend-developer-python",
        "display_name": "Backend Developer (Python)",
        "description": (
            "Designs and maintains server-side APIs, microservices, and data "
            "pipelines using Python frameworks such as FastAPI, Django, or Flask. "
            "Works closely with databases, caching layers, and cloud infrastructure."
        ),
        "required_skills": [
            "Python",
            "FastAPI / Django / Flask",
            "REST API design",
            "SQL (PostgreSQL / MySQL)",
            "Docker",
            "Redis",
            "CI/CD pipelines",
            "Git",
        ],
    },
    {
        "slug": "frontend-developer-react",
        "display_name": "Frontend Developer (React)",
        "description": (
            "Builds responsive, accessible web interfaces using React and the "
            "modern JavaScript ecosystem. Focuses on component architecture, "
            "state management, and performance optimisation."
        ),
        "required_skills": [
            "React",
            "TypeScript",
            "HTML5 / CSS3",
            "State management (Redux / Zustand)",
            "REST / GraphQL consumption",
            "Webpack / Vite",
            "Testing (Jest / RTL)",
            "Git",
        ],
    },
    {
        "slug": "fullstack-developer",
        "display_name": "Full-Stack Developer",
        "description": (
            "Owns both frontend and backend layers of a web application. "
            "Comfortable moving between React / Next.js on the client side and "
            "Node.js, Python, or similar on the server side."
        ),
        "required_skills": [
            "React / Next.js",
            "Node.js or Python",
            "REST API design",
            "SQL or NoSQL databases",
            "Docker",
            "TypeScript",
            "Git",
        ],
    },
    {
        "slug": "mobile-developer",
        "display_name": "Mobile Developer",
        "description": (
            "Creates native or cross-platform mobile applications for iOS and/or "
            "Android. May specialise in React Native, Flutter, Swift, or Kotlin."
        ),
        "required_skills": [
            "React Native or Flutter",
            "Swift or Kotlin (native)",
            "Mobile UX patterns",
            "REST API integration",
            "App Store / Play Store deployment",
            "Push notifications",
            "Offline-first design",
        ],
    },
    {
        "slug": "data-engineer",
        "display_name": "Data Engineer",
        "description": (
            "Builds and operates the data infrastructure: ingestion pipelines, "
            "data warehouses, lake houses, and orchestration. Bridges raw data "
            "sources with analytics and ML consumers."
        ),
        "required_skills": [
            "Python",
            "SQL",
            "Apache Spark or Flink",
            "Airflow / Prefect / Dagster",
            "dbt",
            "Cloud data warehouse (BigQuery / Snowflake / Redshift)",
            "Data modelling",
            "Docker / Kubernetes",
        ],
    },
    {
        "slug": "data-scientist",
        "display_name": "Data Scientist",
        "description": (
            "Extracts insights from data using statistical analysis, machine "
            "learning, and experimentation. Communicates findings to stakeholders "
            "and translates business questions into analytical problems."
        ),
        "required_skills": [
            "Python (pandas, scikit-learn, PyTorch / TensorFlow)",
            "Statistics and probability",
            "SQL",
            "Experiment design (A/B testing)",
            "Data visualisation",
            "Feature engineering",
            "MLflow or similar",
        ],
    },
    {
        "slug": "devops-engineer",
        "display_name": "DevOps / Platform Engineer",
        "description": (
            "Designs and manages cloud infrastructure, CI/CD pipelines, container "
            "orchestration, and observability platforms. Bridges development and "
            "operations to enable fast, reliable software delivery."
        ),
        "required_skills": [
            "Kubernetes",
            "Docker",
            "Terraform / Pulumi",
            "CI/CD (GitHub Actions / GitLab / Jenkins)",
            "AWS / GCP / Azure",
            "Linux",
            "Prometheus / Grafana",
            "Bash / Python scripting",
        ],
    },
    {
        "slug": "ux-ui-designer",
        "display_name": "UX/UI Designer",
        "description": (
            "Researches user needs, produces wireframes and prototypes, and "
            "defines visual design systems. Collaborates with engineers to "
            "translate designs into polished, accessible products."
        ),
        "required_skills": [
            "Figma",
            "User research methods",
            "Wireframing and prototyping",
            "Design systems",
            "Accessibility (WCAG)",
            "Information architecture",
            "Usability testing",
        ],
    },
    {
        "slug": "product-manager",
        "display_name": "Product Manager",
        "description": (
            "Owns the product roadmap, defines requirements, prioritises the "
            "backlog, and aligns cross-functional teams around delivering user "
            "and business value."
        ),
        "required_skills": [
            "Product strategy",
            "Agile / Scrum",
            "User story writing",
            "Stakeholder management",
            "Data-driven decision making",
            "Roadmap planning",
            "Competitive analysis",
            "OKR / KPI definition",
        ],
    },
    {
        "slug": "qa-tester",
        "display_name": "QA Engineer / Tester",
        "description": (
            "Ensures software quality through manual and automated testing "
            "strategies. Writes test plans, executes regression suites, and "
            "integrates quality gates into CI/CD pipelines."
        ),
        "required_skills": [
            "Test planning and execution",
            "Selenium / Playwright / Cypress",
            "API testing (Postman / REST Assured)",
            "Python or JavaScript for automation",
            "Bug tracking (Jira / Linear)",
            "CI/CD integration",
            "Performance testing (k6 / JMeter)",
        ],
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for data in SEED_CATEGORIES:
            existing = (
                await session.execute(
                    select(JobCategory).where(JobCategory.slug == data["slug"])
                )
            ).scalar_one_or_none()

            if existing:
                print(f"  skip  {data['slug']}")
                continue

            session.add(
                JobCategory(
                    slug=data["slug"],
                    display_name=data["display_name"],
                    description=data["description"],
                    required_skills=data["required_skills"],
                )
            )
            print(f"  add   {data['slug']}")

        await session.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
