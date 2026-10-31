import gzip
import math
import os
import re
import secrets
import time
from pathlib import Path

from flask import Flask, Response, abort, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room


ROOT = Path(__file__).resolve().parent
MAX_PLAYERS_PER_ROOM = 8
ROOM_PATTERN = re.compile(r"^[A-Z0-9]{4,8}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]{2,20}$")
PALETTE = ["#e85d4a", "#41a6a0", "#e4b54a", "#658bd6", "#c276aa", "#83ad64", "#d8874a", "#9b83d5"]

app = Flask(__name__, static_folder=None)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
socketio = SocketIO(
    app,
    async_mode="threading",
    cors_allowed_origins=os.environ.get("CORS_ALLOWED_ORIGINS", "*"),
    max_http_buffer_size=16_384,
    ping_interval=25,
    ping_timeout=20,
)

rooms = {}
players = {}


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.get("/<path:filename>")
def project_file(filename):
    path = (ROOT / filename).resolve()
    if ROOT not in path.parents or not path.is_file() or path.name.startswith("."):
        abort(404)
    if filename == "script.js" and "gzip" in request.headers.get("Accept-Encoding", ""):
        response = Response(gzip.compress(path.read_bytes()), mimetype="text/javascript")
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"
        response.headers["Cache-Control"] = "no-cache"
        return response
    return send_from_directory(ROOT, filename, conditional=False)


def public_player(player):
    return {
        "id": player["id"],
        "username": player["username"],
        "color": player["color"],
        "position": player["position"],
        "quaternion": player["quaternion"],
    }


def clean_pose(data):
    if not isinstance(data, dict):
        return None
    position = data.get("position")
    quaternion = data.get("quaternion")
    if not isinstance(position, list) or len(position) != 3:
        return None
    if not isinstance(quaternion, list) or len(quaternion) != 4:
        return None
    try:
        position = [float(value) for value in position]
        quaternion = [float(value) for value in quaternion]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in position + quaternion):
        return None
    if abs(position[0]) > 5000 or abs(position[2]) > 5000 or not -100 <= position[1] <= 5000:
        return None
    length = math.sqrt(sum(value * value for value in quaternion))
    if not 0.5 <= length <= 1.5:
        return None
    return position, [value / length for value in quaternion]


@socketio.on("join_game")
def handle_join(data):
    if not isinstance(data, dict):
        return {"ok": False, "error": "Invalid join request."}
    username = str(data.get("username", "")).strip()
    if not USERNAME_PATTERN.fullmatch(username):
        return {"ok": False, "error": "Use 2-20 letters, numbers, spaces, _ or -."}

    room_code = str(data.get("room", "")).strip().upper()
    if not room_code:
        room_code = secrets.token_hex(3).upper()
    if not ROOM_PATTERN.fullmatch(room_code):
        return {"ok": False, "error": "Room codes must be 4-8 letters or numbers."}

    sid = request_sid()
    previous = players.get(sid)
    if previous:
        remove_player(sid, previous)
    room = rooms.setdefault(room_code, {})
    if len(room) >= MAX_PLAYERS_PER_ROOM:
        return {"ok": False, "error": "That room is full (8 players maximum)."}
    if any(player["username"].casefold() == username.casefold() for player in room.values()):
        return {"ok": False, "error": "That username is already in this room."}

    player = {
        "id": sid,
        "username": username,
        "color": PALETTE[len(room) % len(PALETTE)],
        "room": room_code,
        "position": [0.0, 0.0, -30.0],
        "quaternion": [0.0, 0.0, 0.0, 1.0],
        "last_pose": 0.0,
    }
    existing = [public_player(item) for item in room.values()]
    room[sid] = player
    players[sid] = player
    join_room(room_code)
    emit("player_joined", public_player(player), to=room_code, include_self=False)
    return {"ok": True, "room": room_code, "player_id": sid, "players": existing}


def request_sid():
    from flask import request

    return request.sid


def remove_player(sid, player):
    room_code = player["room"]
    room = rooms.get(room_code, {})
    room.pop(sid, None)
    players.pop(sid, None)
    leave_room(room_code)
    emit("player_left", {"id": sid}, to=room_code)
    if not room:
        rooms.pop(room_code, None)


@socketio.on("player_pose")
def handle_pose(data):
    player = players.get(request_sid())
    if not player:
        return
    now = time.monotonic()
    if now - player["last_pose"] < 0.04:
        return
    pose = clean_pose(data)
    if pose is None:
        return
    player["last_pose"] = now
    player["position"], player["quaternion"] = pose
    emit("player_pose", public_player(player), to=player["room"], include_self=False)


@socketio.on("disconnect")
def handle_disconnect(reason=None):
    sid = request_sid()
    player = players.get(sid)
    if player:
        remove_player(sid, player)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    socketio.run(app, host=os.environ.get("HOST", "0.0.0.0"), port=port, debug=False, allow_unsafe_werkzeug=True)