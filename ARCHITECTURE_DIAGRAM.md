# 🏗️ Poison Guard Architecture Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         POISON GUARD SYSTEM ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐         ┌──────────────────────────────────┐
│    FRONTEND (React + Vite)      │         │    BACKEND (FastAPI + Celery)    │
│     :3000 Development Server    │◄──────► │    :8000 API Server              │
├─────────────────────────────────┤         ├──────────────────────────────────┤
│                                 │         │                                  │
│  ┌───────────────────────────┐  │         │  ┌──────────────────────────┐   │
│  │   Sidebar Navigation      │  │         │  │   FastAPI Routes         │   │
│  │  ├─ Home (/)              │  │         │  │  ├─ POST /api/detect     │   │
│  │  ├─ Dashboard (/dash)     │  │         │  │  ├─ POST /api/detect/rlod│   │
│  │  ├─ Chatbot (/chat)       │  │         │  │  ├─ POST /api/detect/combined
│  │  └─ Settings (/settings)  │  │         │  │  ├─ GET /api/jobs/{id} │   │
│  └───────────────────────────┘  │         │  ├─ GET /health           │   │
│                                 │         │  ├─ GET /ready            │   │
│  ┌───────────────────────────┐  │         │  └─ GET /metrics          │   │
│  │     Pages (4 routes)      │  │         │  └──────────────────────────┘   │
│  │  ├─ Home Page             │  │         │                                 │
│  │  ├─ Dashboard             │  │         │  ┌──────────────────────────┐   │
│  │  │   • 6 KPI Metrics      │  │         │  │  Detection Engines       │   │
│  │  │   • 4 Analytics Charts │  │         │  │  ├─ JIE Detector         │   │
│  │  │   • Detection Table    │  │         │  │  │   • TracIn algorithm  │   │
│  │  ├─ Chatbot Page         │  │         │  │  │   • Gradient-based     │   │
│  │  │   • Message History   │  │         │  │  ├─ RLOD Detector         │   │
│  │  │   • Smart Responses   │  │         │  │  │   • Embedding-based  │   │
│  │  └─ Settings Page        │  │         │  │  │   • kNN + Spectral   │   │
│  │      • API Config        │  │         │  │  └─ Combined (60/40)   │   │
│  │      • Detection Weights │  │         │  └──────────────────────────┘   │
│  │      • UI Preferences    │  │         │                                  │
│  └───────────────────────────┘  │         │  ┌──────────────────────────┐   │
│                                 │         │  │  Celery Task Queue       │   │
│  ┌───────────────────────────┐  │         │  │  ├─ run_jie_detection   │   │
│  │   Components (4)          │  │         │  │  ├─ run_rlod_detection │   │
│  │  ├─ Sidebar              │  │         │  │  └─ run_combined_detection
│  │  ├─ MetricCard           │  │         │  └──────────────────────────┘   │
│  │  ├─ Charts (4 types)     │  │         │                                  │
│  │  └─ ChatInterface        │  │         │  ┌──────────────────────────┐   │
│  └───────────────────────────┘  │         │  │  Model Management        │   │
│                                 │         │  │  ├─ GPT-2-Medium        │   │
│  ┌───────────────────────────┐  │         │  │  ├─ Lazy Loading        │   │
│  │   API Client (Axios)      │  │         │  │  ├─ GPU Acceleration   │   │
│  │  ├─ detectAPI (6 methods)│  │         │  │  └─ CPU Fallback       │   │
│  │  ├─ chatAPI (3 methods) │  │         │  └──────────────────────────┘   │
│  │  └─ Interceptors         │  │         │                                  │
│  └───────────────────────────┘  │         │  ┌──────────────────────────┐   │
│                                 │         │  │  Data Storage            │   │
│  ┌───────────────────────────┐  │         │  ├─ Redis Cache           │   │
│  │   Styling                 │  │         │  ├─ Embeddings Cache      │   │
│  │  ├─ Tailwind CSS         │  │         │  └─ Model Checkpoints    │   │
│  │  ├─ Custom Component CSS │  │         │  └──────────────────────────┘   │
│  │  └─ Responsive Design    │  │         │                                  │
│  └───────────────────────────┘  │         └──────────────────────────────────┘
│                                 │
└─────────────────────────────────┘
         ▲
         │ HTTP/CORS
         │ (Port 3000↔8000)
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES & DATA SOURCES                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Training    │  │  Validation  │  │  Test        │  │  Model       │  │
│  │  Samples     │  │  Samples     │  │  Samples     │  │  Checkpoints │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DETECTION DATA FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

