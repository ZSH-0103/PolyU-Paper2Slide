"""Model boundary shared by conversational customization and paper planning."""
import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from connections import BACKEND, LABELS, connections

def model_name(backend):
    return connections.get(backend).model


def has_vision(backend):
    return connections.get(backend).vision


def workbuddy_command():
    override = os.getenv('PAPER_STUDIO_WORKBUDDY_CLI')
    cli = shutil.which(override or 'codebuddy')
    if cli:
        return [cli]
    desktop = Path('/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/cli/dist/codebuddy-lite-wb.mjs')
    node = shutil.which('node')
    if not override and node and desktop.is_file():
        return [node, str(desktop)]
    raise ValueError('Install CodeBuddy CLI or a supported WorkBuddy desktop harness, then test the connection again.')


def check_backend(backend):
    conf = connections.get(backend)
    if conf.id == 'deepseek' and not conf.key:
        raise ValueError('Open Configure and enter your DeepSeek API key.')
    if conf.id == 'workbuddy':
        workbuddy_command()
    if conf.id == 'openai-compatible' and (not conf.base.startswith(('http://', 'https://')) or not conf.model):
        raise ValueError('Open Configure and enter the API base URL and model ID.')
    return conf


def providers():
    return [connections.public(provider) for provider in LABELS]



PROVIDER='{name="OpenAI",base_url="https://chatgpt.com/backend-api/codex",wire_api="responses",requires_openai_auth=true,supports_websockets=false,request_max_retries=0,stream_max_retries=0}'

def _codex(work,prompt,image,timeout):
    desktop=Path('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex')
    exe=shutil.which('codex') or (str(desktop) if desktop.is_file() else None)
    if not exe: raise RuntimeError('Install and sign in to Codex CLI or configure an API/local model.')
    args=[exe,'exec','--skip-git-repo-check','--ephemeral','-s','read-only','-m',model_name('codex')]
    if desktop.exists() and Path(exe).resolve()==desktop.resolve():
        args+=['--ignore-user-config','--disable','shell_tool','-c','model_reasoning_effort="low"','-c','model_provider="openai_http"','-c','model_providers.openai_http='+PROVIDER]
        cache=Path(os.getenv('CODEX_HOME',str(Path.home()/'.codex')))/'models_cache.json'
        if cache.is_file():
            catalog=work/'catalog.json'
            catalog.write_text(json.dumps({'models':json.loads(cache.read_text(encoding='utf-8'))['models']}))
            args+=['-c','model_catalog_json='+json.dumps(str(catalog))]
    if image: args+=['-i',str(image)]
    args+=['-C',str(work),'--json','-']
    result=subprocess.run(args,input=prompt,encoding="utf-8",capture_output=True,timeout=timeout)
    messages=[];errors=[]
    for line in result.stdout.splitlines():
        try: event=json.loads(line)
        except ValueError: continue
        item=event.get('item',{})
        if item.get('type')=='agent_message': messages.append(item.get('text',''))
        if event.get('type') in ('error','turn.failed'): errors.append(str(event.get('message') or event.get('error','')))
    if result.returncode or not messages:
        detail=(errors[-1] if errors else result.stderr.strip().splitlines()[-1:] or '')
        raise RuntimeError('Codex could not complete the request. Check your sign-in and network connection, then try again. '+str(detail)[:240])
    return messages[-1].strip()


def _workbuddy(work, prompt, timeout, conf):
    args = workbuddy_command() + ['-p', '--output-format', 'json', '--tools', '',
                                 '--strict-mcp-config', '--no-session-persistence']
    if conf.model:
        args.extend(['--model', conf.model])
    env = os.environ.copy()
    if conf.region != 'inherit':
        env.pop('CODEBUDDY_INTERNET_ENVIRONMENT', None)
        if conf.region != 'international':
            env['CODEBUDDY_INTERNET_ENVIRONMENT'] = conf.region
    env.pop('CODEBUDDY_API_KEY', None)
    if conf.key:
        env['CODEBUDDY_API_KEY'] = conf.key
        env.pop('CODEBUDDY_AUTH_TOKEN', None)
    run = subprocess.run(args, input=prompt, cwd=work, encoding='utf-8',
                         capture_output=True, timeout=timeout, env=env)
    try:
        result = json.loads(run.stdout)
    except ValueError:
        result = {}
    if isinstance(result, list):
        result = next((event for event in reversed(result) if event.get('type') == 'result'), {})
    if not isinstance(result, dict):
        result = {}
    answer = result.get('result')
    if 'authentication required' in (answer or run.stdout or '').lower():
        raise RuntimeError('WorkBuddy requires authentication. Open Configure, select your edition and enter a CodeBuddy API key.')
    if run.returncode or result.get('is_error') or not isinstance(answer, str) or not answer.strip():
        raise RuntimeError('WorkBuddy could not complete the request. Check the edition, key and model in Configure.')
    return answer.strip()


def call_model(work, prompt, *, backend=BACKEND, image=None, timeout=90):
    """Return the selected provider's final text for one chat or plan."""
    conf = check_backend(backend)
    if conf.id == 'codex':
        return _codex(work, prompt, image, timeout)
    if conf.id == 'workbuddy':
        return _workbuddy(work, prompt, timeout, conf)
    base, key = conf.base, conf.key
    content=prompt
    if image is not None:
        encoded=base64.b64encode(image.read_bytes()).decode('ascii')
        content=[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+encoded}}]
    payload={'model':conf.model,'messages':[{'role':'user','content':content}],'stream':False}
    headers={'Content-Type':'application/json'}

    request=urllib.request.Request(base+'/chat/completions',data=json.dumps(payload).encode(),headers=headers)
    if key: request.add_unredirected_header('Authorization', 'Bearer '+key)
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
