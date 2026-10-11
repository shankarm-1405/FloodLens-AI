# FloodLens AI: 3-Minute Hackathon Demonstration Script
## Track B: Mapping Flood Damage from Space (Multimodal AI Hackathon 2026)

**Presenter Target Duration:** Exactly 3 minutes (180 seconds)  
**Live URL:** `http://127.0.0.1:5173` (or production build)  
**Case Study Focus:** Trishuli River Corridor, Nuwakot District, Nepal (Monsoon Surge Event, August 2026)  
**Presenter Stance:** Truthful, methodologically rigorous, and scientifically grounded. Emphasize that current benchmark metrics use a calibrated synthetic fixture (`SYNTHETIC_TEST_FIXTURE`).

---

### Segment 1: Problem & Motivation (0:00 – 0:25 | 25s)
- **Screen:** `http://127.0.0.1:5173/#overview` (Overview Dashboard)
- **Visual Action:** Scroll smoothly across the Hero title: *"Operational Rapid Flood Damage & Settlement Isolation Mapping"*, highlighting the Trishuli Corridor benchmark callout.
- **Presenter Speaking Script:**
  > "During monsoon surges in high-relief mountain valleys like Nepal's Trishuli corridor, torrential flash floods wash out roads and isolate entire villages. Optical satellites like Sentinel-2 are blinded by persistent cloud cover, while emergency managers struggle with three critical problems: radar mountain shadows causing false positives, crowdsourced baseline data getting corrupted after the disaster, and LLMs hallucinating casualty counts in crisis reports.  
  > FloodLens AI is our open-source multimodal platform that solves this by pairing all-weather Sentinel-1 SAR change detection with pinned pre-event OpenStreetMap graphs and grounded bilingual reporting."

---

### Segment 2: System Architecture & Multimodal Data Flow (0:25 – 0:50 | 25s)
- **Screen:** `http://127.0.0.1:5173/#overview` (Module cards & Scientific Principles)
- **Visual Action:** Point to the 4 workflow cards: *01 SAR Flood Extent $\rightarrow$ 02 Infrastructure Exposure $\rightarrow$ 03 Cut-Off Settlements $\rightarrow$ 04 Bilingual Situation Report*.
- **Presenter Speaking Script:**
  > "Our architecture unites three multimodal data streams: first, radar amplitude log-ratio change detection; second, pre-disaster OpenStreetMap infrastructure strictly anchored to July 27, 2026 to prevent target leakage; and third, projected UTM Zone 45N road graph routing.  
  > Every calculation is deterministic and traceable. If an input is unavailable, we explicitly flag it as `UNAVAILABLE` rather than fabricating zero counts or making assumptions."

---

### Segment 3: SAR Flood Inundation & Provenance Warning (0:50 – 1:20 | 30s)
- **Screen:** `http://127.0.0.1:5173/#flood-analysis` (Flood Analysis Workspace)
- **Visual Action:** 
  1. Show the active benchmark ID `e2e-trishuli-aug2026`.
  2. Point to the amber **`SYNTHETIC_TEST_FIXTURE`** badge.
  3. Toggle the Leaflet layer: turn on the Candidate Flood mask (cyan) and Copernicus DEM Slope Shadow Mask ($>15^\circ$, orange).
  4. Show the 4 visual inspection tiles (Pre-event SAR, Post-event SAR, Log-ratio Difference, and Extent Mask).
- **Presenter Speaking Script:**
  > "Here on the Flood Analysis page, you can see our SAR change detection workspace. Notice our amber provenance badge: because real multi-gigabyte Sentinel-1 SAFE archives have not been processed locally for this demo, our system prominently labels this as `SYNTHETIC_TEST_FIXTURE`.  
  > In this benchmark, the engine detected 4.245 square kilometres of candidate surface flood extent while our Copernicus DEM slope filter masked out 400 square kilometres of mountain slopes above 15 degrees, eliminating false radar cast shadows."

---

### Segment 4: Historical Infrastructure Exposure (1:20 – 1:45 | 25s)
- **Screen:** `http://127.0.0.1:5173/#infrastructure` (Infrastructure Exposure)
- **Visual Action:** 
  1. Show the live metrics: **3 exposed buildings ($30,298\text{ m}^2$)**, **$1.165\text{ km}$ of road**, and **1 bridge**.
  2. Scroll down to Critical Facilities table: highlight `Battar Community Health Post` marked with a red *Directly Intersecting* badge, while `Trishuli Hospital` is green at a safe $2,357\text{ m}$ setback.
- **Presenter Speaking Script:**
  > "Moving to Infrastructure Exposure, we intersect the candidate flood polygon with our historical OpenStreetMap baseline. The engine identifies 3 buildings, 1.165 kilometres of inundated roadway along Highway H02, and the Battar suspension footbridge.  
  > Crucially, our facility proximity classifier shows that the Battar Community Health Post directly intersects the hazard footprint, whereas Trishuli Hospital remains safe at an elevated 2.3-kilometre setback."

---

### Segment 5: Settlement Road Disconnection & Cut-Off Routing (1:45 – 2:10 | 25s)
- **Screen:** `http://127.0.0.1:5173/#connectivity` (Connectivity Page)
- **Visual Action:** 
  1. Point to the status summary cards: **2 Newly Cut-Off Mountain Communities**, **1 Baseline Disconnected**.
  2. Show the map with red severed road edges and severed routes to Bidur.
  3. Expand the settlement details table: highlight `Devighat` and `Battar` having severed access, while `Tupche` is recognized as already disconnected prior to the flood.
- **Presenter Speaking Script:**
  > "Physical exposure is only half the story. On our Connectivity page, we convert the road network into a topological multigraph in UTM Zone 45N and simulate flood-induced road closures.  
  > Using Dijkstra shortest-path routing to district headquarters in Bidur, we discover that two mountain settlements—Devighat and Battar—have become completely cut off. The model also distinguishes that Tupche was already disconnected at baseline, preventing false attribution."

---

### Segment 6: Grounded Bilingual Situation Report Copilot (2:10 – 2:35 | 25s)
- **Screen:** `http://127.0.0.1:5173/#ai-report` (Situation Report)
- **Visual Action:** 
  1. Show the English report preview with executive summary and KPI metrics.
  2. Click the **`नेपाली`** toggle button: watch the entire document render in clean Nepali Devanagari text.
  3. Point out that all numbers ($4.245\text{ km}^2$, 3 buildings, 2 cut-off settlements) and dates remain identical.
- **Presenter Speaking Script:**
  > "In a crisis, field teams need immediate, authoritative briefs in their local language. Our Grounded Situation Report Copilot generates verifiable 8-section assessments in both English and Nepali.  
  > When I switch to Nepali, notice how every single computed metric, date, and settlement name is strictly preserved. Our backend safety verifier actively rejects hallucinated death tolls or unauthorized evacuation decrees, ensuring emergency managers receive verified facts rather than AI fiction."

---

### Segment 7: Document Exports, Testing & Technical Rigor (2:35 – 2:50 | 15s)
- **Screen:** `http://127.0.0.1:5173/#ai-report` (Export Buttons)
- **Visual Action:** 
  1. Click **`Download PDF Report`** to show the generated PDF opening in the browser tab.
  2. Highlight the 96 automated tests passing in backend.
- **Presenter Speaking Script:**
  > "Users can download full publication-quality PDFs or UTF-8 Markdown reports with a single click, along with georeferenced GeoJSON layers for GIS tools. Our backend features 96 automated passing tests covering CRS math, geometry repair, and safety guardrails."

---

### Segment 8: Honest Limitations & Future Validation (2:50 – 3:00 | 10s)
- **Screen:** `http://127.0.0.1:5173/#limitations` (Limitations & Validation Page)
- **Visual Action:** Show the Limitations summary and the three mandatory Copernicus/OSM attribution notices.
- **Presenter Speaking Script:**
  > "To conclude: FloodLens AI is an educational prototype. Real satellite SAFE archives and field ground-truthing are required before operational deployment. Thank you!"

---

### Contingency & Fallback Guide
- **If backend goes offline during demo:** Point out the top-right engine health indicator which displays a graceful *Backend Offline* badge, and demonstrate the offline mock capabilities built into the frontend.
- **If map tiles load slowly:** Reassure the audience that all vector geometries, metric cards, and report generators are pre-computed locally and do not depend on external map tile latency.
