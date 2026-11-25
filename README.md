# Paper2Slide
**A Reusable Agent Skill for Turning Research Papers into Presentation Slides**

PENG Cheng · REN Shoupeng · ZHAO Shihan · ZHONG Yue

Paper2Slide pairs a paper-reading and presentation-planning skill with an editable PowerPoint renderer. Use the skill in your existing AI agent, or run the browser app to upload a PDF and generate a timed talk. The two bundled designs are **PolyU Red** and **PolyU Blue**.

![Paper2Slide workspace with a paper, a five-minute slot, PolyU Red and the AI provider selector](docs/images/workspace.png)

## Example presentations

Both editable decks present *Buffer of Thoughts* in five minutes. Open them in PowerPoint to see the original exhibits, section headings and timed speaker notes.

| Design | Example |
| --- | --- |
| PolyU Red | [Download the five-slide talk](docs/decks/Buffer-of-Thoughts-PolyU-Red.pptx) |
| PolyU Blue | [Download the six-slide talk with its native closing slide](docs/decks/Buffer-of-Thoughts-PolyU-Blue.pptx) |

[View the English template library screenshot](docs/images/template-library.png).

## Option A — use the skill directly

Give an attachment-capable agent the paper PDF and [SKILL.md](skills/build-paper-beamer-deck/SKILL.md), keeping the skill folder and its assets available. In Codex, copy the entire `skills/build-paper-beamer-deck` folder into `~/.codex/skills/` and start a new chat. For example:

> Use build-paper-beamer-deck. Turn the attached paper into a five-minute talk for first-year graduate students. Use PolyU Red, show the original results table, and give me editable slides with speaker notes.

The agent asks for speaking time when missing, reads the paper, selects the narrative and evidence, and follows the requested output format. It can use the bundled Beamer template (XeLaTeX/latexmk), or the provided single-result-slide PPTX renderer. Standalone output depends on the agent's file and rendering capabilities. The complete-deck PPTX renderer is included in the app.

## Option B — run the web app

Requires Python 3.12+, a configured model, and a browser. Install LibreOffice with `soffice` on PATH if you want to import additional PPTX templates. The bundled templates work without LibreOffice.

Download and unzip the repository, then start the workspace from that folder.

| Platform | Launcher |
| --- | --- |
| Windows | Double-click [start-windows.cmd](start-windows.cmd), or run `./start-windows.cmd` from PowerShell. |
| Linux | Run `sh start-linux.sh` in a terminal. Install your distribution’s Python venv package if it is packaged separately. |
| macOS | Open [启动工作台.command](启动工作台.command) with an existing environment, or run `python3.12 launch.py` for first-time setup. |

The Windows and Linux launchers create a local virtual environment, install dependencies on first use and open the workspace in your browser. An internet connection is needed for first-time installation. Keep the launcher window open while using the app. For a headless session set `PAPER_STUDIO_OPEN_BROWSER=0`.

Open **http://127.0.0.1:8769/**. Upload a text-based PDF, choose a template and confirm the speaking time. Add any audience, language or figure preferences in the chat. Generate, watch the progress indicator, review the outline and download the PPTX. Slides carry source-page references and timed speaker notes. Short talks prioritize the main idea and strongest evidence. Longer talks cover more of the paper in section order.

Use **Template library → Import PPTX** to add a template. The importer takes cover and body designs from the first two slides; use a clean template for best results. The bundled PolyU Blue design preserves the native closing layout. PolyU Blue uses section-prefixed titles; PolyU Red uses a separate section label beside the logo and a left-aligned slide title, both in 20.3 pt Arial Bold. User uploads and completed jobs stay under local directories. The configured model receives paper text and, when vision is enabled, a contact sheet of candidate exhibit pages.

## Model setup

In **AI provider**, choose a service and open **Configure**. Enter the details, click **Test connection** to send a short test message, then **Save settings**. Changes apply to the next chat or generation immediately. An in-progress job keeps its original settings.

| Workspace option | What to enter |
| --- | --- |
| DeepSeek API | Paste a DeepSeek API key. The default model is `deepseek-flash`. Use the link in the dialog to get a key from DeepSeek. |
| WorkBuddy harness | Install CodeBuddy CLI or a supported WorkBuddy desktop harness. Choose the edition that issued your **CodeBuddy** API key and paste it into the dialog. The key link opens the provider’s account page. Leave the model ID blank for the harness default. If the harness already has a working login, use **Use harness settings** and leave the key blank. |
| Custom API / local model | Enter the API base URL and model ID. Add a key for authenticated servers. For example, a local Ollama instance can use `http://127.0.0.1:11434/v1` and the installed model ID. |
| Codex (GPT) | Uses the existing Codex CLI sign-in. Set `CODEX_MODEL` for a different available model. |

[View the WorkBuddy settings dialog](docs/images/workbuddy-settings.png).

Settings last for the current server session by default. **Remember on this computer** stores the entered settings and key in a local file readable by your user account. **Forget settings** removes the web configuration and restores the startup defaults. The browser never receives a saved key. Use the image checkbox only with an API model that accepts image messages. WorkBuddy receives paper text and can cite full exhibit pages.

Existing shell configurations still work as startup defaults. `PAPER_STUDIO_BACKEND` selects the default provider. DeepSeek accepts `DEEPSEEK_API_KEY` and `DEEPSEEK_MODEL`. Compatible servers accept `PAPER_STUDIO_BASE_URL`, `PAPER_STUDIO_API_MODEL` and optional `PAPER_STUDIO_API_KEY`. WorkBuddy detects `codebuddy` on PATH or a supported macOS desktop installation with Node.js. Administrators can override the executable with `PAPER_STUDIO_WORKBUDDY_CLI`.

Provider documentation: [DeepSeek API](https://api-docs.deepseek.com/) · [CodeBuddy authentication and edition-specific keys](https://www.codebuddy.cn/docs/cli/iam).

## Reproduce the interface or add another model

[The implementation brief](INTERFACE.md) specifies the screens, routes, model contract and acceptance checks for another developer or coding agent. [The template library](library/) contains the two bundled designs. Institutional marks are included as parts of the reference layouts.
