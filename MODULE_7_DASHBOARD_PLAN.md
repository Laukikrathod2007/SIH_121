# Module 7: Central Dashboard & Integration Hub
## NWIS - Nearby Wells Intelligence System

---

## Executive Summary

Module 7 serves as the **unified command center** for the NWIS platform, integrating all six operational modules into a cohesive, role-based dashboard system. This module provides real-time monitoring, historical analytics, predictive insights, and alert management through an intuitive interface tailored to different user roles across Oil India Limited's drilling operations.

**Key Innovation**: Context-aware dashboard that adapts based on user role, active well status, and real-time risk levels, combining eRTMAC live data streams with historical offset well intelligence.

---

## 1. Dashboard Architecture Overview

### 1.1 System Integration Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    Module 7: Central Dashboard                   │
│                  (React/Next.js + TypeScript)                    │
└────────────┬───────────────────────────────────────────┬────────┘
             │                                           │
    ┌────────▼────────┐                         ┌───────▼────────┐
    │  Authentication  │                         │   WebSocket    │
    │   & RBAC Layer   │                         │   Gateway      │
    └────────┬────────┘                         └───────┬────────┘
             │                                           │
┌────────────▼──────────────────────────────────────────▼─────────┐
│                      API Gateway Layer                           │
│                    (FastAPI / Node.js)                           │
└──┬────┬─────┬──────┬───────┬────────┬──────────────────────────┘
   │    │     │      │       │        │
   ▼    ▼     ▼      ▼       ▼        ▼
┌────┐┌────┐┌────┐┌────┐┌────────┐┌──────┐
│Mod1││Mod2││Mod3││Mod4││Module5 ││Module│
│PDF ││Real││Geo ││ ML ││ Docs  ││ 6   │
│ETL ││Time││Viz ││Pred││Extract││Alerts│
└────┘└────┘└────┘└────┘└────────┘└──────┘
         ▲
         │
    ┌────▼─────────────────┐
    │  PostgreSQL + PostGIS │
    │   Central Database    │
    └──────────────────────┘
