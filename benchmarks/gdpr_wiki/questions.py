NOUL_QUESTIONS = {
    "breach_72h": {
        "instructions": (
            "Must a personal data breach be reported to the supervisory "
            "authority within 72 hours?"
        ),
        "expected": True,
        "proposition": (
            "A personal data breach must be reported to the supervisory "
            "authority within 72 hours after the controller becomes aware of it."
        ),
        "contradiction": (
            "The GDPR sets no 72-hour deadline for reporting a personal data "
            "breach to the supervisory authority."
        ),
    },
    "applies_non_eu": {
        "instructions": (
            "Does the regulation apply to organisations established outside "
            "the EU that offer goods or services to people in the EU?"
        ),
        "expected": True,
        "proposition": (
            "The GDPR applies to organisations outside the EU that offer "
            "goods or services to people in the EU."
        ),
        "contradiction": (
            "The GDPR never applies to organisations established outside the EU."
        ),
    },
    "dpo_all_orgs": {
        "instructions": (
            "Must every organisation appoint a Data Protection Officer, "
            "regardless of what data it processes?"
        ),
        "expected": False,
        "proposition": (
            "Every organisation must appoint a Data Protection Officer, "
            "regardless of its processing activities."
        ),
        "contradiction": (
            "A Data Protection Officer is required only in specified "
            "circumstances, not for every organisation."
        ),
    },
    "pre_ticked_consent": {
        "instructions": (
            "Can valid consent be obtained through pre-ticked boxes or "
            "inactivity?"
        ),
        "expected": False,
        "proposition": (
            "Pre-selected opt-out choices or inactivity can constitute valid "
            "GDPR consent."
        ),
        "contradiction": (
            "Valid GDPR consent requires an unambiguous affirmative action; "
            "pre-selected opt-out choices are invalid."
        ),
    },
    "right_erasure": {
        "instructions": (
            "Does the regulation grant individuals a right to erasure of "
            "their personal data?"
        ),
        "expected": True,
        "proposition": (
            "The GDPR grants data subjects a right to erasure of personal data."
        ),
        "contradiction": (
            "The GDPR grants no right to erasure of personal data."
        ),
    },
    "data_portability": {
        "instructions": (
            "Does the regulation include a right to data portability?"
        ),
        "expected": True,
        "proposition": (
            "The GDPR includes a right to data portability."
        ),
        "contradiction": (
            "The GDPR includes no right to data portability."
        ),
    },
    "us_federal_law": {
        "instructions": "Is the GDPR a United States federal law?",
        "expected": False,
        "proposition": "The GDPR is a United States federal law.",
        "contradiction": (
            "The GDPR is a European Union regulation, not a United States "
            "federal law."
        ),
    },
    "criminal_penalties": {
        "instructions": (
            "Does the GDPR itself impose criminal penalties such as "
            "imprisonment?"
        ),
        "expected": False,
        "proposition": (
            "The GDPR itself directly imposes criminal punishment such as "
            "imprisonment."
        ),
        "contradiction": (
            "Criminal offences and imprisonment come from national law, not "
            "directly from the GDPR itself."
        ),
    },
}


CHOICE_QUESTIONS = {
    "instrument_type": {
        "instructions": "What kind of EU legal instrument is the GDPR?",
        "criteria": {
            "Regulation": (
                "Directly binding law in all member states, no national "
                "implementation needed."
            ),
            "Directive": (
                "Sets goals that member states implement through national law."
            ),
            "Treaty": "An international treaty between states.",
            "Recommendation": "Non-binding guidance.",
        },
        "expected": "Regulation",
        "retrieval": (
            "The passage identifies whether the GDPR is an EU regulation, "
            "directive, treaty, or recommendation."
        ),
    },
    "max_fine": {
        "instructions": (
            "What is the maximum administrative fine for the most serious "
            "infringements?"
        ),
        "criteria": {
            "TwentyM_or_4pct": (
                "Up to EUR 20 million or 4% of annual worldwide turnover, "
                "whichever is greater."
            ),
            "TenM_or_2pct": (
                "Up to EUR 10 million or 2% of annual worldwide turnover, "
                "whichever is greater."
            ),
            "FixedCap": "A fixed amount not tied to turnover.",
            "NoFines": "The GDPR provides no administrative fines.",
        },
        "expected": "TwentyM_or_4pct",
        "retrieval": (
            "The passage states the maximum administrative fine and worldwide "
            "turnover percentage for serious GDPR infringements."
        ),
    },
}


SCORE_QUESTIONS = {
    "individual_rights": {
        "instructions": (
            "How strong are the rights the GDPR grants to individuals over "
            "their data?"
        ),
        "criteria": [
            "None: individuals get no rights over their data.",
            "Weak: a right to be informed, but little control.",
            (
                "Moderate: access and correction rights, but limited means "
                "to act on them."
            ),
            (
                "Strong: access, erasure, portability, and objection rights, "
                "with enforcement behind them."
            ),
        ],
        "retrieval": (
            "The passage describes individual rights such as access, erasure, "
            "portability, objection, or enforcement."
        ),
        "expected_index": 3,
    },
    "penalty_severity": {
        "instructions": (
            "How severe are the penalties the GDPR provides for non-compliance?"
        ),
        "criteria": [
            "None: no penalties of any kind.",
            "Symbolic: small fixed fines unlikely to change behavior.",
            "Substantial: fines large enough to matter to most companies.",
            (
                "Severe: fines scaled to global revenue, material even to "
                "the largest companies."
            ),
        ],
        "retrieval": (
            "The passage describes GDPR fines, sanctions, or penalties for "
            "non-compliance."
        ),
        "expected_index": 3,
    },
    "compliance_burden": {
        "instructions": (
            "How heavy is the compliance burden the GDPR places on "
            "organisations?"
        ),
        "criteria": [
            "Negligible: no meaningful obligations.",
            "Light: a few notices and disclosures.",
            (
                "Moderate: documented processes and some dedicated roles for "
                "larger processors."
            ),
            (
                "Heavy: records, impact assessments, officers, and breach "
                "procedures for many organisations."
            ),
            (
                "Extreme: obligations so demanding that ordinary "
                "organisations cannot fully comply."
            ),
        ],
        "retrieval": (
            "The passage describes organisational compliance duties such as "
            "records, impact assessments, officers, or breach procedures."
        ),
        "expected_index": 3,
    },
}
