from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EventPulse — Resilient Webhook Console</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca' }
          }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans antialiased">

  <!-- Header -->
  <header class="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
          <i class="fa-solid fa-bolt text-white text-lg"></i>
        </div>
        <div>
          <span class="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">EventPulse</span>
          <span class="text-xs ml-2 px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 font-mono">v0.1.0</span>
        </div>
      </div>

      <div class="flex items-center space-x-4">
        <div id="healthBadge" class="flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span id="healthText">System Healthy</span>
        </div>
        <a href="/docs" target="_blank" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center space-x-1.5">
          <i class="fa-solid fa-book"></i>
          <span>Swagger API Docs</span>
        </a>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-8">

    <!-- KPI Stats Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
          <span>Total Ingested</span>
          <i class="fa-solid fa-arrow-down text-brand-400"></i>
        </div>
        <div class="mt-2 flex items-baseline">
          <span id="statIngested" class="text-3xl font-extrabold text-white">0</span>
          <span class="ml-2 text-xs text-slate-400">events</span>
        </div>
      </div>

      <div class="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
          <span>Delivered (2xx)</span>
          <i class="fa-solid fa-circle-check text-emerald-400"></i>
        </div>
        <div class="mt-2 flex items-baseline">
          <span id="statSuccess" class="text-3xl font-extrabold text-emerald-400">0</span>
          <span class="ml-2 text-xs text-slate-400">deliveries</span>
        </div>
      </div>

      <div class="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
          <span>Dead Letter Queue</span>
          <i class="fa-solid fa-skull-crossbones text-rose-400"></i>
        </div>
        <div class="mt-2 flex items-baseline">
          <span id="statDlq" class="text-3xl font-extrabold text-rose-400">0</span>
          <span class="ml-2 text-xs text-slate-400">unreplayed</span>
        </div>
      </div>

      <div class="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
          <span>Active Subscribers</span>
          <i class="fa-solid fa-tower-broadcast text-sky-400"></i>
        </div>
        <div class="mt-2 flex items-baseline">
          <span id="statClients" class="text-3xl font-extrabold text-sky-400">0</span>
          <span class="ml-2 text-xs text-slate-400">clients</span>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex border-b border-slate-800 space-x-6 text-sm font-medium">
      <button onclick="switchTab('dlq')" id="tabBtn-dlq" class="pb-3 border-b-2 border-brand-500 text-brand-400 flex items-center space-x-2">
        <i class="fa-solid fa-skull"></i>
        <span>Dead Letter Queue</span>
      </button>
      <button onclick="switchTab('clients')" id="tabBtn-clients" class="pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center space-x-2">
        <i class="fa-solid fa-network-wired"></i>
        <span>Clients & Circuit Breakers</span>
      </button>
      <button onclick="switchTab('test')" id="tabBtn-test" class="pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center space-x-2">
        <i class="fa-solid fa-paper-plane"></i>
        <span>Test Webhook Ingest</span>
      </button>
    </div>

    <!-- TAB 1: Dead Letter Queue -->
    <div id="tabContent-dlq" class="space-y-4">
      <div class="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 class="text-lg font-bold">Failed Webhooks (Dead Letter Queue)</h2>
          <p class="text-xs text-slate-400">Events that failed 5 retries. Can be inspected and replayed individually or staggered.</p>
        </div>
        <div class="flex items-center space-x-3">
          <button onclick="openBulkReplayModal()" class="px-3.5 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs font-medium transition flex items-center space-x-2 shadow-sm">
            <i class="fa-solid fa-rotate"></i>
            <span>Staggered Bulk Replay</span>
          </button>
          <button onclick="loadDLQ()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition">
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>
        </div>
      </div>

      <div class="border border-slate-800 rounded-2xl bg-slate-900/30 overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900 border-b border-slate-800 text-slate-400 uppercase font-semibold">
              <tr>
                <th class="px-4 py-3">Event ID / Type</th>
                <th class="px-4 py-3">Failure Reason</th>
                <th class="px-4 py-3">Failed At</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody id="dlqTableBody" class="divide-y divide-slate-800/60 font-mono">
              <tr>
                <td colspan="5" class="px-4 py-8 text-center text-slate-500">Loading dead letter events...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2: Clients & Circuit Breakers -->
    <div id="tabContent-clients" class="space-y-4 hidden">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-bold">Registered Webhook Clients</h2>
          <p class="text-xs text-slate-400">Monitors recipient endpoints, subscription patterns, and real-time Circuit Breaker states.</p>
        </div>
        <button onclick="loadClients()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition">
          <i class="fa-solid fa-arrows-rotate"></i>
        </button>
      </div>

      <div id="clientsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- TAB 3: Test Webhook Ingest -->
    <div id="tabContent-test" class="space-y-4 hidden">
      <div class="max-w-2xl bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div>
          <h2 class="text-lg font-bold">Fire a Test Webhook</h2>
          <p class="text-xs text-slate-400">Test ingestion idempotency, HMAC signing, and Celery dispatch directly.</p>
        </div>

        <form id="ingestForm" onsubmit="handleTestIngest(event)" class="space-y-4 text-xs">
          <div>
            <label class="block font-semibold mb-1 text-slate-300">Event ID (Idempotency Key - Optional)</label>
            <input type="text" id="inputEventId" placeholder="Leave empty for auto-generated UUID" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500 font-mono">
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block font-semibold mb-1 text-slate-300">Event Type</label>
              <input type="text" id="inputEventType" value="payment.success" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500 font-mono">
            </div>
            <div>
              <label class="block font-semibold mb-1 text-slate-300">Sequence ID</label>
              <input type="number" id="inputSeqId" value="1" required class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500 font-mono">
            </div>
          </div>

          <div>
            <label class="block font-semibold mb-1 text-slate-300">JSON Payload</label>
            <textarea id="inputPayload" rows="4" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500 font-mono">{
  "customer_id": "cust_8821",
  "amount": 4999,
  "currency": "INR",
  "status": "COMPLETED"
}</textarea>
          </div>

          <button type="submit" class="px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-semibold transition flex items-center space-x-2">
            <i class="fa-solid fa-paper-plane"></i>
            <span>Ingest Event</span>
          </button>
        </form>

        <div id="ingestResult" class="hidden rounded-xl p-4 border text-xs font-mono"></div>
      </div>
    </div>

  </main>

  <!-- Modal: Bulk Replay -->
  <div id="bulkReplayModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="font-bold text-base">Staggered Bulk Replay</h3>
        <button onclick="closeBulkReplayModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <p class="text-xs text-slate-400">
        Replays all un-replayed DLQ events distributed evenly across the time window to avoid overwhelming recovering external servers.
      </p>
      <div>
        <label class="block font-medium text-xs mb-1 text-slate-300">Spread Window (Seconds)</label>
        <input type="number" id="spreadSeconds" value="60" min="5" max="600" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500 font-mono">
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button onclick="closeBulkReplayModal()" class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs">Cancel</button>
        <button onclick="executeBulkReplay()" class="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-xs font-semibold">Start Staggered Replay</button>
      </div>
    </div>
  </div>

  <script>
    const ADMIN_KEY = "eventpulse_admin_secret_token";
    const HEADERS = { "X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json" };

    function switchTab(tabId) {
      ['dlq', 'clients', 'test'].forEach(t => {
        document.getElementById(`tabContent-${t}`).classList.add('hidden');
        document.getElementById(`tabBtn-${t}`).className = 'pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center space-x-2';
      });
      document.getElementById(`tabContent-${tabId}`).classList.remove('hidden');
      document.getElementById(`tabBtn-${tabId}`).className = 'pb-3 border-b-2 border-brand-500 text-brand-400 flex items-center space-x-2 font-semibold';
      if (tabId === 'dlq') loadDLQ();
      if (tabId === 'clients') loadClients();
    }

    async function loadStats() {
      try {
        const metricsRes = await fetch('/metrics');
        const text = await metricsRes.text();

        let ingested = 0, success = 0, dlq = 0;
        text.split('\\n').forEach(line => {
          if (line.startsWith('eventpulse_events_ingested_total{')) {
            const val = parseInt(line.split(' ')[1] || '0');
            ingested += val;
          }
          if (line.startsWith('eventpulse_deliveries_success_total{')) {
            const val = parseInt(line.split(' ')[1] || '0');
            success += val;
          }
          if (line.startsWith('eventpulse_unreplayed_dlq_gauge ')) {
            dlq = parseInt(line.split(' ')[1] || '0');
          }
        });

        document.getElementById('statIngested').innerText = ingested;
        document.getElementById('statSuccess').innerText = success;
        document.getElementById('statDlq').innerText = dlq;

        const clientsRes = await fetch('/api/v1/clients', { headers: HEADERS });
        if (clientsRes.ok) {
          const clients = await clientsRes.json();
          document.getElementById('statClients').innerText = clients.length;
        }
      } catch (err) {
        console.error('Failed to load stats', err);
      }
    }

    async function loadDLQ() {
      const tbody = document.getElementById('dlqTableBody');
      try {
        const res = await fetch('/api/v1/admin/dlq?limit=50', { headers: HEADERS });
        const items = await res.json();
        if (items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500">No events currently in Dead Letter Queue (All Healthy! 🎉)</td></tr>';
          return;
        }

        tbody.innerHTML = items.map(item => `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="px-4 py-3">
              <div class="font-bold text-slate-200">${item.event_type}</div>
              <div class="text-[10px] text-slate-500">${item.webhook_event_id}</div>
            </td>
            <td class="px-4 py-3 max-w-xs truncate text-rose-300 text-[11px]" title="${item.failure_reason}">
              ${item.failure_reason}
            </td>
            <td class="px-4 py-3 text-slate-400 text-[11px]">
              ${new Date(item.failed_at).toLocaleTimeString()}
            </td>
            <td class="px-4 py-3">
              ${item.replayed
                ? '<span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">Replayed</span>'
                : '<span class="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px]">Dead Letter</span>'}
            </td>
            <td class="px-4 py-3 text-right">
              ${item.replayed ? '' : `
                <button onclick="replaySingle('${item.id}')" class="px-2.5 py-1 rounded bg-brand-600/30 hover:bg-brand-600 text-brand-300 hover:text-white transition text-[11px]">
                  Replay
                </button>
              `}
            </td>
          </tr>
        `).join('');
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="px-4 py-4 text-center text-rose-400">Failed to load DLQ: ${err.message}</td></tr>`;
      }
    }

    async function replaySingle(dlqId) {
      try {
        const res = await fetch(`/api/v1/admin/dlq/${dlqId}/replay`, { method: 'POST', headers: HEADERS });
        if (res.ok) {
          loadDLQ();
          loadStats();
        } else {
          alert('Failed to replay event');
        }
      } catch (err) {
        alert(err.message);
      }
    }

    function openBulkReplayModal() { document.getElementById('bulkReplayModal').classList.remove('hidden'); }
    function closeBulkReplayModal() { document.getElementById('bulkReplayModal').classList.add('hidden'); }

    async function executeBulkReplay() {
      const spread = parseFloat(document.getElementById('spreadSeconds').value) || 60;
      closeBulkReplayModal();
      try {
        const res = await fetch('/api/v1/admin/dlq/bulk-replay', {
          method: 'POST',
          headers: HEADERS,
          body: JSON.stringify({ spread_window_seconds: spread })
        });
        const data = await res.json();
        alert(data.message);
        loadDLQ();
        loadStats();
      } catch (err) {
        alert('Bulk replay error: ' + err.message);
      }
    }

    async function loadClients() {
      const grid = document.getElementById('clientsGrid');
      try {
        const res = await fetch('/api/v1/clients', { headers: HEADERS });
        const clients = await res.json();
        grid.innerHTML = clients.map(c => `
          <div class="border border-slate-800 rounded-2xl p-5 bg-slate-900/40 space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-sm truncate" title="${c.name}">${c.name}</h3>
              ${c.state === 'ACTIVE'
                ? '<span class="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold">ACTIVE</span>'
                : '<span class="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-semibold">PAUSED</span>'}
            </div>
            <div class="text-[11px] font-mono text-slate-400 truncate" title="${c.endpoint_url}">${c.endpoint_url}</div>
            <div class="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/80">
              <span>Failures: <b class="${c.consecutive_failures > 0 ? 'text-rose-400' : 'text-slate-300'}">${c.consecutive_failures}</b></span>
              ${c.state === 'PAUSED' ? `
                <button onclick="resumeClient('${c.id}')" class="px-2.5 py-1 rounded bg-emerald-600/30 hover:bg-emerald-600 text-emerald-300 hover:text-white transition text-[10px]">
                  Resume
                </button>
              ` : ''}
            </div>
            <div class="text-[10px] text-slate-500">
              Subs: ${c.subscriptions.map(s => `<code class="bg-slate-950 px-1 py-0.5 rounded border border-slate-800">${s.event_type}</code>`).join(' ')}
            </div>
          </div>
        `).join('');
      } catch (err) {
        grid.innerHTML = `<div class="text-rose-400 text-xs">Error: ${err.message}</div>`;
      }
    }

    async function resumeClient(id) {
      await fetch(`/api/v1/clients/${id}/resume`, { method: 'POST', headers: HEADERS });
      loadClients();
    }

    async function handleTestIngest(e) {
      e.preventDefault();
      const event_id = document.getElementById('inputEventId').value.trim() || undefined;
      const event_type = document.getElementById('inputEventType').value.trim();
      const sequence_id = parseInt(document.getElementById('inputSeqId').value) || 1;
      let payload;
      try {
        payload = JSON.parse(document.getElementById('inputPayload').value);
      } catch (err) {
        alert('Invalid JSON in payload field');
        return;
      }

      const resDiv = document.getElementById('ingestResult');
      resDiv.classList.remove('hidden');

      try {
        const res = await fetch('/api/v1/webhooks/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ event_id, event_type, sequence_id, payload })
        });
        const data = await res.json();
        if (res.status === 202) {
          resDiv.className = 'rounded-xl p-4 border text-xs font-mono bg-emerald-500/10 border-emerald-500/30 text-emerald-300';
          resDiv.innerHTML = `<b>Status: 202 Accepted (Queued)</b><br>Event ID: ${data.event_id}<br>${data.message}`;
        } else {
          resDiv.className = 'rounded-xl p-4 border text-xs font-mono bg-amber-500/10 border-amber-500/30 text-amber-300';
          resDiv.innerHTML = `<b>Status: 200 OK (Duplicate Deduplication)</b><br>Event ID: ${data.event_id}<br>${data.message}`;
        }
        loadStats();
      } catch (err) {
        resDiv.className = 'rounded-xl p-4 border text-xs font-mono bg-rose-500/10 border-rose-500/30 text-rose-300';
        resDiv.innerHTML = `Error: ${err.message}`;
      }
    }

    // Auto-refresh stats every 5s
    loadStats();
    loadDLQ();
    setInterval(loadStats, 5000);
  </script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"], summary="EventPulse Real-Time Web Console")
async def get_dashboard():
    """Serves the interactive single-page dashboard console."""
    return HTMLResponse(content=DASHBOARD_HTML)
