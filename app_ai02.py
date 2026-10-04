"""ALG-AI-02: Intelligent Document Investigator demo."""
from __future__ import annotations
from collections import Counter
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from document_investigator import Chunk, DocumentError, extract_file, investigate, summarize_documents

app = FastAPI(title="ALG-AI-02 Intelligent Document Investigator", version="1.0.0", description="Upload documents, ask questions, inspect cited passages, and review conflicts and uncertainty.")
INDEX: list[Chunk] = []
DOCUMENTS: dict[str, int] = {}

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)

@app.get("/api/health")
def health(): return {"status": "ok", "track": "AI/ML", "problem_id": "ALG-AI-02"}

@app.get("/api/documents")
def documents(): return {"documents": summarize_documents(INDEX), "chunk_count": len(INDEX)}

@app.post("/api/documents")
async def upload_documents(files: list[UploadFile] = File(...)):
    if not files: raise HTTPException(400, "Select at least one document.")
    added, errors = [], []
    for upload in files:
        name = upload.filename or "unnamed"
        try:
            chunks = extract_file(name, await upload.read())
            INDEX.extend(chunks)
            DOCUMENTS[name] = len(chunks)
            added.append({"name": name, "chunks": len(chunks)})
        except DocumentError as exc: errors.append({"name": name, "error": str(exc)})
    if not added: raise HTTPException(400, {"message": "No documents were added.", "errors": errors})
    return {"added": added, "errors": errors, "total_documents": len(DOCUMENTS), "total_chunks": len(INDEX)}

@app.delete("/api/documents")
def clear_documents():
    INDEX.clear(); DOCUMENTS.clear()
    return {"status": "cleared"}

@app.post("/api/investigate")
def ask(body: Question):
    if not INDEX: raise HTTPException(400, "Upload one or more documents first.")
    try: return investigate(body.question.strip(), INDEX)
    except DocumentError as exc: raise HTTPException(400, str(exc)) from exc

