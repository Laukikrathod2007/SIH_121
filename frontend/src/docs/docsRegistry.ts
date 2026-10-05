import overviewContent from './content/index.md?raw';
import problemStatementContent from './content/problem-statement.md?raw';
import systemDesignContent from './content/architecture/system-design.md?raw';
import endToEndDataFlowContent from './content/architecture/end-to-end-data-flow.md?raw';
import ertmacIntegrationContent from './content/architecture/ertmac-integration.md?raw';
import ingestionPipelineContent from './content/document-intelligence/ingestion-pipeline.md?raw';
import normalizationContent from './content/document-intelligence/normalization-and-validation.md?raw';
import agenticRagContent from './content/document-intelligence/agentic-rag-and-provenance.md?raw';
import geospatialOffsetContent from './content/well-intelligence/geospatial-offset-discovery.md?raw';
import depthCorrelationContent from './content/well-intelligence/depth-and-formation-correlation.md?raw';
import historicalEventsContent from './content/well-intelligence/historical-events-and-memory.md?raw';
import riskTaxonomyContent from './content/risk-intelligence/risk-taxonomy.md?raw';
import predictionMethodologyContent from './content/risk-intelligence/prediction-methodology.md?raw';
import aheadOfBitAlertsContent from './content/risk-intelligence/ahead-of-bit-alerts.md?raw';
import algorithmsFormulasContent from './content/engineering/algorithms-and-formulas.md?raw';
import dataModelsContent from './content/engineering/data-models.md?raw';
import apiReferenceContent from './content/engineering/api-reference.md?raw';
import technologyStackContent from './content/engineering/technology-stack.md?raw';
import cockpitDashboardContent from './content/product-guide/cockpit-and-dashboard.md?raw';
import operationalWorkflowsContent from './content/product-guide/operational-workflows.md?raw';
import uspDifferentiationContent from './content/product-guide/usp-and-differentiation.md?raw';
import requirementsTraceabilityContent from './content/reference/requirements-traceability.md?raw';
import glossaryContent from './content/reference/glossary.md?raw';

export interface DocItem {
  id: string;
  slug: string;
  title: string;
  category: string;
  description: string;
  badge?: string;
  readingTime: string;
  content: string;
}

export interface DocCategory {
  name: string;
  iconName: string;
  description: string;
  items: DocItem[];
}

export const DOCS_CATEGORIES: DocCategory[] = [
  {
    name: 'Getting Started',
    iconName: 'Compass',
    description: 'Executive overview, industrial motivation, and problem statement decomposition.',
    items: [
      {
        id: 'overview',
        slug: 'overview',
        title: 'Executive Overview & Vision',
        category: 'Getting Started',
        description: 'AI-powered offset-well intelligence and decision support for Oil India Limited.',
        badge: 'CORE',
        readingTime: '6 min read',
        content: overviewContent,
      },
      {
        id: 'problem-statement',
        slug: 'problem-statement',
        title: 'Official SIH26121 Problem Statement',
        category: 'Getting Started',
        description: 'Complete background, industrial challenges, and 7 mandated deliverables.',
        badge: 'MANDATE',
        readingTime: '8 min read',
        content: problemStatementContent,
      },
    ],
  },
  {
    name: 'System Architecture',
    iconName: 'Layers',
    description: 'High-level architecture, service decomposition, and real-time streaming flows.',
    items: [
      {
        id: 'system-design',
        slug: 'system-design',
        title: 'System Design & Logical Architecture',
        category: 'System Architecture',
        description: '4-tier component architecture, service boundaries, and runtime contracts.',
        badge: 'ARCHITECTURE',
        readingTime: '9 min read',
        content: systemDesignContent,
      },
      {
        id: 'end-to-end-data-flow',
        slug: 'end-to-end-data-flow',
        title: 'End-to-End Operational Data Flow',
        category: 'System Architecture',
        description: 'The journey from raw rig sensor streams and legacy PDFs to predictive lookahead advisories.',
        badge: 'DATA FLOW',
        readingTime: '7 min read',
        content: endToEndDataFlowContent,
      },
      {
        id: 'ertmac-integration',
        slug: 'ertmac-integration',
        title: 'eRTMAC Integration & Real-Time Protocols',
        category: 'System Architecture',
        description: 'WITSML, WITS0, and OPC-UA edge streaming with read-only safety perimeters.',
        badge: 'STREAMING',
        readingTime: '8 min read',
        content: ertmacIntegrationContent,
      },
    ],
  },
  {
    name: 'Document Intelligence',
    iconName: 'FileText',
    description: '6-tier vision OCR, domain entity extraction, and subsurface Agentic RAG.',
    items: [
      {
        id: 'ingestion-pipeline',
        slug: 'ingestion-pipeline',
        title: '6-Tier Ingestion & Vision OCR Pipeline',
        category: 'Document Intelligence',
        description: 'Automated table extraction, Docling Vision OCR, and Layer-5 physics auto-repair.',
        badge: 'VISION OCR',
        readingTime: '9 min read',
        content: ingestionPipelineContent,
      },
      {
        id: 'normalization-and-validation',
        slug: 'normalization-and-validation',
        title: 'Canonical Data Normalization & Schemas',
        category: 'Document Intelligence',
        description: 'PPDM 3.9 & OSDU alignment, geodetic coordinates, and depth reference conversion.',
        badge: 'PPDM / OSDU',
        readingTime: '7 min read',
        content: normalizationContent,
      },
      {
        id: 'agentic-rag-and-provenance',
        slug: 'agentic-rag-and-provenance',
        title: 'Subsurface Agentic RAG & Evidence Grounding',
        category: 'Document Intelligence',
        description: 'Hybrid vector retrieval with strict page-level PDF citations and provenance tracking.',
        badge: 'AI / RAG',
        readingTime: '8 min read',
        content: agenticRagContent,
      },
    ],
  },
  {
    name: 'Well Intelligence',
    iconName: 'MapPin',
    description: 'Geospatial candidate discovery, 3D wellbore math, and stratigraphic depth tracks.',
    items: [
      {
        id: 'geospatial-offset-discovery',
        slug: 'geospatial-offset-discovery',
        title: 'Geospatial Offset-Well Discovery',
        category: 'Well Intelligence',
        description: '2D Leaflet SCADA GIS, 3D WebGL Globe, and structural fault boundary detection.',
        badge: '2D/3D GIS',
        readingTime: '7 min read',
        content: geospatialOffsetContent,
      },
      {
        id: 'depth-and-formation-correlation',
        slug: 'depth-and-formation-correlation',
        title: 'Stratigraphic & Depth-Aware Correlation',
        category: 'Well Intelligence',
        description: 'Minimum Curvature trajectory math, MD vs. TVD conversion, and dimensionless coordinate ξ.',
        badge: 'ALGORITHMS',
        readingTime: '10 min read',
        content: depthCorrelationContent,
      },
      {
        id: 'historical-events-and-memory',
        slug: 'historical-events-and-memory',
        title: 'Historical Events & Institutional Memory',
        category: 'Well Intelligence',
        description: 'Structured drilling complication taxonomy, NPT impacts, and mitigation archives.',
        badge: 'KNOWLEDGE',
        readingTime: '7 min read',
        content: historicalEventsContent,
      },
    ],
  },
  {
    name: 'Risk Intelligence',
    iconName: 'ShieldAlert',
    description: 'Physical hazard taxonomy, multi-signal risk fusion, and ahead-of-bit lookahead.',
    items: [
      {
        id: 'risk-taxonomy',
        slug: 'risk-taxonomy',
        title: 'Physical Drilling Hazard Taxonomy',
        category: 'Risk Intelligence',
        description: 'Mechanics, precursor telemetry signatures, and SPE mitigations for 7 hazard families.',
        badge: 'SPE / IADC',
        readingTime: '9 min read',
        content: riskTaxonomyContent,
      },
      {
        id: 'prediction-methodology',
        slug: 'prediction-methodology',
        title: 'Predictive Analytics & 4-Pillar Risk Fusion',
        category: 'Risk Intelligence',
        description: 'Physics rules, Isolation Forest, XGBoost classification, and offset priors.',
        badge: 'ML FUSION',
        readingTime: '9 min read',
        content: predictionMethodologyContent,
      },
      {
        id: 'ahead-of-bit-alerts',
        slug: 'ahead-of-bit-alerts',
        title: 'Ahead-of-Bit Lookahead Alerts & Advisories',
        category: 'Risk Intelligence',
        description: 'Risk corridor forward projection with 35-45 minutes of actionable lead time.',
        badge: '35-45m LEAD',
        readingTime: '8 min read',
        content: aheadOfBitAlertsContent,
      },
    ],
  },
  {
    name: 'Engineering Reference',
    iconName: 'Cpu',
    description: 'Mathematical formula derivations, database DDLs, API contracts, and stack specs.',
    items: [
      {
        id: 'algorithms-and-formulas',
        slug: 'algorithms-and-formulas',
        title: 'Algorithms & Mathematical Formulations',
        category: 'Engineering Reference',
        description: 'Complete mathematical equations, variable definitions, and worked numerical examples.',
        badge: 'MATH SPECS',
        readingTime: '12 min read',
        content: algorithmsFormulasContent,
      },
      {
        id: 'data-models',
        slug: 'data-models',
        title: 'Canonical Database Schemas & DDL',
        category: 'Engineering Reference',
        description: 'PostgreSQL 16, PostGIS 3.4 geometries, and pgvector HNSW index specifications.',
        badge: 'DATABASE',
        readingTime: '8 min read',
        content: dataModelsContent,
      },
      {
        id: 'api-reference',
        slug: 'api-reference',
        title: 'REST & WebSocket API Reference',
        category: 'Engineering Reference',
        description: 'OpenAPI endpoint specifications for /api/v1, /api/v2, and /api/v3 streaming.',
        badge: 'REST / WS',
        readingTime: '10 min read',
        content: apiReferenceContent,
      },
      {
        id: 'technology-stack',
        slug: 'technology-stack',
        title: 'Technology Stack & Engineering Decisions',
        category: 'Engineering Reference',
        description: 'Runtime dependencies, trade-off analysis, and Docker container architecture.',
        badge: 'DEVOPS',
        readingTime: '6 min read',
        content: technologyStackContent,
      },
    ],
  },
  {
    name: 'Product Guide',
    iconName: 'LayoutDashboard',
    description: 'Cockpit navigation guide, field scenarios, and strategic value differentiators.',
    items: [
      {
        id: 'cockpit-and-dashboard',
        slug: 'cockpit-and-dashboard',
        title: 'Operational Cockpit & Dashboard Tour',
        category: 'Product Guide',
        description: 'Walkthrough of all 14 SCADA cockpit screens, controls, and visual widgets.',
        badge: 'COCKPIT',
        readingTime: '8 min read',
        content: cockpitDashboardContent,
      },
      {
        id: 'operational-workflows',
        slug: 'operational-workflows',
        title: 'Real-World Field Scenarios',
        category: 'Product Guide',
        description: 'Step-by-step walkthroughs of pre-spud planning, mud loss lookahead, and kick control.',
        badge: 'WORKFLOWS',
        readingTime: '9 min read',
        content: operationalWorkflowsContent,
      },
      {
        id: 'usp-and-differentiation',
        slug: 'usp-and-differentiation',
        title: 'Strategic Differentiation & Business Value',
        category: 'Product Guide',
        description: 'Why eRTMAC-NWIS outperforms legacy GIS tools and generic LLM chatbots.',
        badge: 'VALUE / ROI',
        readingTime: '6 min read',
        content: uspDifferentiationContent,
      },
    ],
  },
  {
    name: 'Reference & Standards',
    iconName: 'BookMarked',
    description: 'Requirements traceability matrix, petroleum glossary, and technical citations.',
    items: [
      {
        id: 'requirements-traceability',
        slug: 'requirements-traceability',
        title: 'SIH26121 Requirements Traceability',
        category: 'Reference & Standards',
        description: 'Exhaustive verification matrix mapping all official requirements to implementations.',
        badge: '100% TRACEABLE',
        readingTime: '8 min read',
        content: requirementsTraceabilityContent,
      },
      {
        id: 'glossary',
        slug: 'glossary',
        title: 'Petroleum Engineering & AI Glossary',
        category: 'Reference & Standards',
        description: 'Authoritative dictionary of drilling mechanics, survey geodesy, and data science terms.',
        badge: 'GLOSSARY',
        readingTime: '7 min read',
        content: glossaryContent,
      },
    ],
  },
];

