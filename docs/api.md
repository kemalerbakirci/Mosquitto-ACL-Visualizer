# API Reference

This document describes the public programmatic surfaces of the Mosquitto ACL Visualizer project.

## REST Endpoints (Flask Web App)

Base URL (default): `http://localhost:5000`

### `POST /upload`
Upload and parse a Mosquitto ACL file.

Request (multipart/form-data):
- file: `.acl` file

Response 200:
```json
{
	"message": "File uploaded and parsed successfully",
	"session_id": "sample.acl",
	"summary": {
		"total_clients": 3,
		"total_rules": 12,
		"clients": ["device1", "device2", "admin"]
	}
}
```

Errors: 400 (validation), 500 (server)

### `GET /visualize?session_id=...`
Return full visualization dataset (clients, topics, relationships, overlaps, hierarchy, matrix, security_analysis, statistics).

Sample Response (abbreviated):
```json
{
	"clients": [{"name": "device1", "total_rules": 2, "read_permissions": 1, "write_permissions": 1, "topics": []}],
	"topics": [{"topic": "sensors/temp", "client_count": 2}],
	"relationships": {"nodes": [...], "edges": [...]},
	"security_analysis": {"issues": [], "warnings": [], "security_score": 100},
	"statistics": {"total_clients": 3, "total_rules": 12}
}
```

### `GET /api/clients?session_id=...`
Client summary collection.

### `GET /api/topics?session_id=...`
Topic summary collection.

### `GET /api/security-analysis?session_id=...`
Security analysis only (subset of `/visualize`).

### `POST /generate`
Generate ACL file from JSON payload.

Request JSON:
```json
{
	"client_rules": {
		"device1": [
			{"client": "device1", "access": "read", "topic": "sensors/room1/temp"},
			{"client": "device1", "access": "write", "topic": "actuators/room1/hvac"}
		]
	},
	"options": {"sort_clients": true, "include_comments": true}
}
```

Response: ACL file download.

### `GET /api/export/<format>?session_id=...`
Export parsed data.

Formats:
- `json` – raw structured rules
- `acl` – regenerated ACL file

## Python Package Modules

### `parser.py`
Classes & Functions:
- `ACLRule(dataclass)` – fields: client, access, topic
- `ACLParser.parse_file(path) -> Dict[str,List[ACLRule]]`
- `ACLParser.parse_string(text)` / `parse_stream(stream)`
- `parse_acl_file(path)` convenience wrapper
- `validate_acl_rules(client_rules) -> List[str]`

Exceptions:
- `ACLParseError`

### `generator.py`
Classes & Functions:
- `ACLGenerator(sort_clients=True, include_comments=True)`
	- `generate_file(client_rules, output_path, access_filter=None)`
	- `generate_string(client_rules, access_filter=None) -> str`
	- internal helpers `_format_header()`, `_format_client_section()`
- `ACLGenerateError`
- `merge_acl_rules(*dicts) -> Dict[str,List[ACLRule]]`
- `filter_rules_by_topic_pattern(client_rules, pattern)`
- `validate_generation_input(client_rules) -> List[str]`

### `visualizer.py`
Classes & Functions:
- `ACLVisualizer(client_rules)` – high‑level analytics:
	- `generate_visualization_data()`
	- `get_client_summary()`
	- `get_topic_summary()`
	- `get_client_topic_relationships()`
	- `get_topic_overlaps()`
	- `get_topic_hierarchy()`
	- `get_client_topic_matrix()`
	- `get_security_analysis()`
	- `get_statistics()`
- `create_visualization_data(client_rules)` convenience wrapper
- `export_visualization_json(client_rules, output_path)`

### `webapp.py`
Primary Flask application factory: `create_app(config=None)` returning a configured instance. Script entrypoint `main()` sets up and runs the server.

## Data Shapes

### Relationship Graph
```json
{
	"nodes": [
		{"id": "client_device1", "label": "device1", "type": "client", "size": 3},
		{"id": "topic_sensors/temp", "label": "sensors/temp", "type": "topic", "is_wildcard": false}
	],
	"edges": [
		{"source": "client_device1", "target": "topic_sensors/temp", "access": "read", "label": "read"}
	]
}
```

### Security Analysis
```json
{
	"issues": [{"level": "high", "client": "admin", "issue": "Write access to all topics (#)"}],
	"warnings": [{"level": "medium", "topic": "sensors/+", "issue": "Multiple writers to same topic"}],
	"recommendations": ["Review and restrict overly permissive wildcard permissions"],
	"security_score": 80
}
```

## Error Handling

Standard JSON error response:
```json
{"error": "Description of the issue"}
```
Status codes: 400 (client), 404, 413 (payload too large), 500.

## Versioning

The API is currently pre‑1.0 and subject to change. Pin a git commit or release tag for production use.

## Rate Limits & Auth

No authentication or rate limiting is implemented yet. For production deploy behind reverse proxy and add auth (e.g., API key or OAuth) plus request throttling.

## CLI Usage

Parser:
```
python -m src.acl_visualizer.parser path/to/file.acl
```

Visualizer (JSON export):
```
python -m src.acl_visualizer.visualizer path/to/file.acl output.json
```

Web App:
```
python -m src.acl_visualizer.webapp
```

---

For questions or proposed changes to this API open an issue with the label `api`.
