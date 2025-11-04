"""
Mock data for testing the evaluation workflow
"""

from src.models import (
    OfferData,
    Education,
    Experience,
    Skill,
    Language,
    CandidateData,
    EvaluationRequest
)


def create_mock_good_candidate() -> EvaluationRequest:
    """Create high-fidelity mock data for a GOOD candidate (expected to be LIKED)."""
    
    mock_offer = OfferData(
        job_title="Senior Full-Stack Developer",
        company_name="TechCorp Innovation Labs",
        contract="full-time",
        type="hybrid",
        description="We are seeking an experienced Full-Stack Developer to join our innovative team building next-generation SaaS platforms. The ideal candidate will have strong expertise in modern web technologies, cloud architecture, and agile methodologies.",
        salary_range="€60,000 - €80,000",
        responsibilities="Design and develop scalable web applications, lead technical architecture decisions, mentor junior developers, collaborate with product teams, implement CI/CD pipelines, ensure code quality and best practices.",
        experience_required="5+ years of professional software development experience",
        mandatory_skills=["Python", "React", "Node.js", "PostgreSQL", "AWS", "Docker", "REST APIs"],
        nice_to_have_skills=["TypeScript", "GraphQL", "Kubernetes", "Redis", "Microservices", "LangChain"],
        mandatory_languages=["English", "Spanish"],
        nice_to_have_languages=["German"],
        preferred_companies=["Google", "Amazon", "Microsoft", "Meta", "Startup experience"],
        extra_requirements_to_consider="Experience with AI/ML integration is a plus. Must be comfortable with remote collaboration and agile workflows."
    )
    
    mock_candidate = CandidateData(
        heading="Senior Full-Stack Engineer | Python & React Specialist | Cloud Architecture",
        experience_years=7,
        educations=[
            Education(
                degree="Master of Science",
                name="Computer Science",
                institute="Universidad Politécnica de Madrid",
                start_date="2014",
                end_date="2016"
            ),
            Education(
                degree="Bachelor of Science",
                name="Software Engineering",
                institute="Universidad Complutense de Madrid",
                start_date="2010",
                end_date="2014"
            )
        ],
        experiences=[
            Experience(
                role="Senior Full-Stack Developer",
                company="InnovateTech Solutions",
                description="Led development of cloud-based SaaS platform using Python/Django, React, and AWS. Architected microservices infrastructure with Docker and Kubernetes. Implemented CI/CD pipelines reducing deployment time by 60%. Mentored team of 4 junior developers.",
                start_date="2020-03",
                end_date="2024-10",
                duration="4 years 7 months"
            ),
            Experience(
                role="Full-Stack Developer",
                company="Digital Ventures Startup",
                description="Built and maintained multiple web applications using Python Flask, React, and PostgreSQL. Integrated third-party APIs and payment gateways. Worked in fast-paced agile environment with 2-week sprints. Reduced page load times by 40% through optimization.",
                start_date="2018-01",
                end_date="2020-02",
                duration="2 years 1 month"
            ),
            Experience(
                role="Junior Software Developer",
                company="WebDev Consulting",
                description="Developed frontend components with React and backend APIs with Node.js. Participated in code reviews and learned best practices. Worked with MongoDB and MySQL databases. Contributed to 15+ client projects.",
                start_date="2016-06",
                end_date="2017-12",
                duration="1 year 6 months"
            )
        ],
        skills=[
            Skill(name="Python", level="Expert"),
            Skill(name="React", level="Expert"),
            Skill(name="Node.js", level="Advanced"),
            Skill(name="PostgreSQL", level="Advanced"),
            Skill(name="AWS", level="Advanced"),
            Skill(name="Docker", level="Advanced"),
            Skill(name="TypeScript", level="Intermediate"),
            Skill(name="GraphQL", level="Intermediate"),
            Skill(name="Kubernetes", level="Intermediate"),
            Skill(name="REST APIs", level="Expert"),
            Skill(name="CI/CD", level="Advanced"),
            Skill(name="Microservices", level="Advanced"),
            Skill(name="Git", level="Expert"),
            Skill(name="Agile/Scrum", level="Advanced")
        ],
        languages=[
            Language(name="Spanish", level="native"),
            Language(name="English", level="fluent"),
            Language(name="French", level="intermediate")
        ]
    )
    
    return EvaluationRequest(offer=mock_offer, candidate=mock_candidate)


def create_mock_bad_candidate() -> EvaluationRequest:
    """Create high-fidelity mock data for a BAD candidate (expected to be REJECTED)."""
    
    mock_offer = OfferData(
        job_title="Senior Full-Stack Developer",
        company_name="TechCorp Innovation Labs",
        contract="full-time",
        type="hybrid",
        description="We are seeking an experienced Full-Stack Developer to join our innovative team building next-generation SaaS platforms. The ideal candidate will have strong expertise in modern web technologies, cloud architecture, and agile methodologies.",
        salary_range="€60,000 - €80,000",
        responsibilities="Design and develop scalable web applications, lead technical architecture decisions, mentor junior developers, collaborate with product teams, implement CI/CD pipelines, ensure code quality and best practices.",
        experience_required="5+ years of professional software development experience",
        mandatory_skills=["Python", "React", "Node.js", "PostgreSQL", "AWS", "Docker", "REST APIs"],
        nice_to_have_skills=["TypeScript", "GraphQL", "Kubernetes", "Redis", "Microservices", "LangChain"],
        mandatory_languages=["English", "Spanish"],
        nice_to_have_languages=["German"],
        preferred_companies=["Google", "Amazon", "Microsoft", "Meta", "Startup experience"],
        extra_requirements_to_consider="Experience with AI/ML integration is a plus. Must be comfortable with remote collaboration and agile workflows."
    )
    
    # Poor fit candidate: limited experience, missing key skills, frequent job changes
    mock_candidate = CandidateData(
        heading="Junior PHP Developer | WordPress Specialist | Freelancer",
        experience_years=2,
        educations=[
            Education(
                degree="Associate Degree",
                name="Web Design",
                institute="Local Community College",
                start_date="2020",
                end_date="2022"
            )
        ],
        experiences=[
            Experience(
                role="PHP Developer",
                company="Small Web Agency",
                description="Developed WordPress websites for small businesses. Created custom themes and plugins. Basic HTML/CSS work. No experience with modern frameworks or cloud platforms.",
                start_date="2023-01",
                end_date="2024-08",
                duration="1 year 7 months"
            ),
            Experience(
                role="Web Developer Intern",
                company="Digital Marketing Agency",
                description="Assisted with website maintenance. Updated content on client websites. Basic jQuery scripting. Used cPanel for hosting management.",
                start_date="2022-06",
                end_date="2022-12",
                duration="6 months"
            )
        ],
        skills=[
            Skill(name="PHP", level="Intermediate"),
            Skill(name="WordPress", level="Advanced"),
            Skill(name="HTML", level="Advanced"),
            Skill(name="CSS", level="Intermediate"),
            Skill(name="jQuery", level="Basic"),
            Skill(name="MySQL", level="Basic"),
            Skill(name="cPanel", level="Intermediate")
        ],
        languages=[
            Language(name="English", level="intermediate"),
            Language(name="Italian", level="native")
        ]
    )
    
    return EvaluationRequest(offer=mock_offer, candidate=mock_candidate)

