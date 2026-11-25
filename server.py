from email.parser import BytesParser
from email.policy import default
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from uuid import uuid4
from zipfile import BadZipFile
import json,mimetypes,re,subprocess,threading,sys
from templates import ROOT,LIB,RUNTIME,catalog,import_template,init_red
from models import BACKEND, check_backend, model_name, providers
from generate import read_paper,plan,export,count_slides,chat_reply,section_name,blue_heading

JOBS=ROOT/'jobs'; WEB=ROOT/'web'
PORT=8769; workers=ThreadPoolExecutor(max_workers=1)
def write_state(work,**values):
    tmp=work/'state.tmp';tmp.write_text(json.dumps(values,ensure_ascii=False),encoding='utf-8');tmp.replace(work/'state.json')

PDF_LIMIT=45*1024*1024
CHAT_LIMIT=96*1024

def read_conversation(raw):
    if len(raw)>CHAT_LIMIT: raise ValueError('This conversation is too long. Shorten the instructions or clear the chat.')
    if not raw: return []
    messages=json.loads(raw)
    if not isinstance(messages,list): raise ValueError('Invalid conversation format.')
    for item in messages:
        if not isinstance(item,dict) or item.get('role') not in ('user','assistant') or not isinstance(item.get('content'),str) or not item['content'].strip():
            raise ValueError('Invalid chat message.')
    return [{'role':m['role'],'content':m['content']} for m in messages]

def read_submission(content_type,raw):
    # Existing binary-PDF clients still use the same endpoint.
    if content_type.split(';',1)[0].lower()!='multipart/form-data': return raw,[]
    envelope=BytesParser(policy=default).parsebytes(b'Content-Type: '+content_type.encode('ascii')+b'\r\n\r\n'+raw)
    fields={part.get_param('name',header='content-disposition'):part.get_payload(decode=True) for part in envelope.iter_parts()}
    return fields.get('paper',b''),read_conversation(fields.get('conversation',b''))

