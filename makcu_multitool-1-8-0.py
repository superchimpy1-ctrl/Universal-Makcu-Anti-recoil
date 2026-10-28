import time
import threading
import json
import os
from flask import Flask, render_template_string, request, jsonify
from pymakcu import create_controller, MouseButton
import ctypes # Used for moving mouse to absolute coordinates

# ================= Makcu Connection =================
print("Connecting to Makcu...")
try:
    makcu = create_controller()
except Exception as e:
    print(f"Connection failed: {e}")
    raise SystemExit(1)
if not makcu.is_connected():
    print("Not connected.")
    raise SystemExit(1)
print("Connected.")

# ================= Global State =================
state = {
    "x_strength": 5.0,
    "y_strength": 0.0,
    "tick_interval": 0.02,
    "speed": 1.0,
    "path_data": [],        # Just the points
    "start_x": 0,
    "start_y": 0,
    "path_index": 0,
    "scale_mult": 1.0,      # Multiplier to fix DPI/screen size differences
    
    "lmb_held": False,
    "enabled": True,
    "current_mode": "manual", 
    "running": True,
}

# Windows API to set absolute mouse position (Teleport to Start)
def set_cursor_pos(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))

# ================= Background Loops =================
def manual_loop():
    while state["running"]:
        if state["current_mode"] == "manual" and state["enabled"] and state["lmb_held"]:
            try:
                makcu.move(state["x_strength"], state["y_strength"])
            except Exception:
                pass
        time.sleep(state["tick_interval"])

def path_loop():
    while state["running"]:
        if state["current_mode"] == "path" and state["enabled"] and state["lmb_held"] and state["path_data"]:
            if state["path_index"] >= len(state["path_data"]):
                state["path_index"] = 0 
                
            point = state["path_data"][state["path_index"]]
            
            # Apply the scale multiplier to fix resolution stretching
            dx = point["dx"] * state["scale_mult"]
            dy = point["dy"] * state["scale_mult"]
            
            try:
                makcu.move(dx, dy)
            except Exception:
                pass
                
            state["path_index"] += 1
            original_dt = point.get("dt", 0.01)
            delay = original_dt / state["speed"]
            
            start_wait = time.perf_counter()
            while time.perf_counter() - start_wait < delay and state["running"]:
                if not state["lmb_held"] or not state["enabled"] or state["current_mode"] != "path":
                    break
                time.sleep(0.0005)
        else:
            time.sleep(0.01)

# ================= Button Callback =================
def on_button_event(button: MouseButton, is_pressed: bool):
    if button == MouseButton.LEFT:
        if is_pressed:
            state["path_index"] = 0
            # If we are in path mode and have data, teleport to the recorded start position!
            if state["current_mode"] == "path" and state["path_data"]:
                set_cursor_pos(state["start_x"], state["start_y"])
        state["lmb_held"] = is_pressed
    elif button == MouseButton.MOUSE4 and is_pressed:
        state["enabled"] = not state["enabled"]

makcu.set_button_callback(on_button_event)
threading.Thread(target=manual_loop, daemon=True).start()
threading.Thread(target=path_loop, daemon=True).start()

