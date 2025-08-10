# Architecture

High‑level view of the Mosquitto ACL Visualizer system.

## Overview Diagram

```
 ┌────────────┐    HTTP/JSON     ┌───────────────┐   In‑Memory   ┌──────────────┐
 │  Browser   │  ─────────────▶  │ Flask Backend │ ───────────▶ │ Data Store   │
 │ (Frontend) │  ◀─────────────  │  (webapp.py)  │  Visualization│ (dict session)│
 └────┬───────┘                   └──────┬────────┘   Objects    └─────┬────────┘
			│  D3.js SVG Rendering             │                                 │
			│                                  │ Reads/Writes                    │
			▼                                  ▼                                 ▼
	User .acl file  ───────────▶  Parser (parser.py)  ──▶  Rules Model  ──▶  Visualizer (visualizer.py)
																					│                                  │
																					▼                                  ▼
																		Generator (generator.py)      Security / Stats / Graph JSON
```

## Components

### Frontend (Static Assets)
- `index.html` minimal UI (upload area + graph container + legend)
- `app.js` handles upload, fetches visualization JSON, renders bipartite graph with D3
- `styles.css` design tokens, layout, legend + tooltip styling

### Backend (Flask)
- `webapp.py` routes:
	- `/upload` → saves temp file, parses, stores rules by session id
	- `/visualize` → runs analytics + returns combined JSON
	- `/api/*` endpoints for partial data (clients, topics, security)
	- `/generate` & `/api/export/*` for ACL regeneration/export

### Core Library Modules
1. `parser.py` → transforms raw ACL text into `Dict[str, List[ACLRule]]`
2. `visualizer.py` → derives higher‑order datasets (graph nodes/edges, overlaps, hierarchy, matrix, security analysis, statistics)
3. `generator.py` → produces canonical ACL text from structured rules with optional filtering/sorting

## Data Model

```
ACLRule:
	client: str
	access: {'read','write','readwrite'}
	topic:  str

ClientRules: Dict[client, List[ACLRule]]

VisualizationData (aggregate):
	clients[]            – per‑client summaries
	topics[]             – per‑topic summaries
	relationships {nodes[], edges[]} – bipartite graph
	overlaps[]           – topics shared by >1 client
	hierarchy {…}        – topic tree (exact topics only)
	matrix {clients[], topics[], matrix[][]}
	security_analysis {issues[], warnings[], recommendations[], security_score}
	statistics {totals, distributions, most_common_topics}
```

## Processing Pipeline
1. Upload `.acl`
2. Parse → `ClientRules`
3. Analyze + derive structures → `VisualizationData`
4. Serialize → JSON → Frontend
5. Render D3 bipartite graph (clients left, topics right, colored edges)

## Security Analysis Heuristics
- High issue: write/readwrite to `#`
- Warning: write/readwrite to pattern containing `+`
- Warning: multiple writers to same exact topic
- Score = 100 − 20*issues − 5*warnings (bounded ≥0)

## Error Handling Strategy
- Parsing: raise `ACLParseError` (mapped to 400 JSON)
- Generation: `ACLGenerateError`
- File size: 413; generic fallback 500

## Extensibility Points
- Add new analysis: extend `ACLVisualizer` with method and include in `generate_visualization_data`
- Persist sessions: replace in‑memory dict with Redis or database keyed by session token
- Auth: wrap endpoints with Flask middleware / JWT
- Large ACL scaling: stream parse, chunk graph (paging) or server‑side sampling

## Performance Considerations
- Current parser: single pass O(N lines)
- Graph building: O(R) where R = total rules
- Matrix: O(C*T) (can be heavy if both large; consider sparse representation)
- Frontend rendering: D3 simple line/circle elements (no force sim)

## Known Limitations
- No authentication or persistence across restarts
- Tooltip code duplication remnants (frontend cleanup pending)
- No pagination for very large ACLs (>5k rules may impact browser)

## Future Improvements (Roadmap)
- WebSocket updates for live ACL changes
- Role abstraction layer (groups of clients)
- Export PDF security report
- Configurable scoring weights
- Performance profiling & lazy topic node rendering

---
This architecture doc reflects the current implemented state (v0.1.0) and planned near‑term enhancements.
