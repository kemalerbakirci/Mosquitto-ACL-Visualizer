# Usage Guide

Practical instructions for running and using the Mosquitto ACL Visualizer.

## 1. Run the Web Application

Using Poetry:
```
poetry install
poetry run python -m src.acl_visualizer.webapp
```

Using pip:
```
pip install -r requirements.txt
python -m src.acl_visualizer.webapp
```

Then open: http://localhost:5000

## 2. Upload an ACL File
Drag & drop or click the upload area and choose a `.acl` file. On success you will see a toast notification and the graph will render.

Accepted line formats:
```
user <username>
topic [read|write|readwrite] <topic/pattern>
```
If access token omitted it defaults to `readwrite`.

## 3. Understand the Graph
- Left (blue nodes): clients / users
- Right (orange nodes): topics
- Edges:
	- Green = read
	- Orange = write
	- Blue = readwrite

Hover nodes or edges → tooltip details. Click a node → side details panel (rules or client list).

## 4. Security Analysis
Internally computed heuristics (displayed via `/api/security-analysis` or inside the full `/visualize` payload):
- High severity: write/readwrite to `#`
- Medium: write/readwrite to wildcard (`+`)
- Medium: multiple writers for same exact topic
Score = 100 − 20*issues − 5*warnings.

## 5. Export Data
Use endpoints manually (or future UI actions):
```
GET /api/export/json?session_id=<id>   # structured rules
GET /api/export/acl?session_id=<id>    # regenerated ACL file
```

## 6. Generate New ACL Programmatically
POST `/generate` with JSON body:
```json
{
	"client_rules": {
		"sensor01": [
			{"client": "sensor01", "access": "write", "topic": "sensors/room1/temp"}
		],
		"dashboard": [
			{"client": "dashboard", "access": "read", "topic": "sensors/+/temp"}
		]
	},
	"options": {"sort_clients": true, "include_comments": true}
}
```
Response is a downloadable `.acl` file.

## 7. CLI Utilities
Parse a file:
```
python -m src.acl_visualizer.parser examples/sample.acl
```

Generate visualization JSON:
```
python -m src.acl_visualizer.visualizer examples/sample.acl output.json
```

## 8. Troubleshooting Quick Table
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Blank graph | Parse failed / no rules | Check server logs / ensure file has topic lines |
| Tooltip missing | Old cache / duplicate code | Hard refresh (Ctrl/Cmd+Shift+R) |
| 500 error on upload | Encoding issue | Ensure UTF-8 file, remove BOM |
| Wrong counts | Mixed users in file | Verify each topic line follows a user line |

## 9. Large ACL Tips
- Collapse broad wildcards into specific prefixes before upload for clarity
- Split extremely large files to reduce initial render time
- Consider future pagination (roadmap) for >5k rules

## 10. Minimal Example
```
user sensor1
topic write sensors/room1/temp

user dashboard
topic read sensors/+/temp
```

Upload → you will see two clients, two topics (one pattern), with one write and one read edge.

---
For deeper conceptual material see `docs/comprehensive-guide.md`.