# ================= Flask App =================
app = Flask(__name__)
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")
PATH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(PROFILE_DIR, exist_ok=True)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Makcu Control</title>
<style>
  :root {
    --bg: #050505; --glass: #101010; --glass-2: #181818;
    --stroke: #2c2c2c; --text: #f2f2f2; --muted: #8a8a8a;
    --accent: #d9d9d9; --danger: #ff4d5e; --track: #242424;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
  body {
    background: var(--bg); color: var(--text);
    display: flex; justify-content: center; align-items: center;
    min-height: 100vh; padding: 20px;
  }
  .main-container {
    display: flex; gap: 20px; align-items: stretch; justify-content: center; width: 100%; max-width: 850px;
  }
  .glass-panel {
    background: var(--glass); border: 1px solid var(--stroke);
    border-radius: 16px; padding: 24px; flex: 0 0 480px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.05);
    backdrop-filter: blur(10px); display: flex; flex-direction: column;
  }
  .preview-panel {
    background: var(--glass); border: 1px solid var(--stroke);
    border-radius: 16px; padding: 16px; flex: 1;
    box-shadow: 0 8px 32px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.05);
    display: flex; flex-direction: column;
  }
  h1 { font-size: 20px; font-weight: 600; margin-bottom: 16px; }
  .status-pill {
    background: var(--glass-2); border: 1px solid var(--stroke);
    border-radius: 20px; padding: 10px 16px; display: flex;
    align-items: center; gap: 10px; font-size: 13px; margin-bottom: 20px;
  }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot.on { background: #7dffa8; box-shadow: 0 0 8px #7dffa8; }
  .dot.off { background: var(--danger); box-shadow: 0 0 8px var(--danger); }
  
  .tabs { display: flex; gap: 8px; margin-bottom: 20px; }
  .tab-btn {
    flex: 1; background: var(--glass-2); border: 1px solid var(--stroke);
    color: var(--muted); padding: 10px; border-radius: 12px;
    cursor: pointer; font-size: 13px; font-weight: 600; transition: 0.2s;
  }
  .tab-btn.active { background: var(--track); color: var(--text); border-color: var(--accent); }
  
  .tab-content { display: none; flex: 1; }
  .tab-content.active { display: block; }
  
  .slider-group { margin-bottom: 16px; }
  .slider-header { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-bottom: 8px; align-items: center;}
  
  .num-input {
    background: var(--glass-2); border: 1px solid var(--stroke);
    color: var(--text); font-weight: bold; font-size: 12px;
    padding: 4px 8px; border-radius: 6px; width: 70px; text-align: right;
    outline: none; transition: border 0.2s;
  }
  .num-input:focus { border-color: var(--accent); }

  input[type=range] { -webkit-appearance: none; width: 100%; background: transparent; }
  input[type=range]::-webkit-slider-runnable-track { height: 8px; background: var(--track); border-radius: 4px; }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; height: 20px; width: 20px;
    border-radius: 50%; background: #f5f5f5; border: 1px solid var(--accent);
    margin-top: -6px; box-shadow: 0 0 8px rgba(255,255,255,0.2); cursor: pointer;
  }
  
  .list-container { max-height: 150px; overflow-y: auto; margin-bottom: 16px; }
  .list-item {
    display: flex; justify-content: space-between; align-items: center;
    background: var(--glass-2); border: 1px solid var(--stroke);
    padding: 10px 12px; border-radius: 10px; margin-bottom: 6px; font-size: 13px;
  }
  .btn {
    background: var(--glass-2); border: 1px solid var(--stroke);
    color: var(--text); padding: 6px 12px; border-radius: 8px;
    cursor: pointer; font-size: 12px; font-weight: 600; transition: 0.2s;
  }
  .btn:hover { background: var(--track); border-color: var(--accent); }
  .btn-accent { background: var(--accent); color: #000; border: none; }
  .btn-accent:hover { background: #fff; }
  .btn-danger { color: var(--danger); border-color: transparent; background: transparent; }
  .btn-danger:hover { background: #2a1416; }
  
  .input-row { display: flex; gap: 8px; margin-top: 10px; }
  .input-row input {
    flex: 1; background: var(--glass-2); border: 1px solid var(--stroke);
    color: var(--text); padding: 10px; border-radius: 10px; font-size: 13px; outline: none;
  }
  .input-row input:focus { border-color: var(--accent); }
  
  .info-text { font-size: 11px; color: var(--muted); text-align: center; margin-top: 16px; }
  
  #pathCanvas {
    width: 100%; height: 100%; background: #000; border-radius: 8px;
    flex: 1; border: 1px solid var(--stroke); min-height: 500px;
  }
  .preview-title {
    font-size: 12px; color: var(--muted); font-weight: bold; margin-bottom: 12px; text-transform: uppercase;
  }
</style>
</head>
<body>

<div class="main-container">
  <div class="glass-panel">
    <h1>Makcu Control</h1>
    
    <div class="status-pill">
      <div class="dot" id="statusDot"></div>
      <span id="statusText">Program: ENABLED (MB4 toggles)</span>
    </div>

    <div class="tabs">
      <button class="tab-btn active" id="btn-tab-manual" onclick="switchTab('manual')">Manual Control</button>
      <button class="tab-btn" id="btn-tab-path" onclick="switchTab('path')">Path Player</button>
    </div>

    <div id="tab-manual" class="tab-content active">
      <div class="slider-group">
        <div class="slider-header">
          <span>X Strength</span>
          <input type="number" class="num-input" id="input-x_strength" step="0.01" value="5.00">
        </div>
        <input type="range" id="x_strength" min="-50" max="50" step="0.01" value="5.00">
      </div>
      
      <div class="slider-group">
        <div class="slider-header">
          <span>Y Strength</span>
          <input type="number" class="num-input" id="input-y_strength" step="0.01" value="0.00">
        </div>
        <input type="range" id="y_strength" min="-50" max="50" step="0.01" value="0.00">
      </div>
      
      <div class="slider-group">
        <div class="slider-header">
          <span>Tick Interval (s)</span>
          <input type="number" class="num-input" id="input-tick_interval" step="0.01" value="0.02">
        </div>
        <input type="range" id="tick_interval" min="0.01" max="0.1" step="0.01" value="0.02">
      </div>

      <div style="font-size: 12px; color: var(--muted); font-weight: bold; margin: 20px 0 10px 0;">PROFILES</div>
      <div class="list-container" id="profileList"></div>
      
      <div class="input-row">
        <input type="text" id="profileName" placeholder="New profile name...">
        <button class="btn btn-accent" onclick="saveProfile()">Save</button>
      </div>
    </div>

    <div id="tab-path" class="tab-content">
      <div class="slider-group">
        <div class="slider-header"><span>Speed Multiplier</span><span class="slider-val" id="val-speed">1.0</span></div>
        <input type="range" id="speed" min="0.1" max="3.0" step="0.1" value="1.0">
      </div>

      <div class="slider-group">
        <div class="slider-header">
          <span>Path Scale (Fix Offset)</span>
          <input type="number" class="num-input" id="input-scale_mult" step="0.05" value="1.00">
        </div>
        <input type="range" id="scale_mult" min="0.5" max="2.0" step="0.05" value="1.00">
      </div>

      <div style="font-size: 12px; color: var(--muted); font-weight: bold; margin: 20px 0 10px 0;">SELECT PATH FILE</div>
      <div class="list-container" id="pathList"></div>

      <div class="info-text">Loaded: <span id="loadedPath" style="color: var(--accent);">None</span></div>
      <div class="info-text" style="margin-top: 8px;">Hold LMB to play path. Release to pause.</div>
    </div>
  </div>

  <div class="preview-panel">
    <div class="preview-title">Path Preview</div>
    <canvas id="pathCanvas"></canvas>
  </div>
</div>

<script>
  async function switchTab(tab) {
    await fetch('/api/mode', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mode: tab})
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('btn-tab-' + tab).classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
  }

  async function fetchState() {
    const res = await fetch('/api/state');
    const data = await res.json();
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (data.enabled) {
      dot.className = 'dot on'; text.innerText = 'Program: ENABLED (MB4 toggles)';
    } else {
      dot.className = 'dot off'; text.innerText = 'Program: DISABLED (MB4 toggles)';
    }
  }
  setInterval(fetchState, 500);

  async function updateBackend(key, val) {
    await fetch('/api/set', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({key: key, value: val})
    });
  }

  function bindControl(sliderId, inputId) {
    const slider = document.getElementById(sliderId);
    const input = document.getElementById(inputId);
    slider.addEventListener('input', () => {
      let val = parseFloat(slider.value);
      input.value = val.toFixed(2);
      updateBackend(sliderId, val);
    });
    input.addEventListener('change', () => {
      let val = parseFloat(input.value);
      if (isNaN(val)) val = 0;
      val = Math.max(parseFloat(slider.min), Math.min(parseFloat(slider.max), val));
      input.value = val.toFixed(2);
      slider.value = val;
      updateBackend(sliderId, val);
    });
  }

  bindControl('x_strength', 'input-x_strength');
  bindControl('y_strength', 'input-y_strength');
  bindControl('tick_interval', 'input-tick_interval');
  bindControl('scale_mult', 'input-scale_mult'); // Added path scale
  
  const speedSlider = document.getElementById('speed');
  const speedVal = document.getElementById('val-speed');
  speedSlider.addEventListener('input', () => {
    speedVal.innerText = parseFloat(speedSlider.value).toFixed(1);
    updateBackend('speed', parseFloat(speedSlider.value));
  });

  async function loadProfiles() {
    const res = await fetch('/api/profiles');
    const profiles = await res.json();
    const list = document.getElementById('profileList');
    list.innerHTML = '';
    profiles.forEach(p => {
      const div = document.createElement('div');
      div.className = 'list-item';
      div.innerHTML = `<span>${p}</span>
        <div>
          <button class="btn" onclick="applyProfile('${p}')">Load</button>
          <button class="btn btn-danger" onclick="deleteProfile('${p}')">✕</button>
        </div>`;
      list.appendChild(div);
    });
  }
  loadProfiles();

  async function saveProfile() {
    const name = document.getElementById('profileName').value.trim();
    if (!name) return alert('Enter a name');
    await fetch('/api/profiles/' + name, {method: 'POST'});
    document.getElementById('profileName').value = '';
    loadProfiles();
  }

  async function applyProfile(name) {
    const res = await fetch('/api/profiles/' + name, {method: 'PUT'});
    const data = await res.json();
    if (data.ok) {
      ['x_strength', 'y_strength', 'tick_interval'].forEach(key => {
        let val = data.settings[key];
        document.getElementById(key).value = val;
        document.getElementById('input-' + key).value = parseFloat(val).toFixed(2);
      });
    }
  }

  async function deleteProfile(name) {
    if (!confirm('Delete profile ' + name + '?')) return;
    await fetch('/api/profiles/' + name, {method: 'DELETE'});
    loadProfiles();
  }

  const canvas = document.getElementById('pathCanvas');
  const ctx = canvas.getContext('2d');

  function drawGrid() {
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#222222";
    ctx.lineWidth = 1;
    const gridSize = 30;
    for (let x = 0; x <= canvas.width; x += gridSize) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += gridSize) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }
  }

  function drawPath(pathData) {
    drawGrid();
    if (!pathData || pathData.length === 0) return;

    let minX = 0, maxX = 0, minY = 0, maxY = 0;
    let currX = 0, currY = 0;
    const absolutePoints = [];
    
    for (let p of pathData) {
      currX += p.dx;
      currY += p.dy;
      absolutePoints.push({x: currX, y: currY});
      if (currX < minX) minX = currX;
      if (currX > maxX) maxX = currX;
      if (currY < minY) minY = currY;
      if (currY > maxY) maxY = currY;
    }

    const padding = 40;
    const width = maxX - minX;
    const height = maxY - minY;
    const scaleX = (canvas.width - padding * 2) / (width || 1);
    const scaleY = (canvas.height - padding * 2) / (height || 1);
    const scale = Math.min(scaleX, scaleY);

    const offsetX = (canvas.width - width * scale) / 2 - minX * scale;
    const offsetY = (canvas.height - height * scale) / 2 - minY * scale;

    ctx.beginPath();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    for (let i = 0; i < absolutePoints.length; i++) {
      const px = absolutePoints[i].x * scale + offsetX;
      const py = absolutePoints[i].y * scale + offsetY;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }

  function resizeCanvas() {
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    drawGrid();
    fetch('/api/path_data')
      .then(r => r.json())
      .then(data => { if (data.path_data) drawPath(data.path_data); });
  }
  
  window.addEventListener('resize', resizeCanvas);
  setTimeout(() => { resizeCanvas(); drawGrid(); }, 100);

  async function loadPaths() {
    const res = await fetch('/api/paths');
    const paths = await res.json();
    const list = document.getElementById('pathList');
    list.innerHTML = '';
    paths.forEach(p => {
      const div = document.createElement('div');
      div.className = 'list-item';
      div.innerHTML = `<span>${p.replace('.json', '')}</span>
        <button class="btn" onclick="selectPath('${p}')">Select</button>`;
      list.appendChild(div);
    });
  }
  loadPaths();

  async function selectPath(filename) {
    await fetch('/api/path/' + filename, {method: 'POST'});
    document.getElementById('loadedPath').innerText = filename.replace('.json', '');
    const res = await fetch('/api/path_data');
    const data = await res.json();
    drawPath(data.path_data);
  }
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/state")
def api_state():
    return jsonify({"enabled": state["enabled"]})

@app.route("/api/set", methods=["POST"])
def api_set():
    data = request.get_json()
    key = data.get("key")
    val = data.get("value")
    if key in state:
        state[key] = val
    return jsonify({"ok": True})

@app.route("/api/mode", methods=["POST"])
def api_mode():
    data = request.get_json()
    state["current_mode"] = data.get("mode", "manual")
    return jsonify({"ok": True})

@app.route("/api/path_data")
def api_path_data():
    return jsonify({"path_data": state["path_data"]})

@app.route("/api/profiles", methods=["GET"])
def api_get_profiles():
    files = [f[:-5] for f in os.listdir(PROFILE_DIR) if f.endswith(".json")]
    return jsonify(sorted(files))

@app.route("/api/profiles/<name>", methods=["POST", "PUT", "DELETE"])
def api_profiles(name):
    safe = "".join(c for c in name if c.isalnum() or c in "-_ ")
    path = os.path.join(PROFILE_DIR, safe + ".json")
    
    if request.method == "POST":
        with open(path, "w") as f:
            json.dump({"x_strength": state["x_strength"], "y_strength": state["y_strength"], "tick_interval": state["tick_interval"]}, f)
        return jsonify({"ok": True})
    elif request.method == "PUT":
        if not os.path.exists(path): return jsonify({"ok": False})
        with open(path) as f: s = json.load(f)
        state["x_strength"] = float(s.get("x_strength", 5.0))
        state["y_strength"] = float(s.get("y_strength", 0.0))
        state["tick_interval"] = float(s.get("tick_interval", 0.02))
        return jsonify({"ok": True, "settings": s})
    elif request.method == "DELETE":
        if os.path.exists(path): os.remove(path)
        return jsonify({"ok": True})

@app.route("/api/paths", methods=["GET"])
def api_get_paths():
    files = [f for f in os.listdir(PATH_DIR) if f.endswith(".json") and f != "profiles"]
    files = [f for f in files if f != "recorded_path.json"]
    if os.path.exists(os.path.join(PATH_DIR, "recorded_path.json")):
        files.insert(0, "recorded_path.json")
    return jsonify(files)

@app.route("/api/path/<filename>", methods=["POST"])
def api_select_path(filename):
    safe = "".join(c for c in filename if c.isalnum() or c in "-_. ")
    path = os.path.join(PATH_DIR, safe)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                
            # Support both old (list) and new (dict) JSON formats
            if isinstance(data, list):
                state["path_data"] = data
                state["start_x"] = 0
                state["start_y"] = 0
            else:
                state["path_data"] = data.get("points", [])
                state["start_x"] = data.get("start_x", 0)
                state["start_y"] = data.get("start_y", 0)
                
            state["path_index"] = 0
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)