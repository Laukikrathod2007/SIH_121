// "The Brief": the DrillWise product story, 8 phases, ~66 s. Each phase is
// a real-time 3D shot (see scene/) with the message overlaid, in the
// layout of a product keynote: problem (2) → solution (5) → outcome (1).
//
// Every number comes from the NWIS backend's output for the demo scenario
// (active well WELL-NHK-002 at 2,850 m MD): /api/v2/offset_rank,
// /ahead_of_bit, /analyze, /formations, /events. Events and drilling
// reports are the synthetic testbed; the page says so.

export type PhaseId = 'well' | 'buried' | 'extract' | 'nearby' | 'relevant' | 'correlate' | 'ahead' | 'decide';

export interface Fact {
  label: string;
  value: string;
}

export interface Phase {
  id: PhaseId;
  label: string;
  stage: 'problem' | 'solution' | 'outcome';
  kicker: string;
  title: string;
  body: string;
  facts?: Fact[];
  where?: string;
  duration: number;
}

export const PHASES: Phase[] = [
  {
    id: 'well',
    label: 'The well',
    stage: 'problem',
    kicker: 'Upper Assam · Naharkatia · Well NHK-002',
    title: 'Two thousand eight hundred metres down. Drilling blind.',
    body: 'eRTMAC shows the engineer every parameter of the live well. Eleven wells were drilled through the same rock around it. Their history isn’t on her screen.',
    facts: [
      { label: 'Bit depth', value: '2,850 m MD' },
      { label: 'Formation at bit', value: 'Kopili' },
      { label: 'Offset wells', value: '11' },
    ],
    // Includes the Earth opening (globe → basin → rig), see scene/state.ts.
    duration: 13,
  },
  {
    id: 'buried',
    label: 'Buried',
    stage: 'problem',
    kicker: 'The problem',
    title: 'The answer exists. It’s on page two of one report out of thirty-nine.',
    body: 'Completion reports, daily drilling reports, scanned PDFs and one retired engineer’s memory. Searching them by hand takes hours. The bit doesn’t wait.',
    facts: [
      { label: 'Drilling reports, demo set', value: '39' },
      { label: 'Real Volve field documents', value: '14' },
      { label: 'Search by hand', value: 'Hours' },
    ],
    duration: 8,
  },
  {
    id: 'extract',
    label: 'Extract',
    stage: 'solution',
    kicker: '01 · Document intelligence',
    title: 'Every report, read and structured.',
    body: 'OCR and drilling-domain rules turn each page into events with depth, formation, severity, mitigation and outcome. Every value is physics-checked and linked to its source page.',
    facts: [
      { label: 'Pipeline', value: 'PDF → OCR → entities → checks' },
      { label: 'Example', value: 'BGJ-007 · Kick · 2,905.3 m' },
      { label: 'Proof', value: 'Source page, one click' },
    ],
    where: 'Document Ingestion',
    duration: 9,
  },
  {
    id: 'nearby',
    label: 'Nearby',
    stage: 'solution',
    kicker: '02 · Nearby wells',
    title: 'Every offset well, in its place.',
    body: 'Set a radius around the active well. Every well inside it rises out of the map with its depth and its history.',
    facts: [
      { label: 'Radius', value: 'User-defined' },
      { label: 'Wells in the basin', value: '12' },
      { label: 'Views', value: '2D map · 3D globe' },
    ],
    where: 'Offset Map · 3D Globe',
    duration: 8,
  },
  {
    id: 'relevant',
    label: 'Relevant',
    stage: 'solution',
    kicker: '03 · Offset ranking',
    title: 'Nearby isn’t the same as relevant.',
    body: 'The closest well, NHK-001, ranks ninth: it stops at 2,820 m, short of her depth. Distance, formation, depth, trajectory and hazard history decide which wells count.',
    facts: [
      { label: 'Rank 1', value: 'NHK-003 · 16.5 km · 0.59' },
      { label: 'Rank 2', value: 'BGJ-007 · 27.1 km · 0.56' },
      { label: 'Closest well', value: 'NHK-001 · rank 9' },
    ],
    where: 'Nearby Wells · Command Center',
    duration: 9,
  },
  {
    id: 'correlate',
    label: 'Correlate',
    stage: 'solution',
    kicker: '04 · Correlation',
    title: 'One formation runs under all of them.',
    body: 'Wells are tied together by formation, not just depth. In the Kopili, two of her best offset wells took kicks. The knowledge base finds them in seconds.',
    facts: [
      { label: 'NHK-003', value: 'Kick · 2,663.9 m · Kopili' },
      { label: 'BGJ-007', value: 'Kick · 2,905.3 m · Kopili' },
      { label: 'Search', value: 'Events · lessons · mitigations' },
    ],
    where: 'Geological Correlation · Historical Search',
    duration: 9,
  },
  {
    id: 'ahead',
    label: 'Ahead',
    stage: 'solution',
    kicker: '05 · Ahead-of-bit risk',
    title: 'See the risk before the bit reaches it.',
    body: 'Offset-well history is projected onto the path ahead of the bit. Overpressure risk peaks 20 m ahead; kick risk climbs again near 3,030 m.',
    facts: [
      { label: 'Overpressure', value: '0.70 at 2,870 m' },
      { label: 'Kick', value: '0.97 at 3,030 m' },
      { label: 'Kick, overall', value: 'HIGH' },
    ],
    where: 'Command Center · Alerts',
    duration: 7,
  },
  {
    id: 'decide',
    label: 'Decide',
    stage: 'outcome',
    kicker: 'The outcome',
    title: 'A warning she can act on, and check.',
    body: 'A recommendation, the offset wells it came from, and confidence split into four pillars. Nothing is a black box.',
    facts: [
      { label: 'Action', value: 'Kill mud on standby · slow ROP · watch pit volume' },
      { label: 'Evidence', value: '6 offset events · HIGH' },
      { label: 'Audit', value: 'Grounded in source reports' },
    ],
    where: 'Command Center',
    // Long enough for its own shot (rig, alert rings, crane out) and for
    // both panels to be read before the story ends.
    duration: 10,
  },
];

