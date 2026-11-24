# Paper2Slide
**A Reusable Agent Skill for Turning Research Papers into Presentation Slides**

PENG Cheng · REN Shoupeng · ZHAO Shihan · ZHONG Yue

Paper2Slide pairs a paper-reading and presentation-planning skill with an editable PowerPoint renderer. Use the skill in your existing AI agent, or run the browser app to upload a PDF and generate a timed talk. The two bundled designs are **PolyU Red** and **Blue**.

## Option A — use the skill directly

Give an attachment-capable agent the paper PDF and [SKILL.md](skills/build-paper-beamer-deck/SKILL.md), keeping the skill folder and its assets available. In Codex, copy the entire `skills/build-paper-beamer-deck` folder into `~/.codex/skills/` and start a new chat. For example:

> Use build-paper-beamer-deck. Turn the attached paper into a five-minute talk for first-year graduate students. Use PolyU Red, show the original results table, and give me editable slides with speaker notes.

The agent asks for speaking time when missing, reads the paper, selects the narrative and evidence, and follows the requested output format. It can use the bundled Beamer template (XeLaTeX/latexmk), or the provided single-result-slide PPTX renderer. Standalone output depends on the agent's file and rendering capabilities. The complete-deck PPTX renderer is included in the app.

## Option B — run the web app

Requires Python 3.12+, a configured model, and a browser. Install LibreOffice with `soffice` on PATH if you want to import additional PPTX templates. The bundled templates work without LibreOffice.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Open **http://127.0.0.1:8769/**. Upload a text-based PDF, choose a template and confirm the speaking time. Add any audience, language or figure preferences in the chat. Generate, watch the progress indicator, review the outline and download the PPTX. Slides carry source-page references and timed speaker notes. Short talks prioritize the main idea and strongest evidence. Longer talks cover more of the paper in section order.

Use **模板库 → 导入 PPTX** to add a template. The importer takes cover and body designs from the first two slides; use a clean template for best results. The bundled Blue design preserves the native closing slide. User uploads and completed jobs stay under local directories. The configured model receives paper text and, when vision is enabled, a contact sheet of candidate exhibit pages.

## Model setup

Set environment variables **before** launching the server. Both chat and deck planning use the same adapter in [models.py](models.py).

| Mode | Settings |
| --- | --- |
| Codex CLI | Default. Install and sign in to the Codex CLI; put `codex` on PATH. Set `PAPER_STUDIO_MODEL` to a model available to your account. The bundled desktop integration uses its HTTP Responses provider. |
| Hosted API, including DeepSeek | Set `PAPER_STUDIO_BACKEND=openai-compatible`, `PAPER_STUDIO_BASE_URL` to the provider's chat API base, `PAPER_STUDIO_MODEL` to your model ID, and `PAPER_STUDIO_API_KEY` in your shell. For DeepSeek the base can be `https://api.deepseek.com`. |
| Local model | Start a local OpenAI-compatible endpoint, for example Ollama or llama.cpp. Use the settings below and the model ID actually served by that endpoint. An API key is optional. |

```sh
export PAPER_STUDIO_BACKEND=openai-compatible
export PAPER_STUDIO_BASE_URL=http://127.0.0.1:11434/v1
export PAPER_STUDIO_MODEL=your-installed-model
python server.py
```

The adapter appends `/chat/completions` to the base URL. API/local mode defaults to text-only: the model can cite a full original exhibit page. Enable `PAPER_STUDIO_VISION=1` for a model that accepts image messages and can plan exhibit crops. Choose a context window large enough for the paper and skill. Credentials are read server-side from the environment.

## Reproduce the interface or add another model

[The implementation brief](INTERFACE.md) specifies the screens, routes, model contract and acceptance checks for another developer or coding agent. [The template library](library/) contains the two bundled designs. Institutional marks are included as parts of the reference layouts.