```

### 1.2 Core Dashboard Components

#### A. **Real-Time Operations Center** (Primary View)
- Live drilling telemetry visualization (Module 2 integration)
- Active well status board
- Real-time alert feed (Module 6 integration)
- Current vs planned performance metrics

#### B. **Offset Wells Intelligence Hub** (Secondary View)
- Interactive geospatial map (Module 3 integration)
- Historical well comparison tool
- Formation-depth correlation matrix
- NPT incident timeline and patterns

#### C. **Predictive Analytics Console** (Tertiary View)
- ML model predictions dashboard (Module 4 integration)
- Risk scoring heatmaps
- Probability curves for drilling hazards
- Offset well correlation insights

#### D. **Document & Knowledge Repository** (Supporting View)
- OCR-extracted data browser (Module 1 & 5 integration)
- Searchable DDR/WCR library
- Lessons learned database
- Best practices recommendations

#### E. **Alert & Notification Center** (Overlay Component)
- Real-time alert banner
- Historical alert log
- Alert acknowledgment workflow
- Escalation management

#### F. **Well Comparison & Benchmarking** (Analytical View)
- Multi-well performance comparison
- KPI benchmarking against offset wells
- Cost and time efficiency analysis
- Best-in-class operations identification

---

## 2. Detailed Dashboard Components

### 2.1 Home Dashboard (Landing Page)

**Layout**: Grid-based responsive layout (4x3 on desktop, stackable on mobile)

#### Top Row: Critical Metrics (Always Visible)
1. **Active Wells Status Card**
   - Number of active drilling operations
   - Current depth progress (% complete)
   - Real-time rig state (Drilling/Tripping/Circulating/Idle)
   - Color-coded health indicators (Green/Yellow/Red)

2. **Live Alert Summary**
   - Count by severity (Critical/Warning/Info)
   - Most recent unacknowledged alerts (top 3)
   - Average response time
   - Quick action buttons (View All/Acknowledge)

3. **Today's Performance Snapshot**
   - Footage drilled today (meters)
   - Average ROP (m/hr)
   - NPT hours today
   - Cost efficiency vs plan (%)

4. **Offset Well Intelligence Indicator**
   - Number of relevant offset wells in database
   - Similar conditions detected (count)
   - Historical incidents at current depth range
   - Recommended actions from AI

#### Middle Row: Real-Time Visualization
5. **Live Drilling Dashboard** (Full width, collapsible)
   - **Real-time line charts** (last 2 hours of data):
     - Bit Depth (MD & TVD)
     - Weight on Bit (WOB)
     - Rate of Penetration (ROP)
     - Torque & RPM
     - Standpipe Pressure (SPP)
     - Flow Rate
   - **Synchronized zoom** across all charts
   - **Anomaly highlighting** (shaded regions for alerts)
   - **Formation overlay** (geological layers at depth markers)
   - **Playback controls** for historical replay

6. **3D Well Visualization** (Interactive)
   - 3D wellbore trajectory
   - Current bit position (animated)
   - Formation layers with labels
   - Directional survey data
   - Clickable depth markers for detailed info

#### Bottom Row: Contextual Information
7. **Nearby Wells Map** (Interactive Leaflet.js)
   - Active well centered on map (Assam field coordinates)
   - Offset wells within 5/10/15 km radius (user-configurable)
   - Color-coded markers:
     - 🟢 Completed wells (no major incidents)
     - 🟡 Completed wells (with NPT incidents)
     - 🔴 Wells with high-severity incidents
     - 🔵 Currently drilling
   - Click marker → Well summary card
   - Distance and azimuth from active well

8. **Formation Correlation Chart**
   - Depth vs Formation comparison across wells
   - Highlight current depth in active well
   - Show where offset wells encountered issues
   - Predicted formation tops (ML-enhanced)

9. **Incident & NPT Timeline**
   - Historical timeline of incidents in offset wells
   - Filtered by depth range (±100m from current depth)
   - Incident type icons (stuck pipe, lost circulation, kick, etc.)
   - Hover for details, click for full report

10. **Recommendations Panel** (AI-Powered)
    - Top 3 actionable insights from ML models
    - "Wells like this one experienced..." context
    - Risk mitigation suggestions
    - Links to relevant historical documents

---

### 2.2 Well Detail View (Drill-Down Page)

**Navigation**: Accessible by clicking any well on map or from well selector dropdown

#### Header Section
- **Well Identity Card**
  - Well name (e.g., "DG-003")
  - Field name (e.g., "Digboi Field")
  - Coordinates (Lat/Lon)
  - Attribution: "Engineering data from Utah FORGE analogue well 16A(78)-32"
  - Status badge (Drilling/Completed/Suspended)
  - Spud date & completion date (if applicable)

#### Tabs Navigation
1. **Overview Tab**
   - Well summary statistics
   - Key milestones timeline
   - Final depth (MD & TVD)
   - Total drilling days
   - NPT summary (hours & %)
   - Cost summary (if available)

2. **Real-Time Data Tab** (For active wells only)
   - Same live charts as home dashboard
   - Extended historical view (24 hours / 7 days selectable)
   - Parameter statistics (min/max/avg)
   - Export data functionality (CSV/JSON)

3. **Historical Analysis Tab**
   - Depth vs Time chart
   - ROP comparison against plan
   - Mud properties timeline
   - Bit performance tracking
   - Daily drilling reports integrated view

4. **Geological Data Tab**
   - Formation tops table (depth, name, identification method)
   - Gamma ray / resistivity logs (if available)
   - 3D wellbore trajectory with formations
   - Offset well formation correlation

5. **Incidents & NPT Tab**
   - Comprehensive incident log table
     - Date/time, depth, incident type, severity
     - Duration (hours), cost impact
     - Root cause analysis
     - Corrective actions taken
   - NPT breakdown chart (by category)
   - Lessons learned section

6. **Documents Tab**
   - List of associated documents (DDR, WCR, EOWR, etc.)
   - Document type filter
   - OCR extraction status indicator
   - View PDF / View extracted JSON buttons
   - Full-text search within documents

7. **Predictions Tab** (For active wells)
   - ML model outputs dashboard
   - Stuck pipe risk probability (next 4 hours)
   - Lost circulation risk score
   - Equipment failure predictions
   - Model confidence intervals
   - Feature importance charts (which parameters influenced prediction)

---

### 2.3 Analytics Dashboard (Advanced Users)

**Purpose**: Deep-dive analytical tools for drilling engineers and data scientists

#### Section A: Multi-Well Comparison Tool
- **Well Selector**: Multi-select dropdown or checkboxes
- **Comparison Metrics**:
  - Depth vs Days (performance curve overlay)
  - Average ROP by formation
  - NPT hours comparison
  - Cost per meter drilled
  - Bit runs efficiency
- **Normalization Options**:
  - By depth interval (e.g., 500-1000m)
  - By formation name
  - By time period
- **Export**: Chart images (PNG) or data tables (Excel)

#### Section B: KPI Benchmarking Dashboard
- **Key Performance Indicators**:
  - Drilling efficiency (m/day)
  - ROP by formation type
  - Tripping speed (avg m/hr)
  - Connection time (avg minutes)
  - Circulating hours per day
  - NPT % of total time
- **Benchmarking Views**:
  - Current well vs field average
  - Current well vs best-in-class well
  - Historical trend (improvement over time)
  - Percentile ranking (P10/P50/P90)

#### Section C: Risk Heatmap
- **2D Heatmap**: Depth (Y-axis) vs Formation (X-axis)
- **Color intensity**: Incident frequency or NPT hours
- **Hover tooltip**: Specific incident details
- **Use case**: Identify high-risk depth intervals

#### Section D: Offset Well Correlation Matrix
- **Matrix View**: Wells (rows) vs similarity factors (columns)
  - Geographic distance (km)
  - Formation overlap count
  - ML-calculated similarity score (0-1)
  - Incident pattern match
- **Sorting**: By any column
- **Filtering**: Distance threshold, minimum similarity score
- **Use case**: Find most relevant offset wells for current operation

---

### 2.4 Alert & Notification Center

**Purpose**: Centralized alert management across all modules

#### Alert Feed (Main Panel)
- **Real-time stream** (WebSocket-powered)
- **Alert Cards** with:
  - Severity badge (Critical/Warning/Info)
  - Alert type icon (stuck pipe, lost circulation, parameter limit, etc.)
  - Timestamp
  - Well name
  - Message description
  - Depth at time of alert
  - Predicted outcome (if ML-generated)
  - Action buttons: Acknowledge / View Details / Escalate

#### Alert Filtering & Search
- **Filters**:
  - By severity
  - By alert type
  - By well
  - By date range
  - Acknowledged vs unacknowledged
- **Search**: Full-text search in alert messages

#### Alert Detail View (Modal)
- **Header**: Alert type, severity, timestamp
- **Context**:
  - Telemetry snapshot at time of alert (table)
  - Chart showing parameter trend leading to alert
  - Offset well context: "Well NH-001 had similar alert at 2,340m → resulted in 4hr NPT"
- **Actions**:
  - Acknowledge (with optional notes)
  - Resolve (mark as addressed)
  - Escalate to supervisor
  - Link to incident report (if incident occurred)

#### Alert Configuration Panel (Admin Only)
- **Threshold Management**:
  - Set parameter limits (WOB max, ROP min, Torque max, etc.)
  - Configure alert severity levels
  - Enable/disable alert types
- **Notification Settings**:
  - Email notifications (to specific roles)
  - SMS alerts for critical events
  - Dashboard popup vs silent logging

---

### 2.5 Document Repository & Knowledge Base

**Purpose**: Searchable interface for all historical drilling documents

#### Search Interface
- **Full-text search** across all documents
- **Advanced filters**:
  - Document type (DDR, WCR, EOWR, Geology Report)
  - Well name
  - Date range
  - Extraction status (completed, pending, failed)
- **Search results**:
  - Document thumbnail (PDF first page)
  - Title, well name, date
  - Relevance score
  - Quick actions: View PDF / View JSON / Download

#### Document Viewer
- **PDF Viewer**:
  - Embedded PDF renderer (PDF.js)
  - Page navigation, zoom, search within PDF
  - Annotation support (add notes)
- **Extracted Data Viewer** (JSON):
  - Structured JSON tree view
  - Highlight mode: Click JSON field → Highlight corresponding PDF text (if available)
  - Edit capability (for data correction)

#### Knowledge Base Browser
- **Categorized sections**:
  - Drilling Best Practices
  - Incident Root Cause Analysis
  - Formation-Specific Guidelines
  - Equipment Maintenance Logs
- **Tagging system**: Tag documents with keywords for easy retrieval
- **Contribution workflow**: Users can submit new knowledge articles (requires admin approval)

---

### 2.6 Reports & Export Module

**Purpose**: Generate customizable reports for management and compliance

#### Pre-Built Report Templates
1. **Daily Drilling Summary**
   - Progress today (depth, footage drilled)
   - NPT summary
   - Alerts triggered
   - Operations timeline
   - Mud properties snapshot
   - Next 24h outlook (predicted depth)

2. **Weekly Performance Report**
   - Footage drilled vs plan
   - ROP trends
   - NPT breakdown by category
   - Cost analysis
   - Incident summary
   - Offset well comparison

3. **Incident Investigation Report**
   - Incident details (type, time, depth, duration)
   - Telemetry data before/during/after
   - Offset well precedents
   - Root cause analysis (ML-assisted)
   - Corrective actions taken
   - Cost impact

4. **Well Completion Summary**
   - Final well statistics
   - Formation tops encountered
   - Total drilling time and cost
   - NPT analysis
   - Lessons learned
   - Recommendations for future wells

#### Custom Report Builder
- **Drag-and-drop interface**:
  - Select wells
  - Choose date range
  - Add KPI widgets (charts, tables, metrics)
  - Add text sections
- **Export formats**: PDF, Excel, PowerPoint
- **Scheduling**: Automate report generation (daily/weekly/monthly)

---

## 3. User Roles & Access Control (RBAC)

### 3.1 Role-Based Access Control Architecture

**Implementation**: PostgreSQL role-based permissions + JWT token-based authentication

#### Users Table Schema (Additional to Module 1 schema)
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- bcrypt hashed
    full_name VARCHAR(100),
    role_id INT REFERENCES roles(role_id),
    department VARCHAR(50), -- 'Drilling', 'Geology', 'Operations', 'Management'
    assigned_fields JSON, -- Array of fields user can access: ["Digboi", "Nahorkatiya"]
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    role_id INT PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    role_description TEXT,
    permissions JSON -- Detailed permission matrix
);

CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100), -- 'view_well_data', 'acknowledge_alert', 'export_report'
    resource_type VARCHAR(50), -- 'well', 'document', 'alert'
    resource_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    details JSON
);
```

