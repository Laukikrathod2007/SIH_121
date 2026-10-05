"""
Generate high-resolution technical working diagrams for the eRTMAC-NWIS Working Document.
"""
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

TMP = Path(r"c:\Users\LAUKIK\Desktop\SIH121\_pdf_tmp")
TMP.mkdir(exist_ok=True)

# Colors
C_DARK = "#0A0E1A"
C_PANEL = "#111827"
C_BORDER = "#1F2937"
C_ACCENT = "#00C2FF"
C_GOLD = "#FFB800"
C_GREEN = "#00E676"
C_RED = "#FF3B30"
C_PURPLE = "#A855F7"
C_GREY = "#94A3B8"
C_WHITE = "#FFFFFF"

# 1. End-to-End Operational Pipeline
def make_e2e_pipeline():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=200)
    fig.patch.set_facecolor(C_DARK)
    ax.set_facecolor(C_DARK)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # Pillars
    boxes = [
        ("1. RAW DATA SOURCES", "Historical WCR / DDR PDFs\nReal Volve & Synthetic\nWITS0 / WITSML Feeds", 0.5, 3.2, 2.0, 1.8, C_PURPLE),
        ("2. DOC INTELLIGENCE", "6-Layer Extraction Engine\nPyMuPDF + Docling OCR\nPetro-Physics Auto-Repair", 2.9, 3.2, 2.0, 1.8, C_ACCENT),
        ("3. NWIS CORE ENGINE", "DORS Offset Well Ranking\nStratigraphic Correlator (xi)\nRisk Corridor Lookahead", 5.3, 3.2, 2.0, 1.8, C_GOLD),
        ("4. REAL-TIME COCKPIT", "12 SCADA React Pages\n4-Pillar Decoupled Conf.\nProactive Advisory Alerts", 7.7, 3.2, 2.0, 1.8, C_GREEN),
    ]

    for title, desc, x, y, w, h, col in boxes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                              facecolor=C_PANEL, edgecolor=col, linewidth=1.8)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.28, title, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color=col)
        ax.text(x + w/2, y + (h - 0.28)/2, desc, ha='center', va='center',
                fontsize=7.2, color=C_GREY, linespacing=1.3)

    # Horizontal Arrows
    for x_arr in [2.52, 4.92, 7.32]:
        arr = FancyArrowPatch((x_arr, 4.1), (x_arr + 0.36, 4.1),
                              arrowstyle='->', mutation_scale=14,
                              color=C_ACCENT, linewidth=2)
        ax.add_patch(arr)

    # Lower Integration & Feedback Loop
    loop_box = FancyBboxPatch((0.5, 0.6), 9.2, 1.8, boxstyle="round,pad=0.08",
                              facecolor=C_PANEL, edgecolor=C_BORDER, linewidth=1.5)
    ax.add_patch(loop_box)
    ax.text(5.1, 2.05, "MODULE 04 PHYSICS TELEMETRY & ADVISORY FEEDBACK LOOP",
            ha='center', va='center', fontsize=8.5, fontweight='bold', color=C_ACCENT)

    sub_items = [
        ("ODE Hydraulics Engine", "Herschel-Bulkley\nBingham Plastic ECD", 1.8, 1.25, C_GOLD),
        ("Real-Time Telemetry", "1-Hz WITS0 / WITSML\nSensor Anomaly Tracking", 4.1, 1.25, C_PURPLE),
        ("Hybrid Risk Aggregator", "R_H = 0.45P + 0.35A + 0.20M\nReal Volve ML Model", 6.4, 1.25, C_RED),
        ("Rig Decision Advisory", "Deterministic SPE/IADC\nEngineering Interventions", 8.5, 1.25, C_GREEN),
    ]
    for stitle, sdesc, cx, cy, scol in sub_items:
        ax.text(cx, cy + 0.25, stitle, ha='center', va='center', fontsize=7.5, fontweight='bold', color=scol)
        ax.text(cx, cy - 0.2, sdesc, ha='center', va='center', fontsize=6.8, color=C_GREY, linespacing=1.2)

    # Vertical connectors
    arr_down = FancyArrowPatch((8.7, 3.2), (8.7, 2.42), arrowstyle='->', mutation_scale=12, color=C_GREEN, linewidth=1.5)
    ax.add_patch(arr_down)
    arr_up = FancyArrowPatch((1.5, 2.42), (1.5, 3.2), arrowstyle='->', mutation_scale=12, color=C_PURPLE, linewidth=1.5)
    ax.add_patch(arr_up)

    plt.tight_layout()
    plt.savefig(TMP / "working_e2e_architecture.png", facecolor=C_DARK, edgecolor='none')
    plt.close()

# 2. 6-Tier Document Intelligence Pipeline
def make_doc_intel_pipeline():
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=200)
    fig.patch.set_facecolor(C_DARK)
    ax.set_facecolor(C_DARK)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis('off')

    tiers = [
        ("Tier 1: Native Text", "PyMuPDF High-Speed\n30-40 ms/page\nVector Stream", 0.6, 2.6, C_ACCENT),
        ("Tier 2: OCR Fallback", "Docling OCR Engine\nRaster Heuristics\nScanned Page Handler", 2.2, 2.6, C_PURPLE),
        ("Tier 3: Rules & Regex", "Deterministic Regex\nFormations, Events\nMud & Casing Records", 3.8, 2.6, C_GOLD),
        ("Tier 4: Template Learner", "Table Structure Anchor\nDynamic Header Match\nCoordinate Mapping", 5.4, 2.6, C_GREEN),
        ("Tier 5: Physics Validator", "Auto-Repair OCR Slips\n(e.g. 3.2 -> 13.2 ppg)\nGradient Consistency", 7.0, 2.6, C_RED),
        ("Tier 6: WITSML Output", "WITSML 2.0 Standard\nStructured JSON Payload\nDirect Database Sync", 8.6, 2.6, C_ACCENT),
    ]

    for title, desc, cx, cy, col in tiers:
        rect = FancyBboxPatch((cx - 0.7, cy - 0.8), 1.4, 1.6, boxstyle="round,pad=0.06",
                              facecolor=C_PANEL, edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(cx, cy + 0.5, title.split(":")[0], ha='center', va='center', fontsize=7.5, fontweight='bold', color=col)
        ax.text(cx, cy + 0.22, title.split(":")[1].strip(), ha='center', va='center', fontsize=6.8, fontweight='bold', color=C_WHITE)
        ax.text(cx, cy - 0.35, desc, ha='center', va='center', fontsize=6.2, color=C_GREY, linespacing=1.2)

    # Arrows between tiers
    for i in range(len(tiers) - 1):
        x1 = tiers[i][2] + 0.7
        x2 = tiers[i+1][2] - 0.7
        arr = FancyArrowPatch((x1, 2.6), (x2, 2.6), arrowstyle='->', mutation_scale=10, color=C_ACCENT, linewidth=1.5)
        ax.add_patch(arr)

    # Cloud Fallback Banner Below
    cloud_box = FancyBboxPatch((0.6, 0.4), 8.8, 1.1, boxstyle="round,pad=0.08",
                               facecolor=C_PANEL, edgecolor=C_GOLD, linewidth=1.2, linestyle='--')
    ax.add_patch(cloud_box)
    ax.text(5.0, 1.15, "HYBRID CLOUD PARSER FALLBACK ARCHITECTURE (Reducto / Extend.ai)",
            ha='center', va='center', fontsize=8, fontweight='bold', color=C_GOLD)
    ax.text(5.0, 0.7, "Automatically engaged if local OCR confidence drops below 60%. Ensures 100% extraction completion\nwhile preserving on-premise air-gapped sovereign execution as the primary path.",
            ha='center', va='center', fontsize=6.8, color=C_GREY, linespacing=1.2)

    plt.tight_layout()
    plt.savefig(TMP / "working_doc_intelligence_flow.png", facecolor=C_DARK, edgecolor='none')
    plt.close()

# 3. Stratigraphic Depth Normalization & The Trajectory Trap
def make_stratigraphic_diagram():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=200)
    for ax in (ax1, ax2):
        fig.patch.set_facecolor(C_DARK)
        ax.set_facecolor(C_DARK)

    # Left: The Trajectory Trap in Measured Depth (MD)
    ax1.set_title("THE TRAJECTORY TRAP (Measured Depth MD)", color=C_RED, fontsize=9, fontweight='bold', pad=10)
    ax1.set_xlim(0, 10)
    ax1.set_ylim(4000, 1500)
    ax1.set_ylabel("Measured Depth MD (m)", color=C_GREY, fontsize=8)
    ax1.tick_params(colors=C_GREY, labelsize=7)
    for spine in ax1.spines.values():
        spine.set_color(C_BORDER)

    # Formation zones
    ax1.axhspan(2000, 2400, color='#1E293B', alpha=0.6, label='Tipam Sandstone (Offset 1)')
    ax1.axhspan(2600, 3100, color='#334155', alpha=0.6, label='Barail Coal-Shale (Deviated)')
    ax1.plot([2, 2], [1500, 3200], color=C_ACCENT, linewidth=2.5, label='Vertical Well A')
    ax1.plot([5, 5, 8], [1500, 2200, 3600], color=C_GOLD, linewidth=2.5, label='Directional Well B (45 deg)')

    ax1.scatter([2], [2200], color=C_RED, s=60, zorder=5)
    ax1.text(2.3, 2200, "Kick Event @ 2200m MD\n(In Tipam Sandstone)", color=C_WHITE, fontsize=7)

    ax1.scatter([6.8], [3000], color=C_RED, s=60, zorder=5)
    ax1.text(7.1, 3000, "Kick Event @ 3000m MD\n(Same Formation!)", color=C_WHITE, fontsize=7)

    ax1.text(5.0, 3850, "Direct MD comparison gives 800m false offset!", color=C_RED,
             ha='center', fontsize=7.5, fontweight='bold')

    # Right: Stratigraphic Normalized Depth (xi)
    ax2.set_title("NWIS STRATIGRAPHIC ALIGNMENT (xi Normalized)", color=C_GREEN, fontsize=9, fontweight='bold', pad=10)
    ax2.set_xlim(0, 10)
    ax2.set_ylim(1.2, -0.2)
    ax2.set_ylabel("Normalized Formation Penetration (xi)", color=C_GREY, fontsize=8)
    ax2.tick_params(colors=C_GREY, labelsize=7)
    for spine in ax2.spines.values():
        spine.set_color(C_BORDER)

    ax2.axhspan(0.0, 1.0, color='#064E3B', alpha=0.4)
    ax2.axhline(0.0, color=C_GREEN, linestyle='--', linewidth=1, label='Formation Top (xi = 0.0)')
    ax2.axhline(1.0, color=C_GOLD, linestyle='--', linewidth=1, label='Formation Base (xi = 1.0)')

    ax2.plot([3, 3], [-0.1, 1.1], color=C_ACCENT, linewidth=2.5, label='Well A Track')
    ax2.plot([7, 7], [-0.1, 1.1], color=C_GOLD, linewidth=2.5, label='Well B Track')

    ax2.scatter([3], [0.42], color=C_RED, s=80, zorder=5)
    ax2.scatter([7], [0.44], color=C_RED, s=80, zorder=5)

    ax2.plot([3, 7], [0.42, 0.44], color=C_GREEN, linestyle=':', linewidth=2)
    ax2.text(5.0, 0.36, "True Geological Alignment @ xi ~ 0.43\nRisk Corridor Confirmed!",
             color=C_GREEN, ha='center', fontsize=7.5, fontweight='bold')
    ax2.text(5.0, 1.15, "xi = (TVD - Top_TVD) / Formation_Thickness",
             color=C_WHITE, ha='center', fontsize=7.2, fontstyle='italic')

    plt.tight_layout()
    plt.savefig(TMP / "working_stratigraphic_depth.png", facecolor=C_DARK, edgecolor='none')
    plt.close()

# 4. Real-Time Telemetry & Anomaly Trigger Curves
def make_telemetry_curves():
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 4.8), dpi=200, sharex=True)
    fig.patch.set_facecolor(C_DARK)

    time = np.linspace(0, 120, 300) # minutes

    # Standpipe Pressure (SPP)
    ax1.set_facecolor(C_DARK)
    spp_normal = 2400 + 30 * np.sin(time / 10) + np.random.normal(0, 15, 300)
    # Sudden drop at t=75 (lost circulation / wash out)
    spp_drop = spp_normal.copy()
    spp_drop[180:] -= np.linspace(0, 450, 120)
    ax1.plot(time, spp_drop, color=C_ACCENT, linewidth=1.5, label='Standpipe Pressure (psi)')
    ax1.axvline(72, color=C_RED, linestyle='--', linewidth=1.2)
    ax1.text(73, 2150, "Pressure Drop Anomaly\n(Mud Loss / Washout)", color=C_RED, fontsize=7, fontweight='bold')
    ax1.set_ylabel("SPP (psi)", color=C_GREY, fontsize=7)
    ax1.tick_params(colors=C_GREY, labelsize=6.5)
    ax1.set_title("REAL-TIME MULTI-SENSOR ANOMALY DETECTION ENGINE", color=C_GOLD, fontsize=8.5, fontweight='bold', pad=4)
    for s in ax1.spines.values(): s.set_color(C_BORDER)

    # Torque & Drag
    ax2.set_facecolor(C_DARK)
    torque_normal = 14 + 1.5 * np.sin(time / 8) + np.random.normal(0, 0.5, 300)
    torque_spike = torque_normal.copy()
    torque_spike[190:] += np.linspace(0, 9, 110)
    ax2.plot(time, torque_spike, color=C_GOLD, linewidth=1.5, label='Surface Torque (kft-lbs)')
    ax2.axvline(76, color=C_RED, linestyle='--', linewidth=1.2)
    ax2.text(77, 19, "Torque Spike (Overpull / Differential Sticking)", color=C_GOLD, fontsize=7, fontweight='bold')
    ax2.set_ylabel("Torque (kft-lb)", color=C_GREY, fontsize=7)
    ax2.tick_params(colors=C_GREY, labelsize=6.5)
    for s in ax2.spines.values(): s.set_color(C_BORDER)

    # Flow In vs Flow Out
    ax3.set_facecolor(C_DARK)
    flow_in = np.full(300, 650)
    flow_out = np.full(300, 650) + np.random.normal(0, 8, 300)
    flow_out[180:] -= np.linspace(0, 160, 120)
    ax3.plot(time, flow_in, color=C_GREEN, linewidth=1.5, label='Flow In (gpm)')
    ax3.plot(time, flow_out, color=C_RED, linewidth=1.5, linestyle='-.', label='Flow Out (gpm)')
    ax3.fill_between(time[180:], flow_in[180:], flow_out[180:], color=C_RED, alpha=0.3, label='Delta Q Loss Zone')
    ax3.set_ylabel("Flow (gpm)", color=C_GREY, fontsize=7)
    ax3.set_xlabel("Elapsed Time (Minutes)", color=C_GREY, fontsize=7.5)
    ax3.tick_params(colors=C_GREY, labelsize=6.5)
    ax3.legend(loc='lower left', fontsize=6.5, facecolor=C_PANEL, edgecolor=C_BORDER, labelcolor=C_WHITE)
    for s in ax3.spines.values(): s.set_color(C_BORDER)

    plt.tight_layout()
    plt.savefig(TMP / "working_telemetry_anomaly_ode.png", facecolor=C_DARK, edgecolor='none')
    plt.close()

