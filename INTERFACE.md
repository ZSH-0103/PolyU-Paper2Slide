# Paper2Slide implementation brief

Build a loopback-only research-paper slide studio with two tabs, a workspace and a template library. Use the supplied skill for editorial decisions. Keep file processing and rendering in the backend. Keep provider keys out of HTML, browser storage and model prompts.

1. Workspace: place a PDF upload/drop target, a template selector and a required speaking-time selector next to a 16:9 template preview. For PolyU Blue expose cover, body and closing views. A customization chat accepts audience, language, evidence and phrasing preferences. Support sending a message for discussion and including an unsent draft on Generate.
2. Templates: list the library; import an ordinary PPTX, extract the cover and body designs, persist a reusable ID and reload the catalog. Keep institutional marks and geometry. Preserve PolyU Blue's native opening and closing slides.
3. Generate: accept PDF + chosen template + minutes + chat history. Read text with physical PDF page numbers and inventory candidate exhibits. Give the language model the skill, the paper as untrusted evidence, and the user's instructions. Use its structured plan to place editable text, original exhibits, citations and notes. Rendering owns slide geometry and timing.
4. Results: show queued/extracting/planning/rendering/completed states, a real outline, an actionable error on failure, and a PPTX download.

## HTTP contract

All POSTs require the header `X-Studio: 1`. The server validates its local host and browser origin.

- GET /api/templates → {templates,model,backend,providers:[{id,label,model,vision}]}
- POST /api/templates?name=... with binary PPTX → template metadata
- POST /api/chat with JSON {messages:[{role,content}],template,minutes,backend} → {reply}
- POST /api/jobs?template=ID&minutes=5&backend=deepseek with multipart fields paper (PDF) and conversation (JSON string); raw PDF remains supported → {id}
- GET /api/jobs/ID → {status,step,message}; when done also {title,pages,minutes,theme,outline}
- GET /api/jobs/ID/download → editable .pptx

## Model contract

Implement `call_model(work,prompt,*,backend=BACKEND,image=None,timeout=90) -> str` in models.py. A conversational call returns plain text. A planner call returns a single JSON object with title, authors and slides. Each content slide has a short paper section label (section), a title, one to three {keyword,text} points, speaker notes, a one-based physical PDF page, and an optional exhibit {label,box:[left,top,right,bottom]}. Box coordinates are relative to the PDF page on a 0–1000 scale. Defaults, validation and example JSON are in generate.py. The optional backend on each chat or job selects codex, deepseek, workbuddy, or openai-compatible. Omission uses the server default. Each queued job retains its chosen provider. The client submits only the provider ID. Credentials and executable paths are server settings.

Red content slides show the section label beside the logo and the specific title below the red band. Both use bold, left-aligned Arial 20.3 pt. PolyU Blue uses “Section · Title” throughout, including its native cover and closing.

## Check a rebuild

With no duration or template selected, Generate is disabled. Uploading a template adds it to the selector after refresh. A user-specified slide heading must appear in the downloaded file. A five-minute PolyU Blue talk has a cover, four content slides and its original Thanks! page; a five-minute PolyU Red talk has five slides total. Confirm duration, outline, source pages and notes against the exported PPTX.
