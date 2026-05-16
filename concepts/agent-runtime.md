# Agent Runtime

**Type**: Managed PaaS (Google Cloud)
**Cold start**: <1 second
**Max session length**: 7 days
**Framework agnostic**: ADK, LangGraph, LangChain, custom

## Features

- Agent Sessions — multi-user session tracking with custom session IDs
- Memory Bank — cross-session memory
- Agent Sandbox — isolated code execution environment

## Deployment Paths

| Path | How |
|---|---|
| Agent Designer (UI) | Click Deploy in Agent Designer canvas |
| agents-cli | `agents-cli deploy` (after `scaffold enhance --deployment-target cloud_run`) |
| Cloud Run (direct) | `agents-cli deploy` or manual Cloud Run setup |
| GKE | For scale-out multi-agent workloads |

## Observability

Cloud Trace enabled by default. For full prompt/response logging (production):
```bash
agents-cli infra single-project
# provisions: service account + GCS bucket + BigQuery dataset
```
Then view traces at: https://console.cloud.google.com/traces

## Related

- [[concepts/vertex-ai]] — SCALE phase of the platform
- [[concepts/adk]] — primary framework for building agents that deploy here
- [[resources/agent-platform-onboard/notes]] — deployment walkthrough
