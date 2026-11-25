"""Per-provider settings for the local Paper2Slide workspace."""
from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from threading import RLock
from urllib.parse import urlsplit

BACKEND = os.getenv('PAPER_STUDIO_BACKEND', 'codex')
LABELS = {'codex': 'Codex (GPT)', 'deepseek': 'DeepSeek API', 'workbuddy': 'WorkBuddy harness',
          'openai-compatible': 'Custom API / local model'}
EDITABLE = {'deepseek', 'workbuddy', 'openai-compatible'}


@dataclass(frozen=True)
class Connection:
    id: str
    model: str
    vision: bool = False
    base: str = ''
    key: str = field(default='', repr=False)
    region: str = 'inherit'


def defaults(provider):
    env = os.getenv
    if provider == 'codex':
        model = env('PAPER_STUDIO_MODEL', 'gpt-6.2-sol') if BACKEND == provider else 'gpt-6.2-sol'
        return Connection(provider, env('CODEX_MODEL', model), BACKEND != provider or env('PAPER_STUDIO_VISION', '1') == '1')
    if provider == 'workbuddy':
        return Connection(provider, env('WORKBUDDY_MODEL', ''), key=env('CODEBUDDY_API_KEY', ''))
    if provider == 'deepseek':
        return Connection(provider, env('DEEPSEEK_MODEL', 'deepseek-flash'), env('DEEPSEEK_VISION') == '1',
                          'https://api.deepseek.com', env('DEEPSEEK_API_KEY', ''))
    if provider == 'openai-compatible':
        model = env('PAPER_STUDIO_MODEL', '') if BACKEND == provider else ''
        return Connection(provider, env('PAPER_STUDIO_API_MODEL', model),
                          BACKEND == provider and env('PAPER_STUDIO_VISION') == '1',
                          env('PAPER_STUDIO_BASE_URL', '').rstrip('/'), env('PAPER_STUDIO_API_KEY', ''))
    raise ValueError('Unknown AI provider.')


def settings_file():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return root / 'Paper2Slide' / 'connections.json'


def endpoint(value):
    parts = urlsplit(value)
    if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.query or parts.fragment or any(c.isspace() for c in value)):
        raise ValueError('Enter an HTTP(S) API base URL without credentials, a query or a fragment.')
    if parts.scheme == 'http' and parts.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Use HTTPS for remote APIs, or HTTP on localhost for a local model.')
    return value.rstrip('/')


class Connections:
    def __init__(self, path):
        self.path = path
        self.lock = RLock()
        try:
            self.saved = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            self.saved = {}
        self.overrides = dict(self.saved)

    def get(self, provider):
        if isinstance(provider, Connection):
            return provider
        with self.lock:
            return replace(defaults(provider), **self.overrides.get(provider, {}))

    def public(self, provider):
        with self.lock:
            conf = self.get(provider)
            # A legacy endpoint can carry a token in its query. Never echo it.
            base = conf.base
            if base and provider == 'openai-compatible':
                try:
                    base = endpoint(base)
                except ValueError:
                    base = ''
            return dict(id=provider, label=LABELS[provider], model=conf.model, vision=conf.vision,
                        base=base, region=conf.region, hasKey=bool(conf.key),
                        remembered=provider in self.saved, customized=provider in self.overrides)

    def prepare(self, provider, data):
        if provider not in EDITABLE or not isinstance(data, dict):
            raise ValueError('Choose an editable provider.')
        current = self.get(provider)
        def string(name, limit):
            value = data.get(name, '').strip() if isinstance(data.get(name, ''), str) else None
            if value is None or len(value) > limit or any(ord(c) < 32 for c in value):
                raise ValueError('Invalid connection setting.')
            return value
        model = string('model', 256)
        changes = {'model': model or ('deepseek-flash' if provider == 'deepseek' else '')}
        if provider == 'workbuddy':
            if model and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_./:+-]*', model):
                raise ValueError('Enter a valid harness model ID.')
            region = data.get('region', 'inherit')
            if region not in ('inherit', 'international', 'internal', 'ioa'):
                raise ValueError('Choose a WorkBuddy edition.')
            changes['region'] = region
        else:
            changes['vision'] = data.get('vision') is True
        if provider == 'openai-compatible':
            changes['base'] = endpoint(string('base', 2048))
            if not model:
                raise ValueError('Enter the model ID served by your endpoint.')
        changed_destination = (changes.get('base', current.base) != current.base
                               or changes.get('region', current.region) != current.region)
        key = string('key', 8192)
        if key:
            changes['key'] = key
        elif changed_destination or data.get('clearKey') is True:
            changes['key'] = ''
        else:
            # Only persist credentials explicitly entered via this form.
            old = self.overrides.get(provider, {})
            if 'key' in old:
                changes['key'] = old['key']
        return changes

    def apply(self, provider, data, action):
        with self.lock:
            if provider not in EDITABLE:
                raise ValueError('Choose an editable provider.')
            if action == 'reset':
                self._commit(provider, None, False)
                return self.public(provider)
            changes = self.prepare(provider, data)
            conf = replace(defaults(provider), **changes)
            if action == 'test':
                return conf
            if action != 'save':
                raise ValueError('Unknown settings action.')
            if provider == 'deepseek' and not conf.key:
                raise ValueError('Enter a DeepSeek API key.')
            self._commit(provider, changes, data.get('remember') is True)
            return self.public(provider)

    def _commit(self, provider, changes, remember):
        saved = dict(self.saved)
        if remember:
            saved[provider] = changes
        else:
            saved.pop(provider, None)
        if saved != self.saved:
            if saved:
                self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                fd, name = tempfile.mkstemp(dir=self.path.parent)
                tmp = Path(name)
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as out:
                        json.dump(saved, out)
                    os.replace(tmp, self.path)
                finally:
                    tmp.unlink(missing_ok=True)
            else:
                self.path.unlink(missing_ok=True)
            self.saved = saved
        if changes is None:
            self.overrides.pop(provider, None)
        else:
            self.overrides[provider] = changes


connections = Connections(settings_file())
