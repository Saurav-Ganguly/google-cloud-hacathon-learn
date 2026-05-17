# ADK Ambient Agents

> Background/event-driven agents that react to triggers instead of waiting for human input.

## What They Are

Ambient agents are background processes that execute workflows in response to events — file uploads, Pub/Sub messages, database changes, schedules — without a human typing a message.

**Regular agent**: user types → agent responds  
**Ambient agent**: event fires → agent processes → writes to downstream system

---

## vs Regular Agents

| Aspect | Regular Agent | Ambient Agent |
|--------|---------------|---------------|
| Trigger | Human message | Cloud event / queue / schedule |
| Output | Reply to user | Log, Pub/Sub, downstream service |
| Session | User-initiated | Auto-created per event |
| Concurrency | Manual | Built-in semaphore (default: 10) |
| Retry | Manual | Exponential backoff (3 attempts) |

---

## Use Cases

- Process files as they land in Cloud Storage
- Classify/route support tickets from a queue
- Generate periodic reports on a schedule
- Monitor infrastructure event streams
- Run evals on model outputs automatically

---

## Implementation

An ambient agent is just a regular `LlmAgent` — the difference is *how it's invoked* (via trigger endpoints, not the chat UI).

```python
from google.adk.agents import LlmAgent
import json

def parse_event(raw_event: str) -> dict:
    """Extract structured data from trigger event payload."""
    try:
        return json.loads(raw_event)
    except json.JSONDecodeError as e:
        return {"error": f"Parse failed: {e}"}

root_agent = LlmAgent(
    model="gemini-flash-latest",
    name="event_processor",
    instruction="""
    You process incoming events. For each event:
    1. Parse the data
    2. Determine the required action
    3. Execute the action using available tools
    4. Log the outcome
    """,
    tools=[parse_event, your_action_tool],
)
```

---

## Trigger Endpoints

Two GCP-native endpoints (recommended over `/run`):

| Endpoint | Use for |
|----------|---------|
| `/apps/{app}/trigger/pubsub` | Cloud Pub/Sub push subscriptions |
| `/apps/{app}/trigger/eventarc` | CloudEvents via Eventarc |

ADK auto-handles per these endpoints:
- Base64 decode + JSON parse
- Session UUID generation (one session per event)
- Concurrency control
- Exponential backoff retries

All events normalize to:
```json
{"data": "<decoded payload>", "attributes": {"key": "value"}}
```

---

## Deployment

```bash
adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --trigger_sources="pubsub,eventarc" \
  path/to/agent
```

Post-deploy:
- **Pub/Sub**: Create push subscription → trigger endpoint URL
- **Eventarc**: Configure trigger routing → endpoint URL
- **Schedule**: Cloud Scheduler → Pub/Sub → trigger endpoint

---

## Configuration (env vars)

```bash
ADK_TRIGGER_MAX_CONCURRENT=5   # default: 10
ADK_TRIGGER_MAX_RETRIES=3      # default: 3
ADK_TRIGGER_RETRY_BASE_DELAY=1.0
ADK_TRIGGER_RETRY_MAX_DELAY=30.0
```

---

## Limitations

- Max 10-minute processing window (Pub/Sub ack deadline)
- Long-running workloads need pull subscriptions or Cloud Run Jobs
- `InMemorySessionService` makes sessions ephemeral per event — use persistent service for audit trail

---

## Related

- [[concepts/adk]] — core ADK concepts
- [[concepts/agent-runtime]] — managed deployment target
- [[concepts/adk-multi-agent]] — multi-agent patterns