export const ALL_DOCS: DocItem[] = DOCS_CATEGORIES.flatMap((c) => c.items);

export function getDocBySlug(slug: string): DocItem | undefined {
  if (!slug || slug === 'index' || slug === 'docs') {
    return ALL_DOCS[0]; // Overview
  }
  return ALL_DOCS.find((d) => d.slug.toLowerCase() === slug.toLowerCase() || d.id.toLowerCase() === slug.toLowerCase());
}

export function getPrevNextDocs(slug: string): { prev?: DocItem; next?: DocItem } {
  const currentIndex = ALL_DOCS.findIndex((d) => d.slug.toLowerCase() === slug.toLowerCase() || d.id.toLowerCase() === slug.toLowerCase());
  if (currentIndex === -1) {
    return { prev: undefined, next: ALL_DOCS[1] };
  }
  return {
    prev: currentIndex > 0 ? ALL_DOCS[currentIndex - 1] : undefined,
    next: currentIndex < ALL_DOCS.length - 1 ? ALL_DOCS[currentIndex + 1] : undefined,
  };
}

export function searchDocs(query: string): Array<{ doc: DocItem; matchSnippet: string }> {
  if (!query || query.trim().length === 0) return [];
  const q = query.toLowerCase().trim();

  const results: Array<{ doc: DocItem; score: number; matchSnippet: string }> = [];

  for (const doc of ALL_DOCS) {
    let score = 0;
    let snippet = doc.description;

    if (doc.title.toLowerCase().includes(q)) score += 50;
    if (doc.category.toLowerCase().includes(q)) score += 20;
    if (doc.description.toLowerCase().includes(q)) score += 30;

    const contentLower = doc.content.toLowerCase();
    const index = contentLower.indexOf(q);
    if (index !== -1) {
      score += 15;
      const start = Math.max(0, index - 50);
      const end = Math.min(doc.content.length, index + 120);
      snippet = '...' + doc.content.substring(start, end).replace(/[#*`_]/g, '') + '...';
    }

    if (score > 0) {
      results.push({ doc, score, matchSnippet: snippet });
    }
  }

  return results.sort((a, b) => b.score - a.score).map((r) => ({ doc: r.doc, matchSnippet: r.matchSnippet }));
}