---

### 3.2 Defined User Roles

#### **Role 1: Field Operator / Roughneck**
**Primary Users**: Rig floor personnel (Roughnecks, Derrickhands, Motorhands)

**Dashboard Access**: **Limited Read-Only**
- ✅ View live drilling dashboard (basic telemetry only)
- ✅ View active alerts (critical severity only)
- ✅ View current well status
- ❌ No access to historical data
- ❌ No access to predictive analytics
- ❌ No access to documents
- ❌ Cannot acknowledge alerts or modify data

**Use Case**: Quick situational awareness on rig floor tablet, monitor critical parameters (WOB, RPM, Torque).

**Justification**: Field operators need real-time visibility to adjust drilling operations, but don't require historical analysis or administrative functions.

---

#### **Role 2: Driller / Tool Pusher**
**Primary Users**: Drillers leading rig crews, Tool Pushers (rig supervisors)

**Dashboard Access**: **Operational Control**
- ✅ Full access to real-time drilling dashboard
- ✅ View and **acknowledge** alerts (all severity levels)
- ✅ View offset well map (basic information only)
- ✅ View current well geological data
- ✅ Limited historical data (last 7 days)
- ✅ View incident reports (read-only)
- ✅ Export daily drilling reports
- ❌ No access to predictive analytics (ML models)
- ❌ Cannot modify database or configure alerts
- ❌ Limited document access (DDRs only, not WCRs)

**Use Case**: Manage drilling operations in real-time, respond to alerts, compare current performance against recent history, export daily reports for handover.

**Justification**: Drillers need operational control to react to drilling conditions and alerts, but detailed engineering analysis is handled by engineers.

---

#### **Role 3: Drilling Engineer**
**Primary Users**: Drilling engineers (field and office-based), MWD engineers

**Dashboard Access**: **Full Analytical Access**
- ✅ Full access to all real-time and historical data
- ✅ View, acknowledge, and **escalate** alerts
- ✅ Full access to offset wells intelligence hub
- ✅ Access predictive analytics console (view ML predictions)
- ✅ Multi-well comparison and benchmarking tools
- ✅ Full document repository access (DDR, WCR, EOWR)
- ✅ Export custom reports (all formats)
- ✅ Add annotations and comments to incidents
- ✅ Submit knowledge base articles
- ❌ Cannot configure alert thresholds or ML models
- ❌ Cannot manage users or roles
- ❌ Cannot delete or modify historical database records

**Use Case**: Perform deep-dive analysis of drilling performance, correlate with offset wells, use predictive analytics to proactively mitigate risks, prepare engineering reports, document lessons learned.

**Justification**: Engineers are the primary technical users who leverage NWIS for decision-making and continuous improvement. They need full analytical capabilities but not system administration access.

---

#### **Role 4: Geologist / Geoscience Specialist**
**Primary Users**: Geologists, formation evaluation specialists

**Dashboard Access**: **Geological & Formation-Focused**
- ✅ View real-time drilling dashboard (focus on gamma ray, ROP, formation tops)
- ✅ Full access to geological data and formation correlation
- ✅ Offset wells map (focus on geological similarities)
- ✅ Access document repository (focus on geology reports, formation evaluation)
- ✅ View incidents related to geological events (lost circulation, kicks)
- ✅ Add formation top annotations
- ✅ Export geological reports
- ⚠️ Limited access to mechanical drilling parameters (view only, no analysis tools)
- ❌ No access to cost data
- ❌ Cannot configure alerts or acknowledge drilling alerts

**Use Case**: Monitor formation characteristics in real-time, correlate geological markers across offset wells, identify geological risks (overpressure zones, lost circulation zones), update formation tops database.

**Justification**: Geologists focus on subsurface conditions and formation evaluation, not mechanical drilling operations. Tailored access improves efficiency and reduces information overload.

---

#### **Role 5: Operations Manager / Superintendent**
**Primary Users**: Operations managers, drilling superintendents, field coordinators

**Dashboard Access**: **Executive & Multi-Well Oversight**
- ✅ Dashboard summary view for all active wells (fleet-level monitoring)
- ✅ High-level KPIs and performance metrics
- ✅ Alert summary across all wells
- ✅ NPT and cost analysis dashboards
- ✅ Well comparison and benchmarking (focus on KPIs, not detailed telemetry)
- ✅ Access pre-built management reports (daily/weekly summaries)
- ✅ Escalated alerts and incident reports (high-level view)
- ⚠️ Can view detailed well data on-demand, but default view is aggregated
- ❌ No access to raw telemetry data or ML model internals
- ❌ Cannot modify database or alert configurations

**Use Case**: Monitor multiple wells simultaneously, identify underperforming operations, review NPT trends, make strategic decisions on resource allocation, review incident reports for management escalation.

**Justification**: Managers need high-level visibility and decision-support insights, not granular operational details. Fleet-level dashboard improves situational awareness across all fields.

---

#### **Role 6: Data Scientist / ML Engineer**
**Primary Users**: Data scientists, ML engineers, analytics team

**Dashboard Access**: **Data & Model Management**
- ✅ Full access to all raw and processed data
- ✅ Access to ML model training data and labels
- ✅ View and analyze prediction accuracy metrics
- ✅ Access feature engineering pipeline
- ✅ Export large datasets (API access for bulk downloads)
- ✅ View model performance dashboards (precision, recall, F1 score)
- ✅ Upload and deploy new ML models (with approval workflow)
- ✅ Access user annotations for training data
- ⚠️ Limited access to operational dashboards (focus on data pipelines)
- ❌ Cannot acknowledge alerts or modify operational data
- ❌ No access to sensitive cost or personnel data

**Use Case**: Develop and improve predictive models, analyze model performance, create new features from telemetry data, retrain models with new labeled data, research drilling patterns for ML insights.

**Justification**: Data scientists focus on model accuracy and data quality, not day-to-day drilling operations. Segregated access prevents accidental operational disruptions.

---

#### **Role 7: System Administrator**
**Primary Users**: IT team, database administrators, NWIS platform maintainers

**Dashboard Access**: **Full System Control**
- ✅ Full administrative access to all modules
- ✅ User and role management (create, edit, delete users)
- ✅ Configure alert thresholds and rules
- ✅ Database management (backup, restore, schema updates)
- ✅ System health monitoring and performance metrics
- ✅ Audit log access (view all user actions)
- ✅ Manage document extraction workflows
- ✅ Configure API keys and integrations
- ✅ Deploy ML models to production
- ⚠️ System admin dashboard (separate from operational dashboard)

**Use Case**: Maintain system uptime, troubleshoot technical issues, manage user access, configure system parameters, monitor data ingestion pipelines, ensure data security and compliance.

**Justification**: Administrators need unrestricted access to maintain system integrity and security, but operate in a separate administrative interface to avoid confusion with operational dashboards.

---

#### **Role 8: Executive / Management (Read-Only)**
**Primary Users**: Senior management, C-suite executives, external auditors

**Dashboard Access**: **Executive Summary View**
- ✅ Executive summary dashboard (high-level KPIs only)
- ✅ Field-level performance metrics (cost, NPT, footage drilled)
- ✅ Major incident reports and safety metrics
- ✅ Pre-built executive reports (quarterly, annual)
- ✅ Strategic analytics (field comparison, investment ROI)
- ❌ No access to real-time telemetry or detailed operations
- ❌ No access to alerts or incident management
- ❌ No access to documents or raw data
- ❌ Fully read-only access (no actions or modifications)

**Use Case**: Monitor organizational performance across all fields, review major incidents for board meetings, assess drilling efficiency for strategic planning, export summary reports for stakeholders.

**Justification**: Executives need high-level strategic insights without operational details. Simplified dashboard prevents information overload and focuses on business-critical metrics.

---

### 3.3 Permission Matrix

| **Feature / Module** | Field Operator | Driller | Engineer | Geologist | Operations Mgr | Data Scientist | Admin | Executive |
|----------------------|:--------------:|:-------:|:--------:|:---------:|:--------------:|:--------------:|:-----:|:---------:|
| **Real-Time Telemetry** | 🟢 View Basic | 🟢 View Full | 🟢 View + Export | 🟡 View Limited | 🟡 Summary | 🟢 Raw Access | 🟢 Full | ❌ |
| **Alert Management** | 🟡 View Critical | 🟢 Acknowledge | 🟢 Escalate | 🟡 View Only | 🟢 View All | ❌ | 🟢 Configure | 🟡 Summary |
| **Offset Wells Map** | ❌ | 🟡 Basic | 🟢 Full | 🟢 Geo Focus | 🟢 Multi-Well | 🟢 Data Export | 🟢 Full | 🟡 Summary |
| **Predictive Analytics** | ❌ | ❌ | 🟢 View Predictions | 🟡 Geo Risks | 🟢 View | 🟢 Model Mgmt | 🟢 Full | ❌ |
| **Historical Data** | ❌ | 🟡 7 Days | 🟢 Unlimited | 🟢 Unlimited | 🟢 KPIs | 🟢 Full | 🟢 Full | 🟡 Summary |
| **Document Access** | ❌ | 🟡 DDR Only | 🟢 All Docs | 🟢 Geo Docs | 🟢 All Docs | 🟢 All Docs | 🟢 Full | ❌ |
| **Data Export** | ❌ | 🟡 Daily Report | 🟢 Custom Reports | 🟢 Geo Reports | 🟢 Mgmt Reports | 🟢 Bulk Export | 🟢 Full | 🟢 Exec Reports |
| **Edit/Annotate** | ❌ | ❌ | 🟢 Annotations | 🟢 Formation Tops | ❌ | 🟢 Labels | 🟢 Full | ❌ |
| **User Management** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🟢 Full | ❌ |
| **Alert Configuration** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🟢 Full | ❌ |

**Legend**:
- 🟢 = Full Access
- 🟡 = Limited / Conditional Access
- ❌ = No Access

---

### 3.4 Field-Level Access Control

**Requirement**: Users can only access data for fields/wells they are assigned to.

**Implementation**:
- `users.assigned_fields` JSON column contains array of accessible fields:
  ```json
  ["Digboi", "Nahorkatiya"]
  ```
- All database queries filtered by:
  ```sql
  WHERE wells.field_name = ANY(user.assigned_fields)
  ```
- **Exception**: Administrators and Data Scientists have access to all fields

**Use Case**: Engineer assigned to Digboi field cannot view Moran field data (competitive sensitivity or operational segmentation).

---

### 3.5 Audit Logging & Compliance

**Purpose**: Track all user actions for security, compliance, and troubleshooting.

**Logged Actions**:
- User login/logout
- Data access (well viewed, document opened, report exported)
- Alert acknowledgment and escalation
- Data modifications (annotations, formation tops updates)
- Configuration changes (alert thresholds, user roles)
- Failed authentication attempts

**Audit Dashboard** (Admin only):
- Recent activity log (last 100 actions)
- User activity report (by user or date range)
- Security alerts (multiple failed logins, unusual access patterns)
- Data export tracking (who exported what data when)

**Compliance**: Audit logs retained for 2 years, exportable for external audits.

---

## 4. Technology Stack for Module 7

### 4.1 Frontend Technologies

| **Component** | **Technology Choice** | **Rationale** |
|---------------|-----------------------|---------------|
| **Framework** | React 18 + Next.js 14 | Server-side rendering (SSR) for performance, built-in routing, API routes for backend integration |
| **Language** | TypeScript 5.x | Type safety, better IDE support, reduces runtime errors |
| **State Management** | Zustand + React Query | Zustand for global state (user, active well), React Query for server state (caching, automatic refetching) |
| **UI Components** | shadcn/ui + Tailwind CSS | Modern, customizable component library; Tailwind for rapid styling |
| **Charts** | Recharts (primary), Apache ECharts (advanced) | Recharts for simple time-series, ECharts for complex 3D/heatmaps |
| **Maps** | Leaflet.js + React-Leaflet | Open-source, lightweight, supports custom markers and overlays |
| **3D Visualization** | Cesium.js (optional) | For 3D wellbore trajectory visualization (if required) |
| **Real-Time Data** | Native WebSocket API | Direct connection to Module 2 FastAPI WebSocket |
| **PDF Viewer** | react-pdf (PDF.js wrapper) | Render PDFs in browser with search and zoom |
| **Date/Time** | date-fns | Lightweight, modular date manipulation |
| **Forms** | React Hook Form + Zod | Type-safe form validation |
| **Notifications** | React Hot Toast | Non-intrusive toast notifications for alerts |

### 4.2 Backend/API Layer

| **Component** | **Technology Choice** | **Rationale** |
|---------------|-----------------------|---------------|
| **API Framework** | FastAPI (Python 3.11) | Async support, automatic OpenAPI docs, WebSocket support, integrates with Module 2 |
| **Authentication** | JWT (JSON Web Tokens) | Stateless authentication, scalable, works across microservices |
| **Authorization** | Role-based middleware (custom) | Check user role and assigned fields on every API request |
| **Database ORM** | SQLAlchemy 2.x | Mature Python ORM, supports PostgreSQL, complex queries |
| **WebSocket** | FastAPI WebSockets | Native support, broadcast to multiple clients |
| **Caching** | Redis | Cache frequently accessed data (well metadata, KPIs), reduce database load |
| **Task Queue** | Celery + Redis | Background jobs (report generation, bulk data export) |
| **API Documentation** | Swagger UI (auto-generated) | FastAPI generates interactive API docs automatically |

### 4.3 Deployment & Infrastructure

| **Component** | **Technology Choice** | **Rationale** |
|---------------|-----------------------|---------------|
| **Containerization** | Docker + Docker Compose | Consistent environments, easy deployment |
| **Web Server** | Nginx (reverse proxy) | Serve static files, load balancing, SSL termination |
| **Database** | PostgreSQL 15 + PostGIS | Already defined in Module 1-6, geospatial support |
| **Monitoring** | Grafana + Prometheus | Real-time system health monitoring, visualize metrics |
| **Logging** | ELK Stack (Elasticsearch, Logstash, Kibana) | Centralized logging for debugging and audit trails |
| **CI/CD** | GitHub Actions | Automated testing and deployment |

### 4.4 Security Measures

- **HTTPS Only**: Enforce SSL/TLS encryption
- **CORS Policy**: Restrict API access to known frontend domains
- **Rate Limiting**: Prevent API abuse (e.g., max 100 requests/min per user)
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy
- **XSS Protection**: Sanitize all user inputs, use Content Security Policy headers
- **Password Security**: bcrypt hashing (cost factor 12)
- **Session Timeout**: Auto-logout after 30 minutes of inactivity
- **Two-Factor Authentication (Optional)**: For admin and data scientist roles

---

## 5. Key Features & Innovations

### 5.1 Context-Aware Dashboard

**Innovation**: Dashboard automatically adapts based on:
1. **User Role**: Engineers see analytics, operators see simplified views
2. **Active Well Status**: If well is drilling → Show real-time telemetry prominently; If well is tripping → Show tripping speed metrics
3. **Alert Severity**: Critical alert → Dashboard highlights affected charts and shows recommended actions
4. **Depth Context**: At 2,500m depth → Automatically show offset well incidents at ±100m depth range

**Implementation**: React components conditionally render based on user context and well state.

---

