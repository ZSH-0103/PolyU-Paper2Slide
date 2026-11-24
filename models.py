"""Model boundary shared by conversational customization and paper planning."""
import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

BACKEND=os.getenv('PAPER_STUDIO_BACKEND','codex')
MODEL=os.getenv('PAPER_STUDIO_MODEL','gpt-6.2-sol' if BACKEND=='codex' else '')
VISION=os.getenv('PAPER_STUDIO_VISION','1' if BACKEND=='codex' else '0')=='1'
PROVIDER='{name="OpenAI",base_url="https://chatgpt.com/backend-api/codex",wire_api="responses",requires_openai_auth=true,supports_websockets=false,request_max_retries=0,stream_max_retries=0}'

def _codex(work,prompt,image,timeout):
    desktop=Path('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex')
    exe=shutil.which('codex') or (str(desktop) if desktop.is_file() else None)
    if not exe: raise RuntimeError('Install and sign in to Codex CLI or configure an API/local model.')
    args=[exe,'exec','--skip-git-repo-check','--ephemeral','-s','read-only','-m',MODEL]
    if desktop.exists() and Path(exe).resolve()==desktop.resolve():
        args+=['--ignore-user-config','--disable','shell_tool','-c','model_reasoning_effort="low"','-c','model_provider="openai_http"','-c','model_providers.openai_http='+PROVIDER]
        cache=Path(os.getenv('CODEX_HOME',str(Path.home()/'.codex')))/'models_cache.json'
        if cache.is_file():
            catalog=work/'catalog.json'
            catalog.write_text(json.dumps({'models':json.loads(cache.read_text())['models']}))
            args+=['-c','model_catalog_json='+json.dumps(str(catalog))]
    if image: args+=['-i',str(image)]
    args+=['-C',str(work),'--json','-']
    result=subprocess.run(args,input=prompt,text=True,capture_output=True,timeout=timeout)
    messages=[];errors=[]
    for line in result.stdout.splitlines():
        try: event=json.loads(line)
        except ValueError: continue
        item=event.get('item',{})
        if item.get('type')=='agent_message': messages.append(item.get('text',''))
        if event.get('type') in ('error','turn.failed'): errors.append(str(event.get('message') or event.get('error','')))
    if result.returncode or not messages:
        detail=(errors[-1] if errors else result.stderr.strip().splitlines()[-1:] or '')
        raise RuntimeError('Codex 调用失败。请检查本机 Codex 登录状态与网络，再重试。 '+str(detail)[:240])
    return messages[-1].strip()


def call_model(work, prompt, *, image=None, timeout=90):
    """Return the assistant's final text. The optional image is a local JPEG."""
    if BACKEND=='codex':
        return _codex(work,prompt,image,timeout)
    if BACKEND!='openai-compatible':
        raise ValueError('Choose codex or openai-compatible for PAPER_STUDIO_BACKEND.')
    base=os.getenv('PAPER_STUDIO_BASE_URL','').rstrip('/')
    if not base.startswith(('http://','https://')) or not MODEL:
        raise ValueError('Set PAPER_STUDIO_BASE_URL and PAPER_STUDIO_MODEL before starting the server.')
    content=prompt
    if image is not None:
        encoded=base64.b64encode(image.read_bytes()).decode('ascii')
        content=[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+encoded}}]
    payload={'model':MODEL,'messages':[{'role':'user','content':content}],'stream':False}
    headers={'Content-Type':'application/json'}
    key=os.getenv('PAPER_STUDIO_API_KEY')
    if key: headers['Authorization']='Bearer '+key
    request=urllib.request.Request(base+'/chat/completions',data=json.dumps(payload).encode(),headers=headers)
    try:
        with urllib.request.urlopen(request,timeout=timeout) as response:
            result=json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'Model endpoint returned HTTP {exc.code}. Check the endpoint, model and authentication.') from exc
    except (OSError,ValueError) as exc:
        raise RuntimeError('Could not read the model response. Check the endpoint and timeout.') from exc
    try:
        answer=result['choices'][0]['message']['content']
    except (IndexError,KeyError,TypeError) as exc:
        raise RuntimeError('The endpoint did not return a chat-completions message.') from exc
    if not isinstance(answer,str) or not answer.strip():
        raise RuntimeError('The model returned an empty answer.')
    return answer.strip()
