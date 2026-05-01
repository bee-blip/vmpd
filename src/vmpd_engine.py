"""
VMPD Engine
-----------
Vulnerability Management for Policy Design (VMPD) v1.0
Author: Bhavyatta Bhardwaj
License: MIT (code) / CC BY 4.0 (methodology)

This module provides the data structures, scoring functions, and visualisation helpers that the VMPD notebooks use. Analysts do not need to read or modify this code — the notebooks import from it and expose simple form-filling
interfaces.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


# =============================================================================
# Sub-metric criteria documentation
# =============================================================================
# These dictionaries document what each score (0-4) means for each sub-metric.
# Used in notebooks to remind analysts of the scoring criteria.

SCORING_CRITERIA = {
    "legibility": {
        "upstream_visibility": {
            0: "Regime fully requires attestation/audit of all upstream conditions it depends on",
            1: "Regime requires attestation of most upstream conditions, with minor gaps",
            2: "Regime requires attestation of some upstream conditions, with significant gaps",
            3: "Regime requires attestation of few upstream conditions; most are invisible",
            4: "Regime requires no attestation of upstream conditions; they are entirely invisible",
        },
        "process_specification": {
            0: "Critical processes are fully specified to a level permitting verification",
            1: "Most critical processes are specified with minor ambiguities",
            2: "Some critical processes are specified; others are ambiguous or undefined",
            3: "Few critical processes are specified; most are ambiguous or undefined",
            4: "Critical processes are not specified at any level permitting verification",
        },
        "inherited_trust": {
            0: "Regime requires verification at every use; no inherited trust",
            1: "Regime requires verification in most cases; minor inherited trust",
            2: "Regime presumes compliance based on prior use in some cases",
            3: "Regime broadly presumes compliance based on prior use",
            4: "Regime entirely presumes compliance based on prior use; no fresh verification",
        },
        "verification_authority": {
            0: "Named authority with full mandate and capability to verify legibility claims",
            1: "Named authority with adequate mandate but limited capability",
            2: "Named authority with partial mandate or capability",
            3: "Authority named but lacks mandate or capability",
            4: "No authority named to verify legibility claims",
        },
    },
    "architecture": {
        "accountability_inclusion_ratio": {
            0: "All accountable actors are structurally required in coordination architecture",
            1: "Most accountable actors are included; minor gaps",
            2: "Some accountable actors are included; significant gaps",
            3: "Few accountable actors are included; most are absent",
            4: "Accountable actors are systematically excluded from coordination architecture",
        },
        "domain_authority_coverage": {
            0: "All domains the regime depends on have their authorities formally included",
            1: "Most relevant domain authorities are included",
            2: "Some relevant domain authorities are included",
            3: "Few relevant domain authorities are included",
            4: "Relevant domain authorities are systematically excluded",
        },
        "affected_party_standing": {
            0: "Affected populations have full formal standing in the architecture",
            1: "Affected populations have substantial standing with minor gaps",
            2: "Affected populations have partial standing",
            3: "Affected populations have minimal standing",
            4: "Affected populations have no formal standing in the architecture",
        },
        "coordination_specificity": {
            0: "Coordination mechanisms are fully specified",
            1: "Coordination mechanisms are mostly specified with minor gaps",
            2: "Coordination mechanisms are partially specified",
            3: "Coordination mechanisms are largely assumed rather than specified",
            4: "Coordination mechanisms are entirely assumed; nothing specified",
        },
    },
    "specificity": {
        "threshold_definition": {
            0: "All triggering conditions are defined to a level permitting enforcement",
            1: "Most triggering conditions are well-defined; minor ambiguities",
            2: "Some triggering conditions are defined; others ambiguous",
            3: "Few triggering conditions are defined; most ambiguous",
            4: "Triggering conditions are not defined to any enforceable level",
        },
        "obligation_bindingness": {
            0: "Obligations stated as fully enforceable requirements",
            1: "Most obligations enforceable; minor aspirational language",
            2: "Mix of enforceable and aspirational obligations",
            3: "Most obligations stated aspirationally rather than as enforceable requirements",
            4: "Obligations entirely aspirational; no enforceable specificity",
        },
        "deferred_process_density": {
            0: "No substantive determinations deferred to undefined future processes",
            1: "Few substantive determinations deferred",
            2: "Some substantive determinations deferred",
            3: "Many substantive determinations deferred",
            4: "Substantive determinations systematically deferred to undefined processes",
        },
        "exception_architecture": {
            0: "Exceptions are fully bounded and conditioned",
            1: "Exceptions are mostly bounded with minor open-ended provisions",
            2: "Exceptions are partially bounded",
            3: "Exceptions are largely open-ended",
            4: "Exceptions are entirely open-ended; no bounding conditions",
        },
    },
    "pattern_responsibility": {
        "pattern_recognition_assignment": {
            0: "Named authority responsible for all anticipated pattern recognition",
            1: "Named authority responsible for most pattern recognition",
            2: "Named authority responsible for some pattern recognition",
            3: "Pattern recognition responsibility largely unassigned",
            4: "No authority assigned to pattern recognition the regime depends on",
        },
        "detection_capability_requirement": {
            0: "Named authority required to have/build full detection capability",
            1: "Named authority required to have substantial detection capability",
            2: "Named authority required to have partial detection capability",
            3: "Named authority's detection capability requirement is minimal",
            4: "No requirement for named authority to have detection capability",
        },
        "trigger_specificity": {
            0: "Conditions triggering response fully specified",
            1: "Trigger conditions mostly specified; minor ambiguities",
            2: "Trigger conditions partially specified",
            3: "Trigger conditions largely unspecified",
            4: "Trigger conditions entirely unspecified",
        },
        "response_architecture_coherence": {
            0: "Response mechanisms fully matched to anticipated patterns",
            1: "Response mechanisms mostly matched; minor mismatches",
            2: "Response mechanisms partially matched",
            3: "Response mechanisms poorly matched to patterns",
            4: "Response mechanisms entirely mismatched or absent",
        },
    },
    "recourse": {
        "mechanism_existence": {
            0: "Robust contestation mechanisms exist for affected parties",
            1: "Contestation mechanisms exist with minor gaps",
            2: "Some contestation mechanisms exist",
            3: "Limited contestation mechanisms exist",
            4: "No contestation mechanisms exist for affected parties",
        },
        "mechanism_accessibility": {
            0: "Mechanisms accessible without specialised legal/institutional resources",
            1: "Mechanisms mostly accessible; minor resource requirements",
            2: "Mechanisms accessible with moderate resource requirements",
            3: "Mechanisms require substantial legal/institutional resources",
            4: "Mechanisms inaccessible without resources affected parties cannot have",
        },
        "cost_distribution": {
            0: "Enforcement costs borne by regime's enforcement architecture",
            1: "Most enforcement costs borne by regime; some by affected parties",
            2: "Enforcement costs shared between regime and affected parties",
            3: "Most enforcement costs borne by affected parties",
            4: "Enforcement costs entirely borne by affected parties",
        },
        "pre_enforcement_recourse": {
            0: "Robust mechanisms allow affected parties to surface concerns pre-enforcement",
            1: "Pre-enforcement recourse mostly available",
            2: "Some pre-enforcement recourse available",
            3: "Limited pre-enforcement recourse",
            4: "No pre-enforcement recourse; parties can only contest after action taken",
        },
    },
}


DIMENSION_NAMES = ["legibility", "architecture", "specificity",
                   "pattern_responsibility", "recourse"]

DIMENSION_DISPLAY_NAMES = {
    "legibility": "Legibility",
    "architecture": "Architecture",
    "specificity": "Specificity",
    "pattern_responsibility": "Pattern Responsibility",
    "recourse": "Recourse",
}


# =============================================================================
# Data structures
# =============================================================================

@dataclass
class Vulnerability:
    """A single structural vulnerability identified in a regime."""
    name: str
    location: str
    description: str
    rationale: str

    # Legibility sub-metrics (0-4)
    upstream_visibility: int = 0
    process_specification: int = 0
    inherited_trust: int = 0
    verification_authority: int = 0

    # Architecture sub-metrics (0-4)
    accountability_inclusion_ratio: int = 0
    domain_authority_coverage: int = 0
    affected_party_standing: int = 0
    coordination_specificity: int = 0

    # Specificity sub-metrics (0-4)
    threshold_definition: int = 0
    obligation_bindingness: int = 0
    deferred_process_density: int = 0
    exception_architecture: int = 0

    # Pattern responsibility sub-metrics (0-4)
    pattern_recognition_assignment: int = 0
    detection_capability_requirement: int = 0
    trigger_specificity: int = 0
    response_architecture_coherence: int = 0

    # Recourse sub-metrics (0-4)
    mechanism_existence: int = 0
    mechanism_accessibility: int = 0
    cost_distribution: int = 0
    pre_enforcement_recourse: int = 0

    # Optional fields
    beneficiaries: str = ""
    impacted_populations: str = ""

    def dimension_score(self, dimension: str) -> float:
        """Calculate dimension score (0-10) from sub-metrics."""
        if dimension == "legibility":
            submetrics = [self.upstream_visibility, self.process_specification,
                          self.inherited_trust, self.verification_authority]
        elif dimension == "architecture":
            submetrics = [self.accountability_inclusion_ratio,
                          self.domain_authority_coverage,
                          self.affected_party_standing,
                          self.coordination_specificity]
        elif dimension == "specificity":
            submetrics = [self.threshold_definition, self.obligation_bindingness,
                          self.deferred_process_density, self.exception_architecture]
        elif dimension == "pattern_responsibility":
            submetrics = [self.pattern_recognition_assignment,
                          self.detection_capability_requirement,
                          self.trigger_specificity,
                          self.response_architecture_coherence]
        elif dimension == "recourse":
            submetrics = [self.mechanism_existence, self.mechanism_accessibility,
                          self.cost_distribution, self.pre_enforcement_recourse]
        else:
            raise ValueError(f"Unknown dimension: {dimension}")

        # Average sub-metrics (0-4 scale) and convert to 0-10
        return round((sum(submetrics) / len(submetrics)) * 2.5, 2)

    def base_score(self) -> float:
        """Calculate Base Vulnerability Score (0-10)."""
        scores = [self.dimension_score(d) for d in DIMENSION_NAMES]
        return round(sum(scores) / len(scores), 2)

    def severity_label(self) -> str:
        """Return severity label based on base score."""
        score = self.base_score()
        if score < 2.5:
            return "Low"
        elif score < 5.0:
            return "Moderate"
        elif score < 7.5:
            return "High"
        else:
            return "Severe"

    def to_dict(self) -> dict:
        """Export vulnerability as a dictionary."""
        return {
            "name": self.name,
            "location": self.location,
            "description": self.description,
            "rationale": self.rationale,
            "beneficiaries": self.beneficiaries,
            "impacted_populations": self. impacted_populations,
            "base_score": self.base_score(),
            "severity": self.severity_label(),
            **{f"{d}_score": self.dimension_score(d) for d in DIMENSION_NAMES},
        }


@dataclass
class Analysis:
    """A complete VMPD analysis of a governance regime."""
    regime_name: str
    analyst: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    operational_context: str = ""
    accountability_frame: str = ""
    vulnerabilities: List[Vulnerability] = field(default_factory=list)

    def add_vulnerability(self, **kwargs) -> Vulnerability:
        """Add a vulnerability to the analysis."""
        v = Vulnerability(**kwargs)
        self.vulnerabilities.append(v)
        return v

    def summary_table(self) -> pd.DataFrame:
        """Return a summary DataFrame of all vulnerabilities."""
        if not self.vulnerabilities:
            return pd.DataFrame()
        return pd.DataFrame([v.to_dict() for v in self.vulnerabilities])

    def regime_severity(self) -> str:
        """Return aggregate severity assessment for the regime."""
        if not self.vulnerabilities:
            return "No vulnerabilities identified"
        scores = [v.base_score() for v in self.vulnerabilities]
        avg = sum(scores) / len(scores)
        max_score = max(scores)
        return f"Average vulnerability: {round(avg, 2)} | Maximum: {round(max_score, 2)} | Count: {len(scores)}"


# =============================================================================
# Convenience functions for notebooks
# =============================================================================

def new_analysis(regime_name: str, analyst: str = "", **kwargs) -> Analysis:
    """Create a new VMPD analysis."""
    return Analysis(regime_name=regime_name, analyst=analyst, **kwargs)


def show_criteria(dimension: str, submetric: str = None):
    """Display scoring criteria for a dimension or specific sub-metric."""
    if dimension not in SCORING_CRITERIA:
        print(f"Unknown dimension: {dimension}")
        print(f"Available: {list(SCORING_CRITERIA.keys())}")
        return

    if submetric is None:
        # Show all sub-metrics for the dimension
        print(f"\n{DIMENSION_DISPLAY_NAMES[dimension]} — Scoring Criteria")
        print("=" * 60)
        for sm, criteria in SCORING_CRITERIA[dimension].items():
            print(f"\n{sm}:")
            for score, desc in criteria.items():
                print(f"  {score}: {desc}")
    else:
        if submetric not in SCORING_CRITERIA[dimension]:
            print(f"Unknown sub-metric: {submetric}")
            return
        print(f"\n{submetric} — Scoring Criteria")
        print("=" * 60)
        for score, desc in SCORING_CRITERIA[dimension][submetric].items():
            print(f"  {score}: {desc}")


# =============================================================================
# Visualisation
# =============================================================================

def radar_chart(vulnerability: Vulnerability, save_path: Optional[str] = None):
    """Generate a radar chart for a single vulnerability."""
    dimensions = DIMENSION_NAMES
    labels = [DIMENSION_DISPLAY_NAMES[d] for d in dimensions]
    scores = [vulnerability.dimension_score(d) for d in dimensions]

    # Close the loop
    angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
    scores_plot = scores + [scores[0]]
    angles_plot = angles + [angles[0]]
    labels_plot = labels + [labels[0]]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.plot(angles_plot, scores_plot, linewidth=2, color='#2C3E50')
    ax.fill(angles_plot, scores_plot, alpha=0.25, color='#2C3E50')
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, size=11)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], size=9)
    ax.grid(True, alpha=0.3)

    title = f"{vulnerability.name}\nBase Score: {vulnerability.base_score()} ({vulnerability.severity_label()})"
    plt.title(title, size=13, pad=20)

    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.tight_layout()
    return fig


def comparison_chart(analysis: Analysis, save_path: Optional[str] = None):
    """Generate a comparison bar chart of all vulnerabilities in an analysis."""
    if not analysis.vulnerabilities:
        print("No vulnerabilities to plot.")
        return None

    names = [v.name for v in analysis.vulnerabilities]
    scores = [v.base_score() for v in analysis.vulnerabilities]
    severities = [v.severity_label() for v in analysis.vulnerabilities]

    color_map = {"Low": "#27AE60", "Moderate": "#F39C12",
                 "High": "#E67E22", "Severe": "#C0392B"}
    colors = [color_map[s] for s in severities]

    fig, ax = plt.subplots(figsize=(10, max(4, len(names) * 0.6)))
    bars = ax.barh(names, scores, color=colors)
    ax.set_xlim(0, 10)
    ax.set_xlabel("Base Vulnerability Score (0-10)")
    ax.set_title(f"VMPD Analysis: {analysis.regime_name}", size=13, pad=15)
    ax.axvline(x=2.5, color='gray', linestyle='--', alpha=0.3)
    ax.axvline(x=5.0, color='gray', linestyle='--', alpha=0.3)
    ax.axvline(x=7.5, color='gray', linestyle='--', alpha=0.3)
    ax.grid(True, alpha=0.3, axis='x')

    # Add score labels on bars
    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{score}', va='center', size=10)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=150)
    return fig


# =============================================================================
# Reporting
# =============================================================================

def generate_report(analysis: Analysis, output_dir: str = "outputs") -> str:
    """Generate a markdown report and save outputs."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_name = analysis.regime_name.replace(" ", "_").replace("/", "_")
    report_path = Path(output_dir) / f"{safe_name}_VMPD_report.md"
    csv_path = Path(output_dir) / f"{safe_name}_VMPD_data.csv"

    # Save CSV
    df = analysis.summary_table()
    df.to_csv(csv_path, index=False)

    # Build markdown report
    lines = [
        f"# VMPD Analysis: {analysis.regime_name}",
        "",
        f"**Analyst:** {analysis.analyst or 'Not specified'}  ",
        f"**Date:** {analysis.date}  ",
        f"**Methodology:** Vulnerability Management for Policy Design (VMPD) v1.0",
        "",
        "## Regime Context",
        "",
        f"**Operational context:** {analysis.operational_context or 'Not specified'}",
        "",
        f"**Accountability frame:** {analysis.accountability_frame or 'Not specified'}",
        "",
        "## Summary",
        "",
        f"{analysis.regime_severity()}",
        "",
        "## Identified Vulnerabilities",
        "",
    ]

    for i, v in enumerate(analysis.vulnerabilities, 1):
        lines.extend([
            f"### Vulnerability {i}: {v.name}",
            "",
            f"**Location:** {v.location}",
            "",
            f"**Description:** {v.description}",
            "",
            f"**Base Score:** {v.base_score()} ({v.severity_label()})",
            "",
            "**Dimension Scores:**",
            "",
            f"- Legibility: {v.dimension_score('legibility')}",
            f"- Architecture: {v.dimension_score('architecture')}",
            f"- Specificity: {v.dimension_score('specificity')}",
            f"- Pattern Responsibility: {v.dimension_score('pattern_responsibility')}",
            f"- Recourse: {v.dimension_score('recourse')}",
            "",
            f"**Analyst Rationale:** {v.rationale}",
            "",
        ])
        if v.beneficiaries:
            lines.extend([f"**Beneficiaries of vulnerability:** {v.beneficiaries}", ""])
        if v. impacted_populations:
            lines.extend([f"**Cost bearers:** {v. impacted_populations}", ""])
        lines.append("---")
        lines.append("")

    lines.extend([
        "## Citation",
        "",
        "Bhardwaj, B. (2026). *Vulnerability Management for Policy Design (VMPD): "
        "A Methodology for Diagnosing Structural Failures in Governance Regimes*, v1.0. "
        "Zenodo. [DOI to be added]",
    ])

    report_path.write_text("\n".join(lines))

    print(f"Report saved: {report_path}")
    print(f"Data saved: {csv_path}")
    return str(report_path)