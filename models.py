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
LABELS = {
    'codex': 'Codex (GPT)',
    'deepseek': 'DeepSeek API',
    'workbuddy': 'WorkBuddy harness',
    'openai-compatible': 'Custom API / local model',
}


def model_name(backend):
    if backend == 'deepseek':
        return os.getenv('DEEPSEEK_MODEL', 'deepseek-flash')
    if backend == 'workbuddy':
        return os.getenv('WORKBUDDY_MODEL', '')
    if backend == 'codex':
        default = os.getenv('PAPER_STUDIO_MODEL', 'gpt-6.2-sol') if BACKEND == 'codex' else 'gpt-6.2-sol'
        return os.getenv('CODEX_MODEL', default)
    return os.getenv('PAPER_STUDIO_API_MODEL', os.getenv('PAPER_STUDIO_MODEL', '') if BACKEND == backend else '')


def has_vision(backend):
    if backend == 'workbuddy':
        return False
    if backend == 'deepseek':
        return os.getenv('DEEPSEEK_VISION', '0') == '1'
    if backend == BACKEND:
        return os.getenv('PAPER_STUDIO_VISION', '1' if backend == 'codex' else '0') == '1'
    return backend == 'codex'


def workbuddy_command():
    override = os.getenv('PAPER_STUDIO_WORKBUDDY_CLI')
    cli = shutil.which(override or 'codebuddy')
    if cli:
        return [cli]
    desktop = Path('/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/cli/dist/codebuddy-lite-wb.mjs')
    node = shutil.which('node')
    if not override and node and desktop.is_file():
        return [node, str(desktop)]
    raise ValueError('Install and sign in to CodeBuddy CLI, or set PAPER_STUDIO_WORKBUDDY_CLI to its executable.')


def check_backend(backend):
    if backend not in LABELS:
        raise ValueError('Unknown model provider. Choose a provider from the workspace.')
    if backend == 'deepseek' and not os.getenv('DEEPSEEK_API_KEY'):
        raise ValueError('Set DEEPSEEK_API_KEY and restart Paper2Slide to use DeepSeek.')
    if backend == 'workbuddy':
        workbuddy_command()
    if backend == 'openai-compatible' and (not os.getenv('PAPER_STUDIO_BASE_URL', '').startswith(('http://', 'https://')) or not model_name(backend)):
        raise ValueError('Set PAPER_STUDIO_BASE_URL and PAPER_STUDIO_API_MODEL and restart Paper2Slide.')
    return backend


def providers():
    return [dict(id=k, label=v, model=model_name(k), vision=has_vision(k)) for k,v in LABELS.items()]


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


def _workbuddy(work, prompt, timeout):
    args = workbuddy_command() + ['-p', '--output-format', 'json', '--tools', '',
                                 '--strict-mcp-config', '--no-session-persistence']
    if model_name('workbuddy'):
        args.extend(['--model', model_name('workbuddy')])
    run = subprocess.run(args, input=prompt, cwd=work, encoding='utf-8',
                         capture_output=True, timeout=timeout)
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
        raise RuntimeError('WorkBuddy requires login. Open CodeBuddy CLI, run /login, and try again.')
    if run.returncode or result.get('is_error') or not isinstance(answer, str) or not answer.strip():
        raise RuntimeError('WorkBuddy could not complete the request. Check your CodeBuddy CLI login and model access.')
    return answer.strip()


def call_model(work, prompt, *, backend=BACKEND, image=None, timeout=90):
    """Return the selected provider's final text for one chat or plan."""
    check_backend(backend)
    if backend == 'codex':
        return _codex(work, prompt, image, timeout)
    if backend == 'workbuddy':
        return _workbuddy(work, prompt, timeout)
    if backend == 'deepseek':
        base = 'https://api.deepseek.com'
        key = os.environ['DEEPSEEK_API_KEY']
    else:
        base = os.environ['PAPER_STUDIO_BASE_URL'].rstrip('/')
        key = os.getenv('PAPER_STUDIO_API_KEY')
    content=prompt
    if image is not None:
        encoded=base64.b64encode(image.read_bytes()).decode('ascii')
        content=[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+encoded}}]
    payload={'model':model_name(backend),'messages':[{'role':'user','content':content}],'stream':False}
    headers={'Content-Type':'application/json'}
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
