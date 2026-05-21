# ADK `code_executor` — BuiltInCodeExecutor reference

Deep reference for the `code_executor=` config slot on `LlmAgent`. The
canonical annotated example is `test/code_runner/agent.py` (PDF explainer
sandbox, 2026-05-21). Cross-link: [[concepts/adk-llm-agent-config]] for
every OTHER `LlmAgent` slot.

---

## What it does

`code_executor=BuiltInCodeExecutor()` gives a Gemini agent the ability to
write Python on the fly and execute it in a sandboxed environment. The
model:

1. Plans what code to write.
2. Emits an `executable_code` Part (the Python source).
3. The sandbox runs it.
4. A `code_execution_result` Part comes back with the stdout + outcome.
5. The model sees the result in its context and continues reasoning.

```python
from google.adk.code_executors import BuiltInCodeExecutor

chart_maker = LlmAgent(
    name="chart_maker",
    model="gemini-2.5-flash",                # see GOTCHA 1 below
    instruction="...",
    code_executor=BuiltInCodeExecutor(),
    after_agent_callback=parse_chart_output,
)
```

---

## When to use it (and when not)

**Good fit** — tasks the LLM cannot do reliably in text:
- Numeric computation, statistics, Monte Carlo simulations
- **matplotlib charts** (the PDF explainer's headline use)
- Symbolic math via sympy
- Data wrangling with pandas

**Not a fit**:
- Anything needing network access (sandbox is offline)
- Anything needing host filesystem access (sandbox is isolated)
- Anything needing libraries outside the allowlist (`pypdf`,
  `pdfplumber`, `imgkit`, etc. are NOT available — see "sandbox limits"
  below)
- Free-text generation tasks (the model can just write the answer)

---

## Sandbox limits

The hosted sandbox allows roughly:
- `numpy`, `pandas`, `scipy`, `matplotlib`, `sympy`, `mpmath`,
  `sklearn`, `statsmodels`, standard library
- ~30 second execution timeout per run
- No network
- No host filesystem access
- Output Parts come back as either text (stdout) or `inline_data`
  (e.g. files saved by the code)

If you need a library outside the allowlist, do that work **outside** the
sandbox via a `FunctionTool` — exactly what `test/code_runner/agent.py`
does for `pypdf` (extracts text locally, passes it through state to the
code-executor agent).

---

## Reading what the executor produced

ADK delivers code-execution artifacts as Parts on the agent's events.
**The output text printed by the executed code lives in
`part.code_execution_result.output`, NOT in `part.text`.** This is the
trap that bit us 2026-05-21 — the first version of
`chart_maker_callback` only read `part.text` and missed every chart.

The clean read pattern (from `test/code_runner/agent.py`):

```python
def _collect_agent_text(callback_context, agent_name):
    chunks = []
    for ev in callback_context._invocation_context.session.events:
        if getattr(ev, "author", None) != agent_name:
            continue
        content = getattr(ev, "content", None)
        if not content or not content.parts:
            continue
        for p in content.parts:
            # Plain model text (e.g. the model's "I produced 4 charts" line).
            if getattr(p, "text", None):
                chunks.append(p.text)
            # The stdout from executed code — where print() output lives.
            cer = getattr(p, "code_execution_result", None)
            if cer and getattr(cer, "output", None):
                chunks.append(cer.output)
            # SKIP part.executable_code — including it lets the marker
            # regex span across the source template AND the real stdout,
            # corrupting captured values.
    return "\n".join(chunks)
```

---

## HARD CONSTRAINTS

### 1. `code_executor` requires an explicit code-execution-capable Gemini

Latest-alias models on Vertex `global` (e.g. `gemini-flash-latest`) do
NOT expose the built-in code-execution tool surface. Symptom:
`adk web` shows the toast "Gemini code execution tool is not supported
for model gemini-flash-latest" and the agent run halts. Fix: pin to an
explicit version that supports it (`gemini-2.5-flash` works as of
2026-05-21).

This is the SAME family of constraint as `google_search` — a Gemini-
native built-in tool, only present on specific model variants.

### 2. `code_executor` is mutually exclusive with `output_schema`

Same wall as tools↔schema. An agent with `output_schema` becomes a pure
JSON shape-fill engine — it can't use any tools, can't transfer to
sub-agents, and can't run code. Resolution: split the work, exactly
like the research-then-structure pattern from [[concepts/adk-llm-agent-config]]:
- one agent runs code (free-text output, captures via callback)
- a separate agent reads its captured state and structures it

`test/code_runner/agent.py` doesn't structure chart_maker's output —
the callback parses sentinel-wrapped print statements into a state
dict directly.

### 3. `code_executor` cannot live with LiteLlm models

`BuiltInCodeExecutor` is a Gemini-native built-in tool. LiteLlm-routed
models (deepseek/gemma/etc via OpenRouter) cannot use it — they would
just hallucinate having run code. If you need code execution AND a
non-Gemini model in the same pipeline, give the non-Gemini model a
plain `FunctionTool` (a local Python function) — that works
universally.

---

## Anti-pattern: piping LLM-generated opaque blobs through prompts

If your code executor produces large opaque output (base64 PNGs, big
binary strings, encoded artifacts), do NOT pass that through a
downstream LLM's prompt and ask it to embed/transcribe the blob into
its response. The model will:

- Burn its output token budget transcribing
- Hallucinate / loop on the pattern
- Truncate mid-string

Verified failure mode 2026-05-21: html_renderer was given the b64-PNG
list as instruction-template context and asked to embed each `<img
src="data:image/png;base64,…">`. Result: 92KB file of repeating garbage
base64 before hitting the output cap.

**Canonical fix** — placeholder + Python substitution:

1. Producer agent emits structured artifacts and writes them to a
   state slot (`state["chart_images"] = [{"section_title", "b64_png"}, …]`).
2. ALSO write a tiny list with just the titles (`state["chart_titles"]`)
   for the downstream LLM's prompt — it only needs the names.
3. Consumer LLM's instruction tells it to emit a placeholder marker
   wherever each artifact should go, using the title:
   `<!-- CHART: Section Title Here -->`.
4. The consumer's `after_agent_callback` runs a Python regex
   substitution: scan for placeholders, look up the b64 by title,
   splice in a real `<img src="data:image/png;base64,…">` tag.

The LLM never sees the base64. Output size stays small, no
hallucination risk, no token budget pressure.

Same pattern applies to ANY large opaque blob: embedded images, file
attachments, encoded payloads, etc.

---

## Reference implementation

[`test/code_runner/agent.py`](../test/code_runner/agent.py) — PDF
explainer pipeline. Pipeline shape:

```
intent_capturer  (Gemini, output_schema=UserIntent)
  -> pdf_extractor    (LiteLlm deepseek + FunctionTool extract_pdf_text)
  -> structure_planner (Gemini + BuiltInPlanner, output_schema=ExplanationPlan)
  -> chart_maker      (Gemini + code_executor)  ← uses this slot
  -> html_renderer    (Gemini, free-text HTML output)
```

Best file to copy `code_executor` patterns from. Demonstrates all three
constraints above being honored — split agents instead of fighting the
walls.

---

## Related

- [[concepts/adk-llm-agent-config]] — every OTHER LlmAgent slot + the
  shared `output_schema`↔tools constraint
- [[concepts/adk]] — high-level ADK reference
- [[logs/2026-05-21]] — the build session that vaulted this knowledge