# 5. SCADA 4-Stage Alert State Machine
def make_alert_state_machine():
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=200)
    fig.patch.set_facecolor(C_DARK)
    ax.set_facecolor(C_DARK)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis('off')

    states = [
        ("STAGE 1: DETECTED", "Sensor Anomaly A_sensor > 0.65\nOR Risk Corridor <= 50m\nAutomated System Trigger", 1.2, 2.3, C_GOLD),
        ("STAGE 2: PROXIMITY ALERT", "Visual & Audio Rig Alarm\nCockpit Banner & Notification\nEngineer Attention Mandated", 3.7, 2.3, C_RED),
        ("STAGE 3: ACKNOWLEDGED", "Drilling Engineer Logged In\nEvidence Modal Inspected\nAnalog Wells Reviewed", 6.2, 2.3, C_ACCENT),
        ("STAGE 4: MITIGATED", "SPE/IADC Action Executed\n(e.g. LCM Pill / MW Increase)\nState Auto-Cleared", 8.7, 2.3, C_GREEN),
    ]

    for title, desc, cx, cy, col in states:
        rect = FancyBboxPatch((cx - 1.0, cy - 0.75), 2.0, 1.5, boxstyle="round,pad=0.08",
                              facecolor=C_PANEL, edgecolor=col, linewidth=1.8)
        ax.add_patch(rect)
        ax.text(cx, cy + 0.45, title, ha='center', va='center', fontsize=7.5, fontweight='bold', color=col)
        ax.text(cx, cy - 0.15, desc, ha='center', va='center', fontsize=6.6, color=C_GREY, linespacing=1.2)

    for i in range(len(states) - 1):
        x1 = states[i][2] + 1.0
        x2 = states[i+1][2] - 1.0
        arr = FancyArrowPatch((x1, 2.3), (x2, 2.3), arrowstyle='->', mutation_scale=12, color=C_ACCENT, linewidth=1.8)
        ax.add_patch(arr)

    # Return loop
    ret_arr = FancyArrowPatch((8.7, 1.5), (1.2, 1.5), arrowstyle='->', mutation_scale=12,
                              color=C_GREEN, linewidth=1.5, connectionstyle="arc3,rad=-0.15")
    ax.add_patch(ret_arr)
    ax.text(5.0, 0.8, "Continuous 1-Hz Real-Time Verification Loop — Cleared to Operational Green",
            ha='center', va='center', fontsize=7.5, color=C_GREEN, fontweight='bold')

    plt.tight_layout()
    plt.savefig(TMP / "working_scada_state_machine.png", facecolor=C_DARK, edgecolor='none')
    plt.close()

if __name__ == "__main__":
    make_e2e_pipeline()
    make_doc_intel_pipeline()
    make_stratigraphic_diagram()
    make_telemetry_curves()
    make_alert_state_machine()
    print("All working diagrams generated successfully.")
