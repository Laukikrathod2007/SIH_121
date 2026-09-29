# SIH 26121 — The Real-World Drilling Problem in Plain English

## 1. Executive Analogy: The Fog of Subsurface Navigation
Imagine navigating an aircraft carrier through a narrow, uncharted fjord in dense fog. You have modern radar that displays your current speed, engine temperature, and rudder angle in real time. However, hidden under the surface are sharp granite reefs and volatile underwater currents. 

Three years ago, another captain sailed a similar ship 3 kilometers north of your current position. At a depth marker corresponding exactly to your next turn, that ship ran aground on a hidden reef, causing $15 million in damage. The captain wrote a detailed 40-page incident report explaining that an abrupt water pressure drop occurred 200 meters before the reef, and the only way to avoid grounding was to reduce speed to 4 knots and alter course 5 degrees west.

Today, that report sits as a scanned PDF inside a folder titled `Voyage_Reports_2023_Final_Scanned.pdf` on an office computer 500 kilometers away. As the current captain approaching that same reef, your live instruments give no warning because the reef has not been touched yet. You cannot afford to stop the ship for 6 hours to search through thousands of old PDF files. Unless an intelligent system proactively alerts you:
> *"Warning: Captain on Ship B encountered a sunken reef 200 meters ahead in this exact corridor; reduce speed and alter course now,"*

you will strike the same reef, suffer the same catastrophe, and learn the exact same lesson that the company had already paid millions of dollars to learn three years ago.

**This is exactly how complex oil and gas drilling operates today without NWIS.**

---

## 2. The Operational Reality: A Day on a Drilling Rig

An oil drilling rig is a heavy industrial factory operating 24 hours a day, 365 days a year. Every minute of operation costs immense capital:
- Rig dayrates in onshore Assam and offshore operations range from **₹8,00,000 to ₹35,00,000+ per day** ($10,000 to $45,000+ per day onshore; up to $250,000+ offshore).
- A single drilling incident that causes the drill pipe to get stuck or triggers an underground blow-out can shut down operations for **5 to 30 days**, resulting in losses of **₹1 Crore to ₹20+ Crores ($150,000 to $2.5+ Million)** per event.

### What the Drilling Engineer Actually Faces:
At 03:00 AM in the Duliajan operational area of Assam, a Drilling Engineer is supervising an active well named `NH-14` at a depth of **3,180 meters Measured Depth (MD)**. The drill bit is cutting through rock at 12 meters per hour inside the geologically challenging **Barail / Kopili formation**.

The rig's live sensors (connected to Oil India's **eRTMAC** system) show:
- Weight on Bit (WOB): 14 tonnes
- Top Drive Speed: 110 RPM
- Surface Torque: 16.5 kN·m
- Standpipe Mud Pressure (SPP): 2,400 psi
- Mud Weight: 1.25 SG

Everything looks normal on the live screens. However, 40 meters deeper, at **3,220 meters**, the active wellbore is about to enter an over-pressured, fractured sand reservoir with micro-faulting.

### The Fragmented Information Nightmare:
To know what will happen at 3,220 meters, the engineer needs to know what happened in other wells drilled into this formation.
- Four nearby wells were drilled in this area: `NH-02` (drilled in 2011), `NH-05` (drilled in 2017), `NH-09` (drilled in 2021), and `KW-01` (drilled in 2023).
- Where is that information?
  - `NH-02` records exist as a scanned paper document stored in an archive room or a static PDF with bad OCR.
  - `NH-05` has a 180-page Well Completion Report (WCR) saved in a shared drive.
  - `NH-09` has 90 daily drilling reports (DDRs) written by a drilling supervisor who retired two years ago.
  - `KW-01` has a mud logging spreadsheet stored on an isolated workstation.