USER INTERACTION
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  1. USER SUBMITS SAMPLES                                          │
│     ├─ Via Dashboard (File Upload)                              │
│     ├─ Via API (Direct)                                         │
│     └─ Via Chatbot (Query)                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
FRONTEND PROCESSING
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  2. CLIENT-SIDE PREPARATION                                      │
│     ├─ Validate inputs                                          │
│     ├─ Format data                                              │
│     └─ Show loading indicator                                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
API REQUEST
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  3. SEND TO BACKEND                                              │
│     ├─ POST /api/detect (JIE)                                   │
│     ├─ POST /api/detect/rlod (RLOD)                             │
│     ├─ POST /api/detect/combined (Both)                         │
│     └─ Return job_id (async mode)                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
BACKEND PROCESSING
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  4. LOAD MODELS                                                  │
│     ├─ Load GPT-2-Medium (first time only)                      │
│     ├─ Move to GPU if available                                 │
│     └─ Initialize JIE & RLOD detectors                          │
│                                                                   │
│  5. RUN DETECTION (Parallel)                                     │
│     ├─ JIE Detection                                            │
│     │   ├─ Extract last-layer gradients                         │
│     │   ├─ Calculate influence scores                           │
│     │   └─ Return scores (0-1 range)                            │
│     │                                                            │
│     └─ RLOD Detection                                           │
│         ├─ Extract embeddings                                   │
│         ├─ Apply kNN outlier detection                          │
│         ├─ Apply spectral analysis                              │
│         ├─ Apply clustering analysis                            │
│         └─ Combine scores (weighted)                            │
│                                                                   │
│  6. COMBINE RESULTS (If combined mode)                          │
│     ├─ JIE Score × 0.6 (60%)                                   │
│     ├─ RLOD Score × 0.4 (40%)                                  │
│     └─ Return combined score                                    │
│                                                                   │
│  7. CACHE & STORE                                               │
│     ├─ Cache embeddings                                         │
│     ├─ Store results                                            │
│     └─ Generate job_id for async tracking                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
RESULT RETURN
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  8. RESPOND TO FRONTEND                                          │
│     ├─ Sync: Return results immediately                         │
│     └─ Async: Return job_id for polling                         │
│                                                                   │
│  9. JOB STATUS POLLING (Async)                                  │
│     ├─ GET /api/jobs/{job_id}                                   │
│     ├─ Poll every 2-5 seconds                                   │
│     └─ Return when complete                                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
FRONTEND VISUALIZATION
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  10. DISPLAY RESULTS                                             │
│      ├─ Update KPI metrics                                      │
│      ├─ Plot charts (Line, Bar, Pie, Radar)                     │
│      ├─ Show detection table                                    │
│      ├─ Color-code status badges                                │
│      └─ Calculate mitigation weights                            │
│                                                                   │
│  11. ENABLE INTERACTIONS                                        │
│      ├─ Refresh button                                          │
│      ├─ Export functionality                                    │
│      ├─ Settings adjustments                                    │
│      └─ Chatbot queries                                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Hierarchy

```
┌─ App (Main Router)
│
├─ Sidebar (Navigation)
│  ├─ Link: Home (/)
│  ├─ Link: Dashboard (/dashboard)
│  ├─ Link: Chatbot (/chatbot)
│  └─ Link: Settings (/settings)
│
├─ Routes
│  │
│  ├─ Route: "/" → Home Page
│  │  └─ Feature Cards
│  │     ├─ JIE Feature
│  │     └─ RLOD Feature
│  │
│  ├─ Route: "/dashboard" → Dashboard Page
│  │  ├─ Header (with Refresh & Export)
│  │  ├─ KPI Metrics Grid (6 cards)
│  │  │  ├─ MetricCard (JIE Score)
│  │  │  ├─ MetricCard (RLOD Score)
│  │  │  ├─ MetricCard (Combined)
│  │  │  ├─ MetricCard (Suspicious Count)
│  │  │  ├─ MetricCard (Clean Count)
│  │  │  └─ MetricCard (Poisoning Rate)
│  │  │
│  │  ├─ Charts Grid (2x2)
│  │  │  ├─ LineChart (Detection Scores)
│  │  │  ├─ LineChart (Combined Trend)
│  │  │  ├─ PieChart (Distribution)
│  │  │  └─ RadarChart (Method Comparison)
│  │  │
│  │  └─ Detection Table
│  │     ├─ Sample ID
│  │     ├─ JIE Score
│  │     ├─ RLOD Score
│  │     ├─ Combined Score
│  │     ├─ Status Badge
│  │     └─ Mitigation Weight
│  │
│  ├─ Route: "/chatbot" → Chatbot Page
│  │  └─ ChatInterface
│  │     ├─ Header
│  │     ├─ Message List
│  │     │  ├─ User Message
│  │     │  ├─ Assistant Message
│  │     │  ├─ Copy Button
│  │     │  └─ Timestamp
│  │     │
│  │     ├─ Typing Indicator (Loading)
│  │     │
│  │     └─ Input Area
│  │        ├─ Text Input
│  │        └─ Send Button
│  │
│  └─ Route: "/settings" → Settings Page
│     ├─ API Configuration Section
│     │  ├─ API URL Input
│     │  └─ API Key Input
│     │
│     ├─ Detection Settings Section
│     │  ├─ JIE Weight Slider
│     │  ├─ RLOD Weight Slider
│     │  ├─ Weight Validation
│     │  ├─ Suspicion Threshold
│     │  └─ Poisoning Threshold
│     │
│     ├─ UI Preferences Section
│     │  ├─ Auto-refresh Interval
│     │  ├─ Auto-refresh Toggle
│     │  ├─ Dark Mode Toggle
│     │  └─ Notifications Toggle
│     │
│     ├─ Action Buttons
│     │  ├─ Save Settings
│     │  └─ Reset to Defaults
│     │
│     └─ Help Section
│        └─ Pro Tips
```

---

## Detection Pipeline

```
INPUT SAMPLES
     │
     ▼
┌─────────────────────┐
│  MODEL LOADING      │
│  (Lazy Loading)     │
│  GPT-2-Medium       │
└─────────────────────┘
     │
     ├────────────────────────┬─────────────────────┐
     │                        │                     │
     ▼                        ▼                     ▼
┌──────────────┐       ┌──────────────┐     ┌──────────────┐
│ JIE DETECTOR │       │RLOD DETECTOR │     │   COMBINED   │
├──────────────┤       ├──────────────┤     │   (60/40)    │
│ Method:      │       │ Method:      │     └──────────────┘
│ TracIn       │       │ Embedding    │            │
│ Algorithm    │       │ -based       │            │
│              │       │              │     ┌──────┴──────┐
│ Steps:       │       │ Steps:       │     │             │
│ 1. Extract   │       │ 1. Extract   │     │ JIE Score   │
│    last-layer│       │    embedding │     │ × 0.6       │
│    params    │       │    from      │     │             │
│ 2. Calculate │       │    hidden    │     ├─────────────┤
│    gradients │       │    layers    │     │             │
│ 3. Compute   │       │ 2. Fit kNN   │     │ RLOD Score  │
│    influence │       │    on clean  │     │ × 0.4       │
│    scores    │       │    samples   │     │             │
│              │       │ 3. Apply     │     ├─────────────┤
│ Output:      │       │    spectral  │     │             │
│ JIE Score    │       │    analysis  │     │ Combined    │
│ (0-1)        │       │ 4. Apply     │     │ Score       │
│              │       │    clustering│     │ (0-1)       │
│              │       │ 5. Combine   │     │             │
│              │       │    weighted  │     └──────────────┘
│              │       │              │
│              │       │ Output:      │
│              │       │ RLOD Score   │
│              │       │ (0-1)        │
└──────────────┘       └──────────────┘
     │                        │
     └────────────────────────┘
           │
           ▼
    ┌─────────────────┐
    │  SCORE MAPPING  │
    │  (Mitigation)   │
    │                 │
    │ 0.0 - 0.33      │
    │ → Clean         │
    │ → Weight: min   │
    │                 │
    │ 0.33 - 0.67     │
    │ → Suspicious    │
    │ → Weight: med   │
    │                 │
    │ 0.67 - 1.0      │
    │ → Poisoned      │
    │ → Weight: max   │
    └─────────────────┘
           │
           ▼
    ┌─────────────────┐
    │   RESULTS       │
    │                 │
    │ ├─ Score        │
    │ ├─ Status       │
    │ ├─ Confidence   │
    │ ├─ Metadata     │
    │ └─ Weight       │
    └─────────────────┘
           │
           ▼
    ┌─────────────────┐
    │  VISUALIZATION  │
    │  (Frontend)     │
    │                 │
    │ ├─ Charts       │
    │ ├─ Table        │
    │ ├─ Badges       │
    │ └─ Metrics      │
    └─────────────────┘
```

---

## File Structure Diagram

```
poison-guard/
│
├── frontend/                          ← React + Vite Application
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js             ← Axios API Client (9 methods)
│   │   │
│   │   ├── components/
│   │   │   ├── Sidebar.jsx           ← Navigation (60 lines)
│   │   │   ├── MetricCard.jsx        ← KPI Cards (35 lines)
│   │   │   ├── Charts.jsx            ← 4 Chart Types (85 lines)
│   │   │   └── ChatInterface.jsx     ← Chat UI (110 lines)
│   │   │
│   │   ├── pages/
│   │   │   ├── Home.jsx              ← Landing Page (130 lines)
│   │   │   ├── Dashboard.jsx         ← Analytics (160 lines)
│   │   │   ├── Chatbot.jsx           ← Chat Wrapper (5 lines)
│   │   │   └── Settings.jsx          ← Config (190 lines)
│   │   │
│   │   ├── App.jsx                   ← Main Component (25 lines)
│   │   ├── App.css                   ← Component Styles (200+ lines)
│   │   ├── index.css                 ← Global Styles (Tailwind)
│   │   └── main.jsx                  ← React Entry (7 lines)
│   │
│   ├── index.html                    ← HTML Template
│   ├── vite.config.js                ← Vite Config
│   ├── tailwind.config.js            ← Tailwind Config
│   ├── package.json                  ← Dependencies
│   ├── .gitignore
│   ├── README.md
│   ├── postinstall.sh / .bat
│   └── node_modules/                 ← Installed packages
│
├── src/                              ← Python Backend
│   ├── api/
│   │   ├── main.py                  ← FastAPI Routes (200 lines)
│   │   ├── auth.py
│   │   ├── tasks.py                 ← Celery Tasks (3 tasks)
│   │   └── rate_limit.py
│   │
│   ├── jie/
│   │   ├── detector.py              ← JIE Detection (300 lines)
│   │   └── tracin.py
│   │
│   └── rlod/
│       ├── detector.py              ← RLOD Core (300 lines)
│       ├── embeddings.py            ← Extraction (250 lines)
│       ├── outlier_detection.py     ← kNN (350 lines)
│       ├── spectral.py              ← Spectral (300 lines)
│       └── cache.py                 ← Caching (200 lines)
│
├── tests/
│   ├── test_rlod.py                ← RLOD Tests (400 lines)
│   ├── test_api.py
│   ├── test_jie.py
│   └── test_smoke.py
│
├── checkpoints/                     ← Model Weights
│   └── gpt2-medium/
│
├── data/
│   └── example_train.json          ← Sample Data
│
├── scripts/
│   ├── download_model.py
│   ├── test_model_access.py
│   └── verify_model_setup.py
│
├── DOCUMENTATION_INDEX.md            ← You are here
├── FRONTEND_SETUP_GUIDE.md
├── UI_IMPLEMENTATION_SUMMARY.md
├── README.md
├── QUICKSTART.md
├── IMPLEMENTATION_SUMMARY.md
├── RLOD_IMPLEMENTATION.md
├── RLOD_QUICKSTART.md
├── DOCKER_GUIDE.md
├── API_DEPLOYMENT.md
├── config.yaml
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
└── .gitignore
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                               │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐         ┌──────────────────────┐
│   Client Browser     │         │   CI/CD Pipeline     │
│   (User Access)      │         │   (GitHub/GitLab)    │
└──────────────┬───────┘         └──────────┬───────────┘
               │                           │
               ▼                           ▼
        ┌─────────────┐          ┌──────────────────┐
        │  Frontend   │          │  Build & Test    │
        │  CDN/S3     │          │  - npm install   │
        │  (Static)   │          │  - npm build     │
        └────────┬────┘          │  - npm test      │
                 │               └────────┬─────────┘
                 │                        │
                 ▼                        ▼
        ┌─────────────────────────────────────────┐
        │         Docker Container                │
        │  (Frontend + Backend + Services)        │
        │                                         │
        │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
        │  │Frontend │  │Backend  │  │ Redis   │ │
        │  │ :3000   │  │ :8000   │  │ :6379   │ │
        │  └─────────┘  └─────────┘  └─────────┘ │
        │  ┌─────────┐  ┌─────────┐              │
        │  │ Celery  │  │ Models  │              │
        │  │ Worker  │  │ Cache   │              │
        │  └─────────┘  └─────────┘              │
        └─────────────────────────────────────────┘
                 │
                 ▼
        ┌─────────────────────────────────────────┐
        │    Kubernetes Cluster (Optional)        │
        │                                         │
        │  Pod 1          Pod 2         Pod 3     │
        │  ┌────────┐    ┌────────┐    ┌────────┐│
        │  │Frontend│    │Backend │    │Celery  ││
        │  │Replica │    │Replica │    │Worker  ││
        │  └────────┘    └────────┘    └────────┘│
        │                                         │
        │  Persistent Volume: Models, Cache       │
        └─────────────────────────────────────────┘
```

---

**End of Architecture Documentation**

Use this diagram to understand how all components fit together!