### 5.2 Offset Well "What If" Simulator

**Feature**: Interactive tool to answer "What would have happened in this offset well at our current conditions?"

**How It Works**:
1. User selects offset well
2. System shows that well's parameters at equivalent depth
3. User can adjust current well's parameters (e.g., increase WOB by 20%)
4. ML model predicts outcome based on offset well's actual results

**Use Case**: "If we increase WOB to 40 klbs like Well NH-001 did at this depth, what's the risk of stuck pipe?"

---

### 5.3 Intelligent Alert Prioritization

**Problem**: Too many alerts → Alert fatigue

**Solution**: ML-powered alert ranking
- **Priority Score** (0-100): Combines severity + probability + potential impact
- **Context-Aware**: "High WOB" alert is more critical if offset wells had stuck pipe at this depth
- **Adaptive Thresholds**: Alert thresholds adjust based on formation and well trajectory (not static)

**UI**: Alerts sorted by priority score, not just severity. Top 3 alerts highlighted.

---

### 5.4 Auto-Generated Drilling Playbook

**Feature**: System generates real-time recommendations based on offset well analysis

**Example Playbook Entry**:
```
🎯 RECOMMENDATION: Approaching 2,600m depth

📍 Context:
  - 3 offset wells experienced lost circulation in Barail formation (2,580-2,650m)
  - Average mud loss: 45 bbl
  - Wells with mud weight >1.45 ppg had lower losses

✅ Recommended Actions:
  1. Reduce ROP to <8 m/hr between 2,580-2,650m
  2. Prepare LCM pills (15 bbl each, 2x ready)
  3. Monitor flow out closely (alert if delta >5%)
  4. Consider increasing mud weight to 1.48 ppg

📊 Predicted Outcome:
  - 70% chance of avoiding lost circulation with these measures
  - If losses occur, estimated 4-6 hours NPT (based on Well MR-002 response)
```

**Implementation**: Triggered when active well approaches high-risk depth intervals identified from offset well incidents.

---

### 5.5 Collaborative Annotation & Lessons Learned

**Feature**: Engineers can add annotations to charts and incidents, creating institutional memory

**How It Works**:
- Click on any chart point → Add annotation (text + optional image/diagram)
- Annotations visible to all engineers (not field operators)
- Tag annotations with categories: "Best Practice", "Avoid This", "Investigate Further"
- Search annotations across all wells

**Use Case**: Engineer notices unusual torque spike at 2,300m → Annotates: "High torque due to tight hole, successful resolution: increase pump rate + reduce RPM"

**Value**: Captures tacit knowledge that doesn't make it into formal reports.

---

## 6. Integration Architecture

### 6.1 Module Integration Endpoints

| **Module** | **Data Provided to Module 7** | **Integration Method** |
|------------|-------------------------------|------------------------|
| **Module 1** (PDF ETL) | Historical well data, documents | REST API: `GET /api/v1/wells/{well_id}`, `GET /api/v1/documents` |
| **Module 2** (Real-Time) | Live telemetry, alerts | WebSocket: `ws://.../live/well/{id}/telemetry`, REST API for historical queries |
| **Module 3** (Geo Viz) | Geospatial data, well coordinates | REST API: `GET /api/v1/wells/geospatial`, PostGIS spatial queries |
| **Module 4** (ML Predictions) | Risk scores, predictions | REST API: `GET /api/v1/predictions/{well_id}/latest`, `/model/status` |
| **Module 5** (Doc Extract) | OCR-extracted JSON, searchable text | REST API: `GET /api/v1/documents/{id}/extracted`, `/search` |
| **Module 6** (Alerts) | Alert stream, alert history | WebSocket + REST API: `ws://.../alerts`, `GET /api/v1/alerts` |

### 6.2 API Gateway Pattern

**Centralized API Gateway** (Module 7 backend) handles:
- **Authentication**: Verify JWT token on every request
- **Authorization**: Check user role and assigned fields
- **Request Routing**: Forward requests to appropriate module backends
- **Response Aggregation**: Combine data from multiple modules (e.g., well summary = Module 1 metadata + Module 2 latest telemetry + Module 4 predictions)
- **Caching**: Cache expensive queries in Redis (e.g., offset well similarity matrix)
- **Rate Limiting**: Prevent abuse

**Architecture**:
```
Frontend (Browser)
    ↓ HTTP/WebSocket
API Gateway (Module 7 Backend - FastAPI)
    ↓ (Internal Network)
Module 1 Backend | Module 2 Backend | Module 4 Backend | ...
    ↓
PostgreSQL Database (Shared)
```

---

## 7. Development Roadmap

### Phase 1: Foundation (Weeks 1-2)
- ✅ Define user roles and permissions matrix
- ✅ Design dashboard wireframes (all views)
- ⏳ Set up Next.js project structure
- ⏳ Implement authentication (JWT + bcrypt)
- ⏳ Build user management API (CRUD users, roles)
- ⏳ Set up PostgreSQL users and roles tables

### Phase 2: Core Dashboard (Weeks 3-4)
- ⏳ Home dashboard layout (responsive grid)
- ⏳ Active wells status card
- ⏳ Live alert summary card
- ⏳ Today's performance snapshot
- ⏳ WebSocket integration with Module 2 (live telemetry)
- ⏳ Real-time chart components (Recharts)

### Phase 3: Offset Wells Integration (Weeks 5-6)
- ⏳ Leaflet.js map with well markers
- ⏳ Well detail view (tabs: overview, real-time, historical, geological, incidents, documents, predictions)
- ⏳ Formation correlation chart
- ⏳ Incident timeline visualization
- ⏳ Integration with Module 3 geospatial API

### Phase 4: Analytics & Predictions (Weeks 7-8)
- ⏳ Multi-well comparison tool
- ⏳ KPI benchmarking dashboard
- ⏳ Risk heatmap visualization
- ⏳ Integration with Module 4 ML predictions
- ⏳ Prediction detail view (model outputs, confidence intervals)