The on-duty engineer cannot manually download and read 500 pages of technical reports while managing a live rig. The engineer must make split-second decisions. As a result, the active well drills straight into the fractured interval at 3,220 m. Suddenly:
1. **Severe Mud Losses Occur:** The drilling fluid drops out of the wellbore into the cavernous formation at 25 m³/hr.
2. **Wellbore Pressure Drops:** As the mud column falls, the pressure drops below the formation gas pressure.
3. **Gas Kick Influx:** Gas rushes into the wellbore. The rig must sound emergency sirens, shut the Blowout Preventer (BOP), and initiate well control procedures.
4. **Pipe Gets Mechanically Stuck:** Cavings collapse around the BHA.

### The Tragedy of "Unremembered History":
Two days later, during the post-incident investigation, the team opens the historical report of `NH-09` (drilled just 1.8 km away in 2021) and discovers on page 42:
> *"At 3,224 m MD, encountered depleted fractured Barail sand. Instant mud loss of 28 m³/hr followed by gas influx. Remediated by pre-treating active mud with 35 kg/m³ coarse calcium carbonate LCM and lowering pump rate to 1,400 lpm prior to penetration."*

The company already knew the exact solution. The solution had been documented three years earlier. Yet, because that knowledge was trapped inside an unsearchable PDF, the company suffered 12 days of Non-Productive Time (NPT), ₹4.5 Crores in remediation costs, and severe risk to crew safety.

---

## 3. Why Existing Tools Fall Short

| Traditional Method | What Actually Happens | Why It Fails |
| :--- | :--- | :--- |
| **Memory of Senior Drillers** | Engineers call a veteran colleague at 02:00 AM asking: *"Have you seen losses in Kopili block 4?"* | Personnel rotate shifts, retire, or transfer. Human memory is inaccurate regarding exact depths and parameters. |
| **Keyword Search in Folders** | Search for *"Barail loss"* in Windows Explorer across thousands of scanned PDFs. | Fails completely on scanned or handwritten PDF reports; misses variations like *"circ loss"*, *"seep"*, *"loss of returns"*. |
| **Standard GIS Maps** | Displays well heads as dots on a map; clicking a dot shows only static metadata (Well Name, Spud Date, Total Depth). | Shows where wells are located on the surface, but reveals **nothing** about subsurface risks, formation tops, or past incidents. |
| **Standard Real-Time Displays** | Displays live curves of ROP, Torque, SPP, and Flow Out. | Shows what is happening **now**, but has zero awareness of what lies **15 meters ahead of the bit**. |

---

## 4. What NWIS Does Differently: The Three Core Transformations

NWIS bridges the fatal gap between **Live Surface Telemetry (eRTMAC)** and **Historical Subsurface Experience (Archives)**:

```
[WITHOUT NWIS: REACTIVE]
Bit hits hazard → Incident occurs → Emergency shutdown → Rig is idle → Post-incident investigation reads archives

[WITH NWIS: PROACTIVE]
Bit is 30m above hazard → NWIS detects historical offset pattern → Early warning triggered → Rig adjusts parameters → Hazard penetrated safely
```

### The Three Transformations:

1. **From "Nearest Wells" to "Most Relevant Offsets":**
   Instead of displaying every well within 5 km, NWIS analyzes structural geology, formation dip, wellbore trajectory, and casing architecture to identify the 3 offset wells that truly matter for the active drilling section.
2. **From "Unstructured PDF Documents" to "Structured Engineering Events":**
   NWIS automatically reads thousands of DDRs, WCRs, and mud logs, extracting depths, formations, mud properties, incidents, and successful mitigations into a clean, queryable knowledge engine.
3. **From "Hindsight Investigations" to "Foresight Early Warnings":**
   As the drill bit deepens in real time, NWIS continuously projects a "Historical Risk Corridor" ahead of the bit. If an offset well suffered stuck pipe 20 meters below the current depth, NWIS alerts the driller with the exact historical evidence, the original source report page, and the recommended engineering countermeasures.