export const TOTAL_DURATION = PHASES.reduce((s, p) => s + p.duration, 0);

export const PHASE_STARTS = PHASES.reduce<number[]>((acc, _p, i) => {
  acc.push(i === 0 ? 0 : acc[i - 1] + PHASES[i - 1].duration);
  return acc;
}, []);

export function phaseAt(t: number): { index: number; local: number; p: number } {
  for (let i = PHASES.length - 1; i >= 0; i--) {
    if (t >= PHASE_STARTS[i]) {
      const local = t - PHASE_STARTS[i];
      return { index: i, local, p: Math.min(1, local / PHASES[i].duration) };
    }
  }
  return { index: 0, local: 0, p: 0 };
}

// ---------------------------------------------------------------------------
// Data shown in the scenes and HUD (backend output, demo scenario)
// ---------------------------------------------------------------------------

/** /api/v2/offset_rank/WELL-NHK-002?depth=2850. */
export const RANKING = [
  { id: 'NHK-003', score: 0.589, km: 16.5 },
  { id: 'BGJ-007', score: 0.564, km: 27.1 },
  { id: 'MRN-005', score: 0.559, km: 35.8 },
  { id: 'BGJ-008', score: 0.553, km: 37.9 },
  { id: 'MRN-006', score: 0.553, km: 31.5 },
  { id: 'BGJ-009', score: 0.532, km: 38.7 },
  { id: 'HGJ-010', score: 0.467, km: 54.7 },
  { id: 'MRN-004', score: 0.46, km: 39.5 },
  { id: 'NHK-001', score: 0.455, km: 12.3 },
  { id: 'HGJ-012', score: 0.381, km: 56.2 },
  { id: 'HGJ-011', score: 0.36, km: 53.9 },
];

