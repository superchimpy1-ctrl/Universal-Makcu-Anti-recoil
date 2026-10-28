# 2PC Universal Makcu Recoil Control

A browser-based control panel for the [MAKCU](https://github.com/MAKCU) hardware mouse passthrough device. Control your mouse's movement in real-time from any device on your local network—no more needing to be at the physical machine running the hardware.

![Makcu Multitool](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **🌐 Remote Web UI** — Access the control panel from a browser on any PC on your local network (`http://<host-ip>:5000`).
- **🎛️ Manual Mode** — Continuous precise movement while holding Left Mouse Button. Adjustable X/Y strength (down to 2 decimals) and tick interval. Save and load profiles.
- **📼 Path Player** — Record organic mouse paths to JSON with variable speed, then replay them with adjustable speed multipliers. Includes a real-time path preview on a black grid canvas.
- **🎯 Auto-Align Start** — Automatically warps the cursor to the exact pixel where the recording started, eliminating drift.
- **📏 Scale Correction** — Built-in multiplier to fix DPI/display scaling differences between the recorder PC and the playback PC.
- **⌨️ Hardware Triggers** — Left Click plays the active mode. MB4 (side button) toggles the program enabled/disabled instantly.
- **🖤 Liquid Glass UI** — Dark monochrome interface with rounded sliders, glass panels, and a live path visualizer.

## 📁 Project Structure

```
2PC Universal Makcu Recoil Control/
├── makcu_multitool-1-8-0.py       # Main Flask app + hardware control
├── recorder.py           # Path recorder (F1 to start/stop)
├── requirements.txt
├── CLAUDE.md
├── README.md
├── LICENSE
├── profiles/             # Saved manual-mode profiles (auto-created)
└── *.json                # Recorded path files
```

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/makcu-multitool.git
   cd makcu-multitool
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Connect your MAKCU** to the PC that will run the script. Confirm it's detected (usually `COM3` on Windows).

## 🎮 Usage

### Starting the Control Panel

```bash
python makcu_multitool-1-8-0.py
```

The console will print the local IP address:
```
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.0.xxx:5000
 * For example mine was http://192.168.0.120:5000
```

Open the second URL (your LAN IP) in a browser on **any PC** on the same network.

> **⚠️ Windows Firewall:** If the second PC can't connect, open PowerShell as Administrator and run:
> ```powershell
> New-NetFirewallRule -DisplayName "Makcu Web" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
> ```

### Recording a Path

1. Run `python recorder.py`.
2. Hover the mouse at the start of the path you want to trace.
3. Press **F1** to start recording.
4. Trace the path with your mouse. Move slower where you want the playback to be slower.
5. Press **F1** again to save. A `recorded_path.json` file will be created.

### Playing a Path

1. In the web UI, go to the **Path Player** tab.
2. Select your recorded JSON from the list. The path will preview on the black grid canvas.
3. Adjust the **Speed Multiplier** and **Path Scale** if needed.
4. Hold **Left Mouse Button** to play. Release to pause. Click again to resume from the beginning.

### Manual Control

1. Go to the **Manual Control** tab.
2. Adjust X Strength, Y Strength, and Tick Interval (type or drag).
3. Save your configuration as a named profile for one-click switching later.

### MB4 Toggle

Press the side mouse button (**MB4**) at any time to disable or re-enable the program. The status dot at the top of the UI shows the current state.

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| **"Connected" but UI shows nothing happening** | Verify MB4 status dot is green and you're holding Left Mouse Button. |
| **First PC can't reach the site** | Check Windows Firewall (see above), confirm both PCs are on the same Wi-Fi/subnet, and try pinging the host IP. |
| **Path is off / drifts** | Re-record with the latest `recorder.py` (it now saves the start position). Adjust the **Path Scale** slider. |
| **"Circular import" error** | Your script is named `makcu.py`. Rename it to `makcu_web.py`. |
| **MB4 doesn't toggle** | Change `MouseButton.MOUSE4` to `MouseButton.MOUSE5` in `on_button_event`. |

## 🧠 How It Works

The MAKCU device acts as a hardware mouse passthrough. The `pymakcu` library exposes `move(dx, dy)` for relative movement. Two background threads run constantly:
- One reads manual slider values when the mode is `manual`.
- The other reads the JSON array when the mode is `path`, calculating per-tick delays using `time.perf_counter()` for sub-millisecond precision.

The frontend is embedded directly in `makcu_web.py` as an HTML string—no build step, no bundler, no Node.js. Just open the URL and it works.

## 📜 License

MIT — see LICENSE for details.

## 🙏 Credits

- Built on the [MAKCU](https://github.com/MAKCU) hardware platform.
- Uses `pymakcu` for hardware communication.
- Uses `pynput` and `keyboard` for the recorder
