# Learning Mosquitto ACLs (Hands‑On Guide)

Goal: become confident writing secure Mosquitto ACL files through short iterative exercises.

## 1. Core Syntax

Lines:
```
user <username>
topic [read|write|readwrite] <topic/pattern>
```
If access omitted → defaults to `readwrite` (be explicit to avoid surprises).

Comments start with `#` and blank lines are ignored.

## 2. Access Semantics
| Access | Publish? | Subscribe? |
|--------|----------|-----------|
| read | ❌ | ✅ |
| write | ✅ | ❌ |
| readwrite | ✅ | ✅ |

## 3. Wildcards & Substitution Tokens
| Symbol | Meaning | Example | Matches |
|--------|---------|---------|---------|
| `+` | single level | sensors/+/temp | sensors/room1/temp |
| `#` | multi (remaining) | sensors/# | sensors/room1/temp |
| `%u` | username | users/%u/config | users/alice/config |
| `%c` | client id | sessions/%c/state | sessions/device123/state |

Never combine text after `#` (invalid). `%u` / `%c` expand at auth time.

## 4. Progressive Exercises

### Exercise A: Single Device
Write ACL so device `temp_01` can only publish its temperature.
```
user temp_01
topic write sensors/temp_01/temperature
```
Add dashboard read access for all device temperatures only:
```
user dashboard
topic read sensors/+/temperature
```

### Exercise B: Per‑User Namespace
Requirement: each user can read & write only under `users/<username>/#`.
```
user alice
topic readwrite users/%u/#

user bob
topic readwrite users/%u/#
```
Test: alice tries publish to `users/bob/data` → should be denied.

### Exercise C: Split Read vs Write
Sensors publish; dashboard reads; controller writes selective actuators.
```
user sensor_room1
topic write sensors/room1/temperature

user dashboard
topic read sensors/+/temperature

user hvac_controller
topic read sensors/+/temperature
topic write actuators/hvac/+
```

Check: `dashboard` must not publish to sensors path.

### Exercise D: Avoid Over‑Broad Wildcards
Bad:
```
user maint_tool
topic readwrite #
```
Improved (scoped):
```
user maint_tool
topic read sensors/+/temperature
topic read sensors/+/humidity
topic write maintenance/requests/+
```

### Exercise E: Multi‑Tenant Separation
Tenants: `t1`, `t2`. Prevent cross‑tenant access.
```
user t1_api
topic readwrite tenants/t1/#

user t2_api
topic readwrite tenants/t2/#
```
Add shared status channel (read‑only for all):
```
topic read status/global
```

## 5. Security Anti‑Patterns
| Pattern | Why Risky | Alternative |
|---------|-----------|------------|
| `topic readwrite #` | Full broker control | Enumerate required prefixes |
| `topic write sensors/#` | Any sensor path writable | Narrow to device id or use `+` once |
| Large use of `+` with write | Broad injection surface | Specific device topics |
| Mixed unrelated topics per user | Hard to audit | Separate service accounts |

## 6. Review Checklist
Before deploying an ACL file ask:
- Any `#` with write or readwrite? Remove / justify.
- Can two different clients write the same exact topic? If yes, acceptable?
- Are wildcard write rules necessary or can they be enumerated?
- Are `%u` or `%c` used to shorten repetitive sections safely?
- Are admin/break‑glass accounts isolated and monitored?

## 7. Hardening Tips
- Combine ACL with TLS client certs (`use_identity_as_username true`).
- Disable anonymous: `allow_anonymous false`.
- Keep topics hierarchical: `org/site/device_type/device_id/data`.
- Separate write vs read identities for automation vs dashboards.
- Log & audit denied attempts; unusual patterns may indicate probing.

## 8. Example: Final Hardened Snippet
```
# Admin (monitoring only, no write to entire broker)
user admin_dashboard
topic read sensors/#
topic read actuators/#
topic read system/status

# Device namespace (templated)
user temp_sensor_01
topic write devices/temp_sensor_01/telemetry
topic read devices/temp_sensor_01/config

user temp_sensor_02
topic write devices/temp_sensor_02/telemetry
topic read devices/temp_sensor_02/config

# Controller limited
user hvac_controller
topic read devices/+/telemetry
topic write actuators/hvac/+
```

## 9. Using This Project to Validate
1. Write / modify ACL.
2. Upload to visualizer.
3. Inspect:
   - Overlaps (unexpected shared topics?)
   - Security score (drops indicate risky patterns).
   - Wildcard usage concentration.
4. Iterate until least‑privilege satisfied.

## 10. Quick Glossary
| Term | Meaning |
|------|---------|
| ACL | Access Control List controlling publish/subscribe rights |
| Wildcard | `+` or `#` topic pattern symbol |
| Principle of Least Privilege | Grant minimum permissions required |
| Namespace | Structured topic prefix grouping related resources |

---
Practice iteratively: small ACL → visualize → refine → repeat. Mastery comes from minimizing surprise edges in the graph.
