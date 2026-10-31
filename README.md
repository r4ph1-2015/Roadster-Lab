# Roadster: Thrust Lab

**Roadster: Thrust Lab** is a browser-based, third-person stunt-driving playground inspired by the Tesla Roadster reveal and its rocket-assisted demonstration concept. It is built around experimentation rather than conventional racing: drive, build speed, launch, control the vehicle in the air, try unusual manoeuvres, and see whether you can land cleanly.

This is an independent fan project inspired by the idea and visual spectacle of a rocket-assisted Roadster. It is not an official Tesla product, is not endorsed by Tesla, and does not claim to reproduce Tesla's proprietary systems or undisclosed vehicle controls.

## Experience at a glance

The project is now a single open-world night-time test facility instead of five separate scenarios. Drive between zones, run the experiments, and chain stunts for combo multipliers.

- **Hand-authored Tesla Roadster model:** a GLB car (`tesla_roadster.glb`) with working headlamps and taillamps, replacing the earlier procedural body.
- **WebGPU rendering:** Three.js WebGPU renderer with a custom sky dome (sun, stars, clouds), distant mountains and a neon skyline, image-based lighting that matches the sky, and a post stack of bloom, speed-based chromatic blur, ACES tone mapping, vignette and film grain. Press `V` for the developer bloom panel.
- **Infinite expedition layer:** deterministic terrain chunks stream in every direction outside the authored facility, with no automatic altitude or map-edge respawn.
- **Advanced tuning and pilots:** live speed, thrust, response, steering, stability and wall-grip controls; Standard, Trick and Roadster ZERO pilots use the real landing scorer.
- **Rigid-body vehicle physics:** mass and inertia, per-wheel and chassis contact points, suspension, traction and brake-to-drift handling, solid-obstacle collision, and curved profile surfaces for walls steeper than the height-field allows.
- **Rocket-assisted stunts:** rear, bottom and side thrusters with a fuel reserve, airborne pitch/roll/yaw control, and AUTO landing assist or MANUAL direct control.
- **Wall adhesion:** toggle grip with `G` and hold `Shift` to ride walls and the circular tunnel.
- **Test zones:** Test Straight, Drop Tower, Adhesion Lab, Clearance Range, Kinematics Yard, Gravity Well, Collision Lab, Terrain Sim, Ascent Helix and Orbital Ramp.
- **Objectives and scoring:** light-gate checkpoints, collectible data orbs, hoops, boost pads, smashable crates and barrels, and a combo multiplier for flips, spins and adhesion runs.
- **Feedback:** thruster plume and landing dust particles (7,200-particle pool), a minimap, and telemetry for speed, fuel, G-force, altitude, airtime and jump distance.
- **Desktop and mobile:** keyboard and mouse orbit camera, a virtual joystick with touch thruster buttons, and a responsive HUD.
- **Generated audio:** engine, thruster, tire-slip and landing sounds are synthesized with the Web Audio API. No audio files are needed.

## Technology

- HTML and CSS for the interface and responsive layout
- JavaScript and Three.js (WebGPU build, with TSL post-processing) for rendering and scene geometry
- `GLTFLoader` for the Roadster model
- A custom rigid-body physics integrator for driving, contact, thruster forces and vehicle rotation
- Web Audio API for procedural sound effects

Three.js (v0.186.1) is loaded from a public CDN through an import map, so an internet connection is required. If the locally served Roadster GLB fails to load, the client retries from a public model mirror. A WebGPU-capable browser is recommended. There is no build step or package installation.

## Project structure

```text
thrust-lab-project/
├── index.html           # Page structure, import map, HUD, controls guide and creator links
├── styles.css           # Responsive layout, HUD, desktop UI and mobile touch controls
├── script.js            # Renderer, world zones, vehicle physics, objectives, camera, particles and audio
├── tesla_roadster.glb   # Roadster model
├── app.py               # Flask server for local/legacy development
├── worker/
│   ├── entry.py          # Python Worker and Durable Object WebSocket room service
│   ├── room_protocol.py  # Username, room and pose validation
│   └── test_room_protocol.py # Worker protocol tests
├── wrangler.jsonc        # Workers assets, Durable Object binding and SQLite migration
├── pyproject.toml        # Python Workers development dependencies
├── scripts/              # Cloudflare deployment helper scripts
├── public/               # Generated static asset staging directory for Wrangler
└── README.md             # Project overview and development notes
```

## Deploy multiplayer on Cloudflare

Cloudflare serves the game files at the edge and runs multiplayer rooms in Python Durable Objects over WebSockets. The Mac does not need to accept inbound connections. Workers Free and SQLite-backed Durable Objects have daily quotas; check the current Cloudflare limits before opening a room widely.

