from dataclasses import dataclass, field
from typing import List


VALID_AI_FIT = {"high", "medium_high", "medium", "low"}


@dataclass
class GrantProgram:
    id: str
    name: str
    administrator: str
    eligible_areas: List[str]       # "rural", "small_urban", "urban" or subset
    eligible_states: List[str]      # empty list means all states
    fund_types: List[str]           # "operating", "capital", "training", "demo", "research"
    federal_share_pct: str
    ai_fit: str                     # "high" | "medium_high" | "medium" | "low"
    notes: str
    narrative_sections: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.ai_fit not in VALID_AI_FIT:
            raise ValueError(f"ai_fit must be one of {VALID_AI_FIT}, got '{self.ai_fit}'")


GRANTS: List[GrantProgram] = [
    GrantProgram(
        id="5311_rtap",
        name="Section 5311 + RTAP (Rural Transit Assistance Program)",
        administrator="State DOT",
        eligible_areas=["rural"],
        eligible_states=[],  # national
        fund_types=["operating", "training", "technical_assistance", "capital"],
        federal_share_pct="Up to 80% (capital); training often higher",
        ai_fit="high",
        notes=(
            "Primary federal funding source for rural public transit. Eligible recipients are "
            "agencies serving areas under 50,000 population. The RTAP component specifically funds "
            "training, technical assistance, and related support services. Non-rural agencies are "
            "not eligible. Strong fit for AI training initiatives and capacity-building projects."
        ),
        # RTAP is training-focused: emphasize need, the training plan itself, staff capacity,
        # and how the agency will sustain the skills after the grant period.
        narrative_sections=[
            "Statement of Need",
            "Project Description",
            "Training Plan and Curriculum",
            "Agency Capacity and Qualifications",
            "Budget Summary",
            "Expected Outcomes and Sustainability",
        ],
    ),
    GrantProgram(
        id="wa_consolidated",
        name="Washington Consolidated Grant",
        administrator="WSDOT (Washington State DOT)",
        eligible_areas=["rural", "small_urban"],
        eligible_states=["WA"],
        fund_types=["capital", "operating", "mobility", "training"],
        federal_share_pct="Varies by sub-program",
        ai_fit="medium_high",
        notes=(
            "Washington State consolidated grant that bundles federal programs (5311, 5310, "
            "5339(a)) with state funds. Available to rural and small-urban agencies in WA. "
            "Covers capital, operating, and mobility management projects. "
            "Medium-high fit for AI training and small technology pilots."
        ),
        # Consolidated grant requires sub-program alignment and local match documentation;
        # mobility management projects need a coordination narrative.
        narrative_sections=[
            "Statement of Need",
            "Project Description",
            "Sub-Program Alignment",
            "Local Match and Budget Summary",
            "Coordination and Mobility Management Approach",
            "Expected Outcomes",
        ],
    ),
    GrantProgram(
        id="5312_emi",
        name="Section 5312 / Enhancing Mobility Innovation (EMI)",
        administrator="FTA (Federal Transit Administration — direct)",
        eligible_areas=["rural", "small_urban", "urban"],
        eligible_states=[],  # national
        fund_types=["research", "demo", "automation", "demand_response"],
        federal_share_pct="Varies",
        ai_fit="high",
        notes=(
            "FTA-administered program for agencies pursuing transit demonstrations and innovation. "
            "Funds research, demos, and demand-response software. "
            "High fit for AI pilots and automation projects."
        ),
        # Innovation grants must justify the novelty of the approach, describe how the demo
        # will be evaluated, and explain knowledge transfer so other agencies can replicate it.
        narrative_sections=[
            "Statement of Need",
            "Project Description and Innovation Rationale",
            "Technical Approach and Methodology",
            "Demonstration Plan and Timeline",
            "Evaluation Methodology and Success Metrics",
            "Budget Summary",
            "Knowledge Transfer and Replicability",
        ],
    ),
]