### Phase 5: Alerts & Documents (Weeks 9-10)
- ⏳ Alert feed (WebSocket-powered)
- ⏳ Alert detail modal
- ⏳ Alert configuration panel (admin)
- ⏳ Document repository interface
- ⏳ PDF viewer integration
- ⏳ Full-text search (Elasticsearch or PostgreSQL full-text search)

### Phase 6: Reports & Advanced Features (Weeks 11-12)
- ⏳ Pre-built report templates
- ⏳ Custom report builder
- ⏳ Export functionality (PDF, Excel, PowerPoint)
- ⏳ Auto-generated drilling playbook
- ⏳ Collaborative annotations
- ⏳ Offset well "What If" simulator

### Phase 7: Testing & Deployment (Weeks 13-14)
- ⏳ Unit tests (Jest + React Testing Library)
- ⏳ Integration tests (Playwright for E2E)
- ⏳ Performance testing (load testing WebSocket connections)
- ⏳ Security audit (penetration testing)
- ⏳ Docker containerization
- ⏳ Deployment to production environment
- ⏳ User training and documentation

---

## 8. Success Metrics

### 8.1 User Adoption Metrics
- **Target**: 80% of drilling engineers use NWIS dashboard daily within 3 months
- **Measure**: User login frequency, session duration

### 8.2 Operational Impact Metrics
- **Target**: 15% reduction in NPT incidents due to proactive alerting
- **Measure**: Compare NPT % before and after NWIS deployment (6-month window)

### 8.3 Decision-Making Speed
- **Target**: 50% reduction in time to retrieve offset well information
- **Baseline**: Currently ~30 minutes to manually search DDR/WCR files
- **Target**: <5 minutes with NWIS search and map interface

### 8.4 Alert Effectiveness
- **Target**: 70% of critical alerts result in proactive action (avoiding incident)
- **Measure**: Alert acknowledgment rate + incident correlation analysis

### 8.5 Technical Performance
- **Real-Time Latency**: <500ms from telemetry data ingestion to dashboard display
- **Dashboard Load Time**: <2 seconds for home dashboard, <1 second for subsequent navigation
- **Uptime**: 99.5% availability (excluding scheduled maintenance)

---

## 9. Risk Mitigation

### 9.1 Identified Risks