Prerequisites: a Cloudflare account, a domain added to that account, Python 3.13+, `uv`, and Node.js (required by Cloudflare's CLI). On a managed computer, ask IT to approve the required developer tools if they are blocked. Do not bypass managed endpoint controls.

Install `uv` using its official installer, then from this project directory:

```bash
uv sync
sh scripts/prepare_cloudflare_assets.sh
uv run pywrangler login
uv run pywrangler dev
```

Open the local Wrangler URL and verify `/health` returns `{"ok":true,...}`. Test a room with two browser windows. Deploy after the local test succeeds:

```bash
uv run pywrangler deploy
```

In Cloudflare, open **Workers & Pages → roadster-thrust-lab → Settings → Domains & Routes → Add → Custom Domain**, then choose a subdomain such as `play.example.com`. Share that HTTPS hostname with players. When game files change, run `sh scripts/prepare_cloudflare_assets.sh` before `pywrangler dev` or `pywrangler deploy`.

The Durable Object uses a SQLite-backed migration, available on Workers Free. If using a custom domain, its DNS zone must be active on the same Cloudflare account. There is no need to point DNS at your Mac, expose port 8000, or run the Flask server publicly.

## Run locally with Flask

For local development only, Python 3.10+ can run the included Flask-SocketIO server:

```bash
uv sync
uv run python app.py
```

Open `http://localhost:8000`. This Flask server is a local-development/legacy reference only; the browser's Cloudflare multiplayer client connects to `/ws`, which is implemented by the Worker/Durable Object. For multiplayer testing, use `uv run pywrangler dev` as described above.

The Cloudflare room supports up to eight players per room. Usernames are room-local and are not accounts. The Durable Object validates pose shape/range and relays poses at up to about 20 updates per second. WebSocket attachments keep player metadata available across Durable Object hibernation. Rooms are coordination state, not persistent player profiles.

## Multiplayer roadmap

The current multiplayer foundation provides usernames, Cloudflare-hosted rooms, join/leave notifications, and remote Roadster rendering. Local vehicle physics and game objectives are still simulated independently in each browser; remote cars do not collide, and scores, pickups, checkpoints, and races are not yet authoritative or shared.

The next version should extract vehicle physics and world collision data into a browser/server-compatible simulation module, then move simulation ticks and shared outcomes to the server. After that, add client prediction and reconciliation, shared race state, reconnect recovery, and latency/disconnect tests. Until server-authoritative simulation is implemented, treat this build as synchronized co-driving rather than competitive or cheat-resistant multiplayer.

## Controls

### Desktop

| Input | Action |
| --- | --- |
| `W` / `S` | Throttle / brake; pitch while airborne |
| `A` / `D` | Steer; roll while airborne |
| `S` + `A`/`D` | Brake while turning to drift |
| `Space` | Rear rocket thruster |
| `F` | Bottom thrusters |
| `Q` / `E` | Yaw while airborne |
| `Z` / `C` | Side thrusters in MANUAL mode |
| `Shift` | Hold wall grip |
| `G` | Toggle the wall-grip system on or off |
| `M` | Switch AUTO / MANUAL thruster mode |
| `B` | Toggle Stability Mode |
| `P` | Cycle Manual, Standard, Trick and Roadster ZERO autopilot (manual drive input interrupts) |
| Mouse drag | Orbit the camera; it returns to chase view after 3.5 seconds |
| `R` | Respawn at the last checkpoint |
| `T` | Return to the start |
| `V` | Show/hide the developer bloom panel |
| `H` | Hide/show the controls guide |
| `Esc` | Open/close the menu |

### Mobile

Use the on-screen joystick to accelerate/brake and steer. Pull back while steering to brake and drift. In the air, the joystick controls pitch and roll. Hold **ROCKET** for rear thrust and **LIFT** for bottom thrusters, and use **YAW** for rotation. **GRIP** toggles wall grip and **AUTO** switches landing-assist modes. Drag the scene to look around. Open **Controls** for the on-screen guide.

## Where to tune the experience

Search `script.js` for these names:

- `makeZone(...)` — each test zone's name, colour and bounds (for example `ZW` for the Adhesion Lab).
- `TUNNEL` — tunnel dimensions and world placement.
- `VEHICLE_MASS`, `VEHICLE_INERTIA`, `WHEEL_CONTACT_OFFSETS`, `CHASSIS_CONTACT_OFFSETS` — vehicle mass and contact layout.
- `SOLID_PROBES` — collision probe points around the car.
- `PARTICLE_COUNT` — thruster and dust particle pool size.
- `MOUSE_RETURN_DELAY` and `MOUSE_RETURN_DURATION` — camera look-return timing.
- `initSound()`, `updateSound()`, `playLandingImpact()` — synthesized audio.

## Visual and product direction

The goal is a premium, shareable vehicle playground: a compact stunt facility, distinctive ramps and targets, controlled airborne manoeuvres, convincing effects, cinematic but readable camera work, quick resets, and a responsive experience. Performance and clear feedback matter; visuals and effects should not obscure the driving surface or make the browser experience unstable.

The core idea is simple: **Drive it. Launch it. Rotate it. Try something ridiculous. See whether you can land it.**

## Credits and disclaimer

Created by Muhammad Bilal Khan.

Inspired by the Tesla Roadster and the concept of rocket-assisted vehicle demonstrations. Tesla and Roadster are referenced for inspiration only. This is an unofficial fan-made project, not affiliated with, endorsed by, or representative of Tesla, Inc.
