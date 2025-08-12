# PTPPing – Network-wide Audio Latency Probe  
> “Zoom doesn’t lie, but your switches might.”

---

## What is it?

PTPPing is a passive-measurement toolkit that pinpoints **how much each network hop adds to real-time audio latency**.  
Instead of synthetic ICMP pings, we ship **actual audio** (short 440 Hz bursts) through your production VLANs, then time-stamp every copy against the **PTP grandmaster clock**.  
The result is a per-switch, per-second heat-map of “audio delay budget spent” that shows up directly in Grafana.

---

## How it works

1. **Generation**  
   A VLC instance on every workstation plays *silence* while the built-in `audiobargraph_a` filter injects a deterministic 440 Hz tone burst every 100 ms.  
   → Bursts are **phase-locked** to the local PTP clock.

2. **Capture**  
   ALSA loopback devices on the same hosts grab the audio back.  
   → Each burst is FFT-analysed; its phase offset vs. the PTP epoch gives one **one-way latency sample**.

3. **Storage**  
   Samples are streamed into **InfluxDB** (`latency_ms,switch=sw03 host=ws42 …`).

4. **Visualisation**  
   A **Grafana** dashboard maps the data by:
   - switch port  
   - time-of-day  
   - active Zoom/Teams call (optional webhook tag)

---

## Quick-start

```bash
# 1. Clone
git clone https://github.com/makalin/ptpping.git
cd ptpping

# 2. Install deps
sudo apt install vlc influxdb-client grafana
pip install -r requirements.txt

# 3. Configure
cp config.toml.example config.toml
$EDITOR config.toml   # set PTP_IFACE, INFLUX_URL, GRAFANA_API_KEY

# 4. Run
sudo ./ptpping.py --role generator  # on every workstation
sudo ./ptpping.py --role capture    # on every workstation
sudo ./ptpping.py --role dashboard  # once in the NOC
```

---

## Repo layout

```
├── ptpping.py              # Main orchestrator
├── generator/              # VLC wrapper + silence.wav
├── capture/                # ALSA loopback + phase detector
├── config.toml.example
├── grafana/
│   ├── dashboards/
│   └── provisioning/
├── systemd/
│   ├── ptpping-generator.service
│   ├── ptpping-capture.service
└── README.md
```

---

## Grafana preview

![heatmap](docs/heatmap.png)  
*Dark squares = 3–4 ms extra latency on switch “TOR-03” during 10 a.m. stand-up.*

---

## FAQ

**Q. Will users hear the tone?**  
No. VLC plays digital silence; the tone only exists in the loopback buffer.

**Q. 440 Hz is musical. Can I change it?**  
Yes. Edit `generator/audiobargraph_a.lua` – any integer divisor of 48 kHz works.

**Q. Does this require PTP hardware?**  
Only the grandmaster needs hardware timestamping. End-stations can run `linuxptp` in software mode; accuracy is still sub-millisecond.

---

## Contributing

Pull requests welcome.  
Please run `tox` before submitting; it lints Python, Lua and checks Grafana JSON against the schema.

---

## License

MIT © 2024 PTPing Authors