| **Risk** | **Impact** | **Probability** | **Mitigation Strategy** |
|----------|-----------|-----------------|-------------------------|
| **User Resistance** (prefer manual methods) | High | Medium | Conduct user training, demonstrate time savings, phased rollout with champions |
| **Data Quality Issues** (incorrect OCR extraction) | High | Medium | Implement validation workflows, allow manual corrections, display confidence scores |
| **Performance Degradation** (slow dashboard with large data) | Medium | High | Implement pagination, lazy loading, caching (Redis), optimize database indexes |
| **Security Breach** (unauthorized data access) | Critical | Low | HTTPS only, RBAC enforcement, audit logging, regular penetration testing |
| **WebSocket Connection Drops** | Medium | Medium | Automatic reconnection logic, fallback to REST API polling, notify user of connection status |
| **Role Confusion** (users can't find features) | Medium | Medium | Clear UI labeling, role-specific onboarding tours, help documentation |

---

## 10. Documentation & Training Plan

### 10.1 User Documentation
1. **Quick Start Guide** (1-page PDF per role)
   - Role-specific: "Drilling Engineer Quick Start", "Driller Quick Start"
   - Key features and common workflows
   - Screenshots and step-by-step instructions

2. **Comprehensive User Manual** (50+ pages)
   - All dashboard features explained
   - Glossary of terms (WOB, ROP, NPT, etc.)
   - Troubleshooting section
   - FAQ

3. **Video Tutorials** (5-10 minute videos)
   - "How to use the real-time dashboard"
   - "Finding offset well incidents"
   - "Interpreting ML predictions"
   - "Exporting custom reports"

### 10.2 Training Sessions
- **Initial Training**: 2-hour in-person session per field location
- **Role-Specific Training**: 1-hour focused sessions for engineers, drillers, geologists
- **Train-the-Trainer**: Certify 2-3 "NWIS Champions" per field to support other users
- **Ongoing Support**: Weekly office hours (1 hour) for Q&A during first 2 months

### 10.3 Developer Documentation
- **API Documentation**: Auto-generated Swagger UI + markdown API reference
- **Database Schema**: ERD diagrams, table descriptions, sample queries
- **Deployment Guide**: Step-by-step setup instructions, Docker commands
- **Architecture Documentation**: System design diagrams, technology stack rationale

---

## 11. Future Enhancements (Post-MVP)

### Version 2.0 Features
1. **Mobile App** (iOS/Android)
   - Simplified dashboard for field personnel
   - Push notifications for critical alerts
   - Offline mode with data sync

2. **Voice Commands**
   - "Show me stuck pipe incidents in Well DG-003"
   - Hands-free operation for rig floor

3. **Augmented Reality (AR)**
   - AR overlay on rig floor showing current depth, alerts
   - Point phone at equipment → See live sensor data

4. **Advanced ML Models**
   - Natural language queries: "Which wells had high torque in Barail formation?"
   - Anomaly detection (unsupervised learning for novel drilling behaviors)

5. **Integration with External Systems**
   - ERP integration for real-time cost tracking
   - Rig equipment sensors (IoT integration)
   - Third-party MWD/LWD service data

6. **Collaborative Drilling Planning**
   - Multi-user well planning tool
   - Comment threads on drilling plans
   - Version control for drilling programs

---

## 12. Conclusion

Module 7 transforms NWIS from a collection of independent modules into a unified, intelligent drilling operations platform. By providing role-based access, real-time monitoring, offset well intelligence, and predictive analytics through an intuitive dashboard, Module 7 empowers Oil India Limited's drilling teams to make faster, data-driven decisions that reduce NPT, optimize performance, and enhance safety.

**Key Differentiators**:
- ✅ **Context-Aware**: Dashboard adapts to user role, well status, and depth context
- ✅ **Actionable Intelligence**: Not just data visualization, but AI-powered recommendations
- ✅ **Institutional Memory**: Captures and preserves drilling knowledge through annotations and lessons learned
- ✅ **Proactive Alerting**: ML-powered predictions enable preventive actions, not just reactive responses
- ✅ **User-Centric Design**: Each role sees exactly what they need, reducing cognitive load

**Success Depends On**:
1. High-quality data from Modules 1-6
2. User adoption through training and change management
3. Continuous improvement based on user feedback
4. Scalable infrastructure to handle growing data volumes

---

## Appendix A: Sample Dashboard Screenshots (Wireframes)

### A.1 Home Dashboard (Drilling Engineer View)
```
┌───────────────────────────────────────────────────────────────┐
│  NWIS Dashboard  |  Well: DG-003 (Digboi)  |  User: J. Sharma │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐ │
│  │ ACTIVE     │  │ ALERTS     │  │ TODAY'S    │  │OFFSET  │ │
│  │ WELLS: 3   │  │ 🔴 2       │  │ FOOTAGE    │  │INTEL   │ │
│  │ Drilling   │  │ 🟡 5       │  │ 45.2m      │  │12 Wells│ │
│  │ 2,345m/    │  │ 🟢 3       │  │ ROP:10m/hr │  │3 Risks │ │
│  │ 3,200m     │  │            │  │ NPT: 0hr   │  │        │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ LIVE DRILLING DASHBOARD (Last 2 Hours)                  │ │
│  │                                                          │ │
│  │  WOB (klbs)    [~~~~~Chart~~~~~]   🟢 Normal           │ │
│  │  ROP (m/hr)    [~~~~~Chart~~~~~]   🟡 Below Target     │ │
│  │  Torque (kNm)  [~~~~~Chart~~~~~]   🟢 Normal           │ │
│  │  SPP (kPa)     [~~~~~Chart~~~~~]   🟢 Normal           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────┐  ┌──────────────────────────────────┐   │
│  │ NEARBY WELLS   │  │ FORMATION CORRELATION           │   │
│  │ [🗺️ Map]       │  │                                  │   │
│  │ DG-003 (You)   │  │ 2,345m ← YOU ARE HERE           │   │
│  │ NH-001 (5km N) │  │ ├─ Barail Fm                    │   │
│  │ MR-002 (12km)  │  │ ├─ Tipam Fm (predicted 2,480m)  │   │
│  │                │  │ MR-002 had stuck pipe @ 2,360m ⚠️│   │
│  └────────────────┘  └──────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### A.2 Alert Detail Modal
```
┌───────────────────────────────────────────────────────────────┐
│  ⚠️ HIGH WOB ALERT - STUCK PIPE RISK                          │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Alert Type: Stuck Pipe Risk                                  │
│  Severity: 🔴 Critical                                        │
│  Triggered: 2024-01-15 14:32:10                              │
│  Well: DG-003 | Depth: 2,345.2m MD                           │
│                                                               │
│  ── CURRENT CONDITIONS ──                                     │
│  WOB: 48.5 klbs (Threshold: 45 klbs)                         │
│  Torque: 28.3 kNm (Elevated)                                 │
│  ROP: 6.2 m/hr (Declining trend)                             │
│                                                               │
│  ── OFFSET WELL CONTEXT ──                                    │
│  Well MR-002 had stuck pipe at 2,360m with similar WOB       │
│  → Result: 6 hours NPT, fishing operations required          │
│                                                               │
│  ── ML PREDICTION ──                                          │
│  Probability of stuck pipe in next 2 hours: 68%              │
│  Confidence: High (±8%)                                       │
│                                                               │
│  ── RECOMMENDED ACTIONS ──                                    │
│  ✅ Reduce WOB to 40 klbs                                     │
│  ✅ Increase pump rate to 800 lpm                             │
│  ✅ Monitor torque closely (alert if >30 kNm)                 │
│                                                               │
│  [ Acknowledge ]  [ Escalate to Supervisor ]  [ View Chart ] │
└───────────────────────────────────────────────────────────────┘
```

---

## Appendix B: API Endpoint Summary

### Authentication
- `POST /api/v1/auth/login` - User login (returns JWT)
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Get current user info

### Wells
- `GET /api/v1/wells` - List all accessible wells (filtered by user role/fields)
- `GET /api/v1/wells/{well_id}` - Get well details
- `GET /api/v1/wells/{well_id}/summary` - Get well summary (aggregated from multiple modules)

### Real-Time Telemetry
- `WS /api/v1/live/well/{well_id}/telemetry` - WebSocket for live telemetry
- `GET /api/v1/wells/{well_id}/telemetry/latest` - Get last N telemetry rows
- `GET /api/v1/wells/{well_id}/telemetry/range` - Get telemetry for date range

### Alerts
- `WS /api/v1/live/alerts` - WebSocket for real-time alerts (all wells)
- `GET /api/v1/alerts` - Get alerts (with filters)
- `GET /api/v1/alerts/{alert_id}` - Get alert details
- `POST /api/v1/alerts/{alert_id}/acknowledge` - Acknowledge alert
- `POST /api/v1/alerts/{alert_id}/resolve` - Resolve alert

### Predictions
- `GET /api/v1/predictions/{well_id}/latest` - Get latest ML predictions
- `GET /api/v1/predictions/{well_id}/history` - Get prediction history

### Documents
- `GET /api/v1/documents` - List documents (with filters)
- `GET /api/v1/documents/{doc_id}` - Get document metadata
- `GET /api/v1/documents/{doc_id}/download` - Download PDF
- `GET /api/v1/documents/{doc_id}/extracted` - Get extracted JSON
- `GET /api/v1/documents/search?q={query}` - Full-text search

### Reports
- `POST /api/v1/reports/generate` - Generate custom report (async job)
- `GET /api/v1/reports/{job_id}/status` - Check report generation status
- `GET /api/v1/reports/{job_id}/download` - Download generated report

### User Management (Admin only)
- `GET /api/v1/users` - List all users
- `POST /api/v1/users` - Create new user
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user
- `GET /api/v1/roles` - List all roles

---

**Document Version**: 1.0  
**Last Updated**: September 28, 2026  
**Author**: NWIS Development Team  
**Status**: PLANNING PHASE - READY FOR IMPLEMENTATION
