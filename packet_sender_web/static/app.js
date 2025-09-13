async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Request failed");
  return data;
}

function setResult(data) {
  const el = document.getElementById("result");
  el.textContent = JSON.stringify(data, null, 2);
}

async function refreshLogs() {
  const resp = await fetch("/api/logs");
  const data = await resp.json();
  const logsEl = document.getElementById("logs");
  logsEl.innerHTML = "";
  (data.logs || []).slice().reverse().forEach((row) => {
    const div = document.createElement("div");
    div.className = "log-row";
    const left = document.createElement("div");
    left.textContent = row.timestamp;
    const right = document.createElement("div");
    right.textContent = `${row.destination}  |  ${JSON.stringify(row.result)}`;
    div.appendChild(left);
    div.appendChild(right);
    logsEl.appendChild(div);
  });
}

document.getElementById("sendForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const destination = document.getElementById("destination").value.trim();
  const payload = document.getElementById("payload").value;
  let headers = document.getElementById("headers").value.trim();
  let auth = document.getElementById("auth").value.trim();

  try {
    headers = headers ? JSON.parse(headers) : {};
  } catch {
    alert("Headers must be valid JSON");
    return;
  }
  try {
    auth = auth ? JSON.parse(auth) : {};
  } catch {
    alert("Auth must be valid JSON");
    return;
  }

  setResult({status: "sending..."});
  try {
    const res = await postJSON("/api/send", { destination, payload, headers, auth });
    setResult(res);
    await refreshLogs();
  } catch (err) {
    setResult({ ok: false, error: err.message });
  }
});

document.getElementById("refreshLogs").addEventListener("click", refreshLogs);
window.addEventListener("load", refreshLogs);