/** /api/v2/ahead_of_bit/WELL-NHK-002?depth=2850&step_m=20. */
export const LOOKAHEAD = [
  { md: 2850, kick: 0.412, op: 0.507 },
  { md: 2870, kick: 0.147, op: 0.7 },
  { md: 2890, kick: 0.03, op: 0.498 },
  { md: 2910, kick: 0.0, op: 0.182 },
  { md: 2930, kick: 0.0, op: 0.034 },
  { md: 2950, kick: 0.0, op: 0.0 },
  { md: 2970, kick: 0.038, op: 0.0 },
  { md: 2990, kick: 0.203, op: 0.0 },
  { md: 3010, kick: 0.596, op: 0.0 },
  { md: 3030, kick: 0.969, op: 0.0 },
  { md: 3050, kick: 0.875, op: 0.0 },
];

/** /api/v2/analyze → KICK.confidence. */
export const PILLARS = [
  { label: 'Evidence strength', value: 'HIGH', score: 0.9 },
  { label: 'Sensor anomaly', value: '0.00', score: 0.04 },
  { label: 'Data quality', value: '0.60', score: 0.6 },
  { label: 'Audit status', value: 'GROUNDED', score: 1 },
];

/** Every DDR in real_data/evidence_pdfs, matched to its dataset event. */
export const DDRS: [string, number, string][] = [
  ['BGJ-007', 1236.7, 'STUCK_PIPE'], ['BGJ-007', 1345.2, 'CEMENTING_FAILURE'], ['BGJ-007', 2905.3, 'KICK'], ['BGJ-007', 563.2, 'STUCK_PIPE'],
  ['BGJ-008', 1244.0, 'STUCK_PIPE'], ['BGJ-008', 1813.3, 'KICK'], ['BGJ-008', 3173.1, 'MUD_LOSS'], ['BGJ-009', 1203.8, 'STUCK_PIPE'],
  ['BGJ-009', 1937.5, 'STUCK_PIPE'], ['HGJ-010', 1180.7, 'CEMENTING_FAILURE'], ['HGJ-010', 1257.3, 'WELLBORE_INSTABILITY'], ['HGJ-010', 1571.9, 'KICK'],
  ['HGJ-010', 2801.5, 'KICK'], ['HGJ-011', 1423.9, 'WELLBORE_INSTABILITY'], ['HGJ-011', 1614.4, 'STUCK_PIPE'], ['HGJ-011', 1739.0, 'STUCK_PIPE'],
  ['HGJ-011', 1834.7, 'WELLBORE_INSTABILITY'], ['HGJ-011', 2742.7, 'KICK'], ['HGJ-011', 573.8, 'STUCK_PIPE'], ['HGJ-012', 1396.6, 'STUCK_PIPE'],
  ['HGJ-012', 488.0, 'TORQUE_SPIKE'], ['HGJ-012', 691.4, 'CEMENTING_FAILURE'], ['MRN-004', 1324.0, 'WELLBORE_INSTABILITY'], ['MRN-004', 496.0, 'STUCK_PIPE'],
  ['MRN-005', 1179.4, 'WELLBORE_INSTABILITY'], ['MRN-005', 1281.1, 'WELLBORE_INSTABILITY'], ['MRN-005', 1844.0, 'WELLBORE_INSTABILITY'], ['MRN-005', 3069.8, 'KICK'],
  ['MRN-006', 1383.5, 'STUCK_PIPE'], ['MRN-006', 1490.1, 'STUCK_PIPE'], ['MRN-006', 1835.5, 'MUD_LOSS'], ['MRN-006', 2902.1, 'KICK'],
  ['MRN-006', 569.8, 'STUCK_PIPE'], ['NHK-001', 1221.5, 'CEMENTING_FAILURE'], ['NHK-001', 2658.5, 'MUD_LOSS'], ['NHK-002', 1459.2, 'WELLBORE_INSTABILITY'],
  ['NHK-002', 1620.3, 'KICK'], ['NHK-003', 2663.9, 'KICK'], ['NHK-003', 3061.5, 'KICK'],
];
/** Index of the report that matters: BGJ-007, kick at 2,905.3 m. */
export const KEY_DDR = 2;
