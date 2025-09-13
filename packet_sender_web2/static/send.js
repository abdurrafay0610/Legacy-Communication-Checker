
async function postJSON(url, body){
  const resp = await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const data = await resp.json();
  if(!resp.ok) throw new Error(data.error||"Request failed");
  return data;
}
function setResult(obj){document.getElementById("result").textContent = JSON.stringify(obj,null,2);}
async function refreshLogs(){
  const resp = await fetch("/api/logs"); const data = await resp.json();
  const logsEl = document.getElementById("logs"); logsEl.innerHTML="";
  (data.logs||[]).slice().reverse().forEach(row=>{
    const div = document.createElement("div"); div.className="log-row";
    const left = document.createElement("div"); left.textContent = row.ts;
    const right = document.createElement("div"); right.textContent = JSON.stringify(row.result);
    div.appendChild(left); div.appendChild(right); logsEl.appendChild(div);
  });
}
document.getElementById("sendForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const template = document.getElementById("templateSelect").value || null;
  const destination = document.getElementById("destination").value.trim();
  const protocol = document.getElementById("protocol").value;
  const port = document.getElementById("port").value;
  const timeout_ms = document.getElementById("timeout_ms").value;
  const retries = document.getElementById("retries").value;
  let headers = document.getElementById("headers").value.trim();
  let auth = document.getElementById("auth").value.trim();
  let payload = document.getElementById("payload").value;
  try{ headers = headers ? JSON.parse(headers) : undefined; }catch{ alert("Headers must be JSON"); return; }
  try{ auth = auth ? JSON.parse(auth) : undefined; }catch{ alert("Auth must be JSON"); return; }
  const body = { template };
  if(destination) body.destination = destination;
  if(protocol) body.protocol = protocol;
  if(port) body.port = parseInt(port,10);
  if(timeout_ms) body.timeout_ms = parseInt(timeout_ms,10);
  if(retries) body.retries = parseInt(retries,10);
  if(payload) body.payload = payload;
  if(headers !== undefined) body.headers = headers;
  if(auth !== undefined) body.auth = auth;
  setResult({status:"sending..."});
  try{
    const res = await postJSON("/api/send", body);
    setResult(res); await refreshLogs();
  }catch(err){ setResult({ok:false, error: err.message}); }
});
document.getElementById("refreshLogs").addEventListener("click", refreshLogs);
window.addEventListener("load", refreshLogs);
