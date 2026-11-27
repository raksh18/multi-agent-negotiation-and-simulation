from copy import deepcopy

SCENARIOS = [
    {
        "id": "vendor-pricing",
        "name": "Vendor pricing negotiation",
        "description": "A procurement manager and a vendor sales lead negotiate price, volume, delivery and payment terms for a bulk purchase.",
        "default_max_rounds": 8,
        "parameters": [
            {
                "key": "product",
                "label": "Product or service being purchased",
                "type": "text",
                "required": True,
                "placeholder": "e.g. 500 business laptops"
            },
            {
                "key": "context",
                "label": "Additional context",
                "type": "textarea",
                "required": False,
                "placeholder": "Anything the agents should know, e.g. contract length or existing relationship"
            }
        ],
        "offer_fields": [
            {"key": "unit_price", "label": "Unit price", "type": "number"},
            {"key": "quantity", "label": "Quantity", "type": "number"},
            {"key": "delivery_days", "label": "Delivery time", "type": "number", "unit": "days"},
            {"key": "payment_terms_days", "label": "Payment terms", "type": "number", "unit": "days"},
            {"key": "warranty_months", "label": "Warranty", "type": "number", "unit": "months"}
        ],
        "agents": [
            {
                "id": "buyer",
                "name": "Procurement Manager",
                "role": "Buyer",
                "goals": ["Get the lowest total cost", "Secure delivery within the project deadline", "Obtain longer payment terms and warranty"],
                "constraints": ["Cannot exceed the approved purchasing budget", "Must have a signed agreement before the deadline"],
                "personality": "collaborative"
            },
            {
                "id": "vendor",
                "name": "Vendor Sales Lead",
                "role": "Vendor",
                "goals": ["Maximise margin per unit", "Win a large volume commitment", "Get paid quickly"],
                "constraints": ["Cannot sell below the minimum margin set by the company", "Limited production capacity per month"],
                "personality": "aggressive"
            }
        ]
    },
    {
        "id": "job-offer",
        "name": "Job offer negotiation",
        "description": "A candidate and a hiring manager negotiate compensation, benefits and working arrangements for a new role.",
        "default_max_rounds": 8,
        "parameters": [
            {
                "key": "role",
                "label": "Role being offered",
                "type": "text",
                "required": True,
                "placeholder": "e.g. Senior Software Engineer"
            },
            {
                "key": "context",
                "label": "Additional context",
                "type": "textarea",
                "required": False,
                "placeholder": "e.g. location, seniority, competing offers"
            }
        ],
        "offer_fields": [
            {"key": "base_salary", "label": "Base salary", "type": "number", "unit": "per year"},
            {"key": "bonus_percent", "label": "Annual bonus", "type": "number", "unit": "%"},
            {"key": "joining_bonus", "label": "Joining bonus", "type": "number"},
            {"key": "remote_days", "label": "Remote days", "type": "number", "unit": "per week"},
            {"key": "vacation_days", "label": "Vacation", "type": "number", "unit": "days per year"}
        ],
        "agents": [
            {
                "id": "candidate",
                "name": "Candidate",
                "role": "Job candidate",
                "goals": ["Maximise total compensation", "Get flexible working arrangements", "Secure a clear growth path"],
                "constraints": ["Has a competing offer to compare against", "Needs to answer before the offer expires"],
                "personality": "collaborative"
            },
            {
                "id": "employer",
                "name": "Hiring Manager",
                "role": "Employer",
                "goals": ["Hire the candidate within budget", "Keep pay consistent with the existing team", "Close the role quickly"],
                "constraints": ["Salary must stay inside the approved band", "Limited flexibility on bonus and equity"],
                "personality": "risk-averse"
            }
        ]
    },
    {
        "id": "project-budget",
        "name": "Project budget allocation",
        "description": "Stakeholders negotiate how a fixed total budget is split across project categories, based on the project requirements.",
        "default_max_rounds": 10,
        "parameters": [
            {
                "key": "total_budget",
                "label": "Total budget",
                "type": "number",
                "required": True,
                "placeholder": "e.g. 500000",
                "help": "The allocations must add up to this amount."
            },
            {
                "key": "project_requirements",
                "label": "Project requirements",
                "type": "textarea",
                "required": True,
                "placeholder": "Describe what the project must deliver, key deadlines and major cost areas"
            }
        ],
        "offer_fields": [
            {"key": "engineering", "label": "Engineering", "type": "number"},
            {"key": "design", "label": "Design", "type": "number"},
            {"key": "marketing", "label": "Marketing", "type": "number"},
            {"key": "operations", "label": "Operations", "type": "number"},
            {"key": "contingency", "label": "Contingency", "type": "number"}
        ],
        "agents": [
            {
                "id": "project-manager",
                "name": "Project Manager",
                "role": "Project owner",
                "goals": ["Fund every requirement needed to deliver on time", "Keep a contingency reserve"],
                "constraints": ["Allocations must add up to the total budget"],
                "personality": "collaborative"
            },
            {
                "id": "finance-lead",
                "name": "Finance Lead",
                "role": "Budget holder",
                "goals": ["Stay within the total budget", "Avoid over-funding any single category"],
                "constraints": ["Cannot approve spending above the total budget"],
                "personality": "risk-averse"
            },
            {
                "id": "department-head",
                "name": "Department Head",
                "role": "Largest cost stakeholder",
                "goals": ["Secure the largest share for their department", "Resist cuts to core work"],
                "constraints": ["Must still support the overall project goals"],
                "personality": "aggressive"
            }
        ]
    }
]


def get_all_scenarios():
    return deepcopy(SCENARIOS)


def get_scenario_by_id(scenario_id: str):
    for scenario in SCENARIOS:
        if scenario["id"] == scenario_id:
            return deepcopy(scenario)
    return None
