from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from . import spool
from .models import EmulatorInactiveJob, EmulatorJob, EmulatorJobResponse

router = APIRouter(prefix="/emulator", tags=["emulator"])


@router.get("", response_class=HTMLResponse)
def upload_page() -> HTMLResponse:
    return HTMLResponse(_UPLOAD_HTML)


@router.post("/upload", response_model=EmulatorJob)
async def upload_pdf(file: Annotated[UploadFile, File()]) -> EmulatorJob:
    data = await file.read(spool.max_upload_bytes() + 1)
    try:
        return spool.create_job(file.filename or "", file.content_type, data)
    except spool.EmulatorSpoolError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/job", response_model=EmulatorJobResponse)
def job_status() -> EmulatorJobResponse:
    return spool.get_job()


@router.post("/job/consume", response_model=EmulatorInactiveJob)
def consume_job() -> EmulatorInactiveJob:
    return spool.consume_job()


_UPLOAD_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nospe Virtual Scanner</title>
<style>
html,body{height:100%;margin:0;background:#f7f7f5}
body{display:grid;place-items:center;font-family:system-ui,sans-serif}
button{width:128px;height:128px;border:1px solid #d7d7d2;border-radius:8px;background:#fff;color:#333;display:grid;place-items:center;cursor:pointer}
button[data-state=busy]{color:#9a7b22}
button[data-state=ok]{color:#167647}
button[data-state=error]{color:#a33030}
svg{width:44px;height:44px;stroke:currentColor;stroke-width:1.8;fill:none}
input{display:none}
</style>
</head>
<body>
<button id="drop" type="button" aria-label="PDF hochladen">
<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></svg>
</button>
<input id="file" type="file" accept="application/pdf,.pdf">
<script>
const drop=document.getElementById("drop");
const input=document.getElementById("file");
drop.addEventListener("click",()=>input.click());
input.addEventListener("change",()=>upload(input.files[0]));
drop.addEventListener("dragover",(event)=>{event.preventDefault();drop.dataset.state="busy";});
drop.addEventListener("dragleave",()=>{drop.dataset.state="";});
drop.addEventListener("drop",(event)=>{event.preventDefault();upload(event.dataTransfer.files[0]);});
async function upload(file){
  if(!file)return;
  drop.dataset.state="busy";
  const data=new FormData();
  data.append("file",file);
  const response=await fetch("/emulator/upload",{method:"POST",body:data});
  drop.dataset.state=response.ok?"ok":"error";
}
</script>
</body>
</html>"""