@app.get("/", response_class=HTMLResponse)
def home(): return HTMLResponse(PAGE)

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DocuLens - Intelligent Document Investigator</title><style>.badge{display:none!important}
:root{color-scheme:dark;--bg:#0b1020;--panel:#111a2d;--line:#25334b;--text:#eef4ff;--muted:#a2b0c5;--teal:#63e6cf;--blue:#83adff;--amber:#ffd27d}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 75% -20%,#203960 0,transparent 50%),var(--bg);color:var(--text);font:15px/1.55 system-ui,Segoe UI,sans-serif}.wrap{width:min(1080px,calc(100% - 36px));margin:auto}.top{padding:27px 0 15px;border-bottom:1px solid var(--line)}.brand{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--teal);font-weight:800}.top h1{margin:10px 0 4px;font-size:clamp(28px,5vw,43px);line-height:1.1;letter-spacing:-.035em}.sub{color:var(--muted);margin:0}main{display:grid;grid-template-columns:350px 1fr;gap:18px;padding:23px 0}.card{background:linear-gradient(145deg,#141f34,#101827);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 15px 45px #03071155}.card h2{font-size:17px;margin:0 0 4px}.hint{color:var(--muted);font-size:13px;margin:0 0 16px}label{display:block;font-weight:650;margin:15px 0 7px}input[type=file],textarea{width:100%;background:#0b1322;color:var(--text);border:1px solid #34445e;border-radius:10px;padding:11px}textarea{min-height:106px;resize:vertical}button{background:var(--teal);color:#09201d;border:0;border-radius:9px;padding:11px 14px;font-weight:750;cursor:pointer}button.secondary{background:#1b2c44;color:#dbe9ff;border:1px solid #334963}button:disabled{opacity:.5;cursor:wait}.row{display:flex;gap:8px;align-items:center;margin-top:12px}.row button{flex:1}.docs{list-style:none;padding:0;margin:15px 0 0}.docs li{padding:9px 0;border-top:1px solid var(--line);font-size:13px;overflow-wrap:anywhere}.status{color:var(--muted);font-size:13px;margin-top:10px;min-height:20px}.right{display:flex;flex-direction:column;gap:18px}.results{min-height:390px}.empty{border:1px dashed #34445e;border-radius:12px;padding:28px;color:var(--muted);text-align:center;margin-top:15px}.callout{padding:13px 15px;border-radius:10px;background:#102c2a;border:1px solid #235a53;color:#b8f6e9;margin:12px 0}.callout.warn{background:#342815;border-color:#725628;color:#ffe0a5}.answer{padding:14px;border-left:3px solid var(--teal);background:#10221f;border-radius:8px;margin:14px 0}.answer p{margin:6px 0 0;font-size:16px;color:#e8fff9}.source{border:1px solid var(--line);border-radius:11px;padding:14px;margin:10px 0;background:#0c1422}.sourcehead{color:var(--blue);font-size:13px;font-weight:700}.excerpt{margin:9px 0 0;color:#d9e2ef;white-space:pre-wrap}.conflict{padding:12px;background:#321e23;border:1px solid #75414b;border-radius:10px;margin:10px 0}.footer{color:#7f8da2;font-size:12px;padding:0 0 25px}.tiny{font-size:12px;color:var(--muted)}@media(max-width:780px){main{grid-template-columns:1fr}}
</style></head><body><header class="top"><div class="wrap"><div class="brand">DocuLens / Problem statement demo</div><h1>Ask your documents.<br><span style="color:var(--teal)">See the evidence.</span></h1><p class="sub">Investigate multiple files with cited passages, possible conflict flags, and clear uncertainty.</p></div></header><main class="wrap"><section class="card"><h2>1. Build your document set</h2><p class="hint">Files are processed in memory for this session. PDF, DOCX, TXT, Markdown, and CSV. 12 MB per file.</p><label for="files">Choose one or more files</label><input id="files" type="file" multiple accept=".pdf,.docx,.txt,.md,.csv"><div class="row"><button id="upload" onclick="uploadFiles()">Add documents</button><button class="secondary" onclick="clearDocs()">Clear set</button></div><div id="uploadStatus" class="status" aria-live="polite"></div><ul id="docs" class="docs"><li>No documents loaded.</li></ul><label for="question">2. Ask a question</label><textarea id="question" placeholder="What are the main eligibility requirements? Do the files disagree about the deadline?"></textarea><div class="row"><button id="ask" onclick="askQuestion()">Find evidence</button></div><div class="tiny" style="margin-top:12px">Try: ?What does the policy say about deadlines?? or ?Which documents describe eligibility??</div></section><div class="right"><section class="card results"><h2>Investigation report</h2><p class="hint">Extractive answers with evidence you can inspect. Retrieval runs locally; no API key is required.</p><div id="report"><div class="empty">Upload a few documents, then ask a question. Relevant passages and their file/page locations will appear here.</div></div></section><section class="card"><h2>How this demo works</h2><p class="hint">Text extraction - structured passages - hybrid TF-IDF retrieval - cited extractive answer - disagreement and uncertainty review.</p><p class="tiny">The system uses local lexical retrieval, not an LLM. It does not perform OCR or guarantee semantic understanding. Scores rank passages; they are not factual confidence.</p></section></div></main><footer class="wrap footer">Intelligent Document Investigator - Uploaded content stays in server memory and is cleared on restart.</footer><script>
async function uploadFiles(){let files=document.getElementById('files').files;if(!files.length){msg('Select at least one file.');return}let fd=new FormData();for(const f of files)fd.append('files',f);let b=document.getElementById('upload');b.disabled=true;msg('Reading and indexing documents?');try{let r=await fetch('/api/documents',{method:'POST',body:fd}),d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));msg(`Added ${d.added.length} file(s); ${d.total_chunks} searchable passages.`);if(d.errors?.length)msg(d.errors.map(x=>`${x.name}: ${x.error}`).join(' ? '));await refreshDocs()}catch(e){msg(e.message)}finally{b.disabled=false}}
async function refreshDocs(){let d=await(await fetch('/api/documents')).json(),el=document.getElementById('docs');el.innerHTML=d.documents.length?d.documents.map(x=>`<li><b>${esc(x.name)}</b><br><span class="tiny">${x.passages} passages - ${x.characters.toLocaleString()} characters${x.pages?` - ${x.pages} pages`:''}</span><br><span class="tiny">${esc(x.preview)}</span></li>`).join(''):'<li>No documents loaded.</li>'}
async function clearDocs(){await fetch('/api/documents',{method:'DELETE'});await refreshDocs();document.getElementById('report').innerHTML='<div class="empty">Document set cleared. Upload files to begin a new investigation.</div>';msg('Document set cleared.')}
async function askQuestion(){let q=document.getElementById('question').value.trim();if(q.length<3){document.getElementById('report').innerHTML='<div class="callout warn">Enter a longer question to search the documents.</div>';return}let b=document.getElementById('ask');b.disabled=true;document.getElementById('report').innerHTML='<div class="empty">Searching passages?</div>';try{let r=await fetch('/api/investigate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})}),d=await r.json();if(!r.ok)throw Error(d.detail);render(d)}catch(e){document.getElementById('report').innerHTML=`<div class="callout warn">${esc(e.message)}</div>`}finally{b.disabled=false}}
function render(d){let answer=d.answer||{};let h=`<div class="callout ${d.uncertainty.flagged?'warn':''}"><b>${d.uncertainty.flagged?'Review evidence':'Evidence found'}</b><br>${esc(d.uncertainty.message)}</div><div class="answer"><div class="tiny">EXTRACTED ANSWER - verify against cited sources</div><p>${esc(answer.text||'No answer extracted.')}</p></div><div class="tiny">Retrieval: ${esc(d.retrieval.method)} - ${d.retrieval.matched_passages} passages</div>`;if(d.conflicts.length){h+='<h3>Possible conflicts to review</h3>';for(const c of d.conflicts)h+=`<div class="conflict"><b>${esc(c.reason)}</b>${c.claims.map(x=>`<article class="source"><div class="sourcehead">${esc(x.document)}${x.page?` - page ${x.page}`:''}</div><p class="excerpt">${esc(x.text)}</p></article>`).join('')}</div>`}h+=`<h3>Source passages (${d.sources.length})</h3>`;h+=d.sources.length?d.sources.map(source).join(''):'<div class="empty">No matching passages found.</div>';document.getElementById('report').innerHTML=h}
function source(s){return `<article class="source"><div class="sourcehead">${esc(s.document)}${s.page?` ? page ${s.page}`:''} ? retrieval ${Math.round(s.score*100)}%</div><p class="excerpt">${esc(s.excerpt)}</p></article>`}
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function msg(x){document.getElementById('uploadStatus').textContent=x}refreshDocs();
</script></body></html>"""
