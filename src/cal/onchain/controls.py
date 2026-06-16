"""On-chain control registry (OC-01..OC-05), mapped to MITRE ATT&CK + NIST CSF 2.0.

These validate that the REAL deployed compliance/governance controls exist, respond,
and remain correctly wired — the on-chain analogue of the mock control catalog.
"""

from __future__ import annotations

from cal.assurance.controls import Control

ONCHAIN_CONTROL_REGISTRY: tuple[Control, ...] = (
    Control(
        "OC-01",
        "Custody contracts are deployed and reachable (stablecoin decimals == 6)",
        "On-chain · Infra",
        (),
        ("ID.AM", "GV.OC"),
        "oc_reachability",
    ),
    Control(
        "OC-02",
        "Restriction-list wiring intact (TransferRestrictions → expected RestrictionList)",
        "On-chain · Compliance",
        ("T1565",),
        ("PR.PS", "DE.CM"),
        "oc_restriction_wiring",
    ),
    Control(
        "OC-03",
        "KYC-registry wiring intact (TransferRestrictions → expected KYCRegistry)",
        "On-chain · Compliance",
        ("T1565",),
        ("PR.AA", "DE.CM"),
        "oc_kyc_wiring",
    ),
    Control(
        "OC-04",
        "Denylist surface functional (legit transfer allowed, unknown not restricted)",
        "On-chain · Screening",
        ("T1657",),
        ("DE.AE",),
        "oc_denylist_functional",
    ),
    Control(
        "OC-05",
        "Mint-ceiling control present (MintController.remainingAllocation callable)",
        "On-chain · Governance",
        ("T1657",),
        ("GV.PO",),
        "oc_mint_ceiling",
    ),
)