def generate(work,minutes,theme,conversation=(),backend=BACKEND):
    def update(step,message): write_state(work,status='running',step=step,message=message)
    try:
        update(1,'Extracting paper text and original figures and tables…')
        paper,exhibits,pages=read_paper(work)
        page_count=count_slides(minutes)+int(bool(theme.get("closingTitle")))
        update(2,f'Planning a {page_count}-slide presentation for a {minutes}-minute talk…')
        data=plan(work,minutes,theme,paper,exhibits,conversation,backend)
        update(3,'Adding original exhibits, page references and speaker notes…')
        (work/'plan.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        export(work,theme,minutes,data)
        outline=[data['title']]+[s['title'] for s in data['slides']]
        if theme.get('nativeBookends'):
            outline=[blue_heading('Overview',data['title'])]+[blue_heading(section_name(s),s['title']) for s in data['slides']]
        if theme.get('closingTitle'): outline.append(theme['closingTitle'])
        write_state(work,status='done',step=4,message='Your PowerPoint is ready.',title=data['title'],pages=len(outline),minutes=minutes,theme=theme['name'],outline=outline)
    except subprocess.TimeoutExpired: write_state(work,status='error',message='The model timed out. Check your connection and generate again.')
    except Exception as e:
        print(type(e).__name__,str(e)[:500],flush=True)
        write_state(work,status='error',message=str(e)[:350] or 'Could not read this file. Check the file and try again.')
    finally:
        for name in ('catalog.json','figures.jpg'): (work/name).unlink(missing_ok=True)

class Handler(BaseHTTPRequestHandler):
    def send(self,status,body,typ='application/json; charset=utf-8',download=False):
        if not isinstance(body,bytes): body=json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store')
        if download: self.send_header('Content-Disposition','attachment; filename="paper-slides.pptx"')
        self.end_headers();self.wfile.write(body)
    def local(self):
        return self.headers.get('Host') in {f'127.0.0.1:{PORT}',f'localhost:{PORT}'}
    def do_GET(self):
        if not self.local(): return self.send(403,{'error':'Local access only.'})
        path=urlsplit(self.path).path
        if path=='/api/templates': return self.send(200,{'templates':catalog(),'model':model_name(BACKEND),'backend':BACKEND,'providers':providers()})
        if path in ('/','/style.css','/app.js'):
            f=WEB/('index.html' if path=='/' else path[1:]);return self.send(200,f.read_bytes(),mimetypes.guess_type(f)[0]+'; charset=utf-8')
        m=re.fullmatch(r'/library/([a-f0-9]{24}|polyu-transcope)/(cover|cover-preview|body|closing)\.png',path)
        if m:
            f=LIB/m[1]/(m[2]+'.png')
            if f.is_file(): return self.send(200,f.read_bytes(),'image/png')
        m=re.fullmatch(r'/api/jobs/([a-f0-9]{32})(/download)?',path)
        if m:
            work=JOBS/m[1]
            if (work/'state.json').exists():
                state=json.loads((work/'state.json').read_text(encoding='utf-8'))
                if not m[2]: return self.send(200,state)
                if state['status']=='done': return self.send(200,(work/'slides.pptx').read_bytes(),'application/vnd.openxmlformats-officedocument.presentationml.presentation',True)
        self.send(404,{'error':'File not found.'})
    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.local() or (origin and origin!='http://'+self.headers.get('Host','')) or self.headers.get('X-Studio')!='1':
            return self.send(403,{'error':'Upload files through the local workspace.'})
        try:
            url=urlsplit(self.path); params=parse_qs(url.query)
            size=int(self.headers.get('Content-Length','0'))
            if url.path=='/api/chat':
                if not 0<size<=CHAT_LIMIT+4096: return self.send(413,{'error':'This conversation is too long. Shorten it and try again.'})
                payload=json.loads(self.rfile.read(size))
                messages=read_conversation(json.dumps(payload['messages'],ensure_ascii=False).encode())
                if not messages or messages[-1]['role']!='user': raise ValueError('Enter a customization request.')
                theme=next((t['name'] for t in catalog() if t['id']==payload.get('template')),None)
                with TemporaryDirectory(prefix='studio-chat-') as tmp:
                    answer=chat_reply(Path(tmp),messages,theme,payload.get('minutes'),check_backend(payload.get('backend',BACKEND)))
                return self.send(200,{'reply':answer})
            upload_limit=PDF_LIMIT+CHAT_LIMIT+4096 if url.path=='/api/jobs' else PDF_LIMIT
            if not 0<size<=upload_limit: return self.send(413,{'error':'Upload a file of 45 MB or less.'})
            if url.path=='/api/templates':
                data=self.rfile.read(size)
                if not data.startswith(b'PK'): raise ValueError('Choose a .pptx template.')
                name=params.get('name',['New template'])[0].strip() or 'New template'
                try: value=import_template(data,name)
                except (BadZipFile,KeyError,subprocess.SubprocessError): raise ValueError('Could not read this template. Save it as a standard .pptx and try again.')
                return self.send(201,value)
            if url.path!='/api/jobs': return self.send(404,{'error':'Unknown endpoint.'})
            backend=check_backend(params.get('backend',[BACKEND])[0])
            minutes=int(params.get('minutes',['0'])[0])
            if not 1<=minutes<=45: raise ValueError('Choose a speaking time from 1 to 45 minutes.')
            theme=next((t for t in catalog() if t['id']==params.get('template',[''])[0]),None)
            if not theme: raise ValueError('Choose a template from the library first.')
            data,conversation=read_submission(self.headers.get('Content-Type',''),self.rfile.read(size))
            if len(data)>PDF_LIMIT: return self.send(413,{'error':'Upload a PDF of 45 MB or less.'})
            if b'%PDF-' not in data[:1024]: raise ValueError('Choose a paper in PDF format.')
            key=uuid4().hex;work=JOBS/key;work.mkdir()
            (work/'paper.pdf').write_bytes(data);write_state(work,status='running',step=0,message='Paper uploaded. Waiting to generate…')
            if conversation: (work/'conversation.json').write_text(json.dumps(conversation,ensure_ascii=False),encoding='utf-8')
            workers.submit(generate,work,minutes,theme,conversation,backend)
            self.send(202,{'id':key})
        except subprocess.TimeoutExpired: self.send(504,{'error':'The model timed out. You can still generate with the instructions you entered.'})
        except RuntimeError as e: self.send(502,{'error':str(e)})
        except ValueError as e: self.send(400,{'error':str(e)})
        except Exception as e:
            print(type(e).__name__,str(e)[:300],flush=True);self.send(400,{'error':'Could not read the file. Check it and try again.'})

if __name__=='__main__':
    init_red();JOBS.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    for state in JOBS.glob('*/state.json'):
        if json.loads(state.read_text(encoding='utf-8')).get('status')=='running': write_state(state.parent,status='error',message='The server restarted. Please submit your paper again.')
    print(f'Paper2Slide — http://127.0.0.1:{PORT}/',flush=True)
    server.serve_forever()
