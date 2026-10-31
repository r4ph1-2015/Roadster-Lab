import json
from urllib.parse import parse_qs, urlsplit

from js import Date, WebSocketPair
from workers import DurableObject, Response, WorkerEntrypoint

from room_protocol import MAX_PLAYERS_PER_ROOM, PALETTE, clean_pose, new_player_id, valid_room, valid_username


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlsplit(request.url).path
        if path == "/health":
            return Response.json({"ok": True, "service": "roadster-thrust-lab"})
        if path != "/ws":
            return await self.env.ASSETS.fetch(request)
        if request.headers.get("Upgrade", "").lower() != "websocket":
            return Response("WebSocket upgrade required", status=426)

        params = parse_qs(urlsplit(request.url).query)
        username = params.get("username", [""])[0].strip()
        room = params.get("room", [""])[0].strip().upper()
        if not valid_username(username):
            return Response.json({"error": "Use 2-20 letters, numbers, spaces, _ or -."}, status=400)
        if not valid_room(room):
            return Response.json({"error": "Room codes must be 4-8 letters or numbers."}, status=400)

        room_stub = self.env.ROOMS.getByName(room)
        return await room_stub.fetch(request)


class GameRoom(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.ctx = ctx

    def _player_for(self, websocket):
        attachment = websocket.deserializeAttachment()
        if not attachment:
            return None
        try:
            return json.loads(str(attachment))
        except (TypeError, ValueError):
            return None

    def _players(self):
        return [player for player in (self._player_for(ws) for ws in self.ctx.getWebSockets()) if player]

    @staticmethod
    def _public_player(player):
        return {key: player[key] for key in ("id", "username", "color", "position", "quaternion")}

    def _broadcast(self, message, exclude_id=None):
        encoded = json.dumps(message, separators=(",", ":"))
        for websocket in self.ctx.getWebSockets():
            player = self._player_for(websocket)
            if not player or player["id"] == exclude_id:
                continue
            try:
                websocket.send(encoded)
            except Exception:
                websocket.close(1011, "Broadcast failed")

    def _rejected_socket(self, message):
        client, server = WebSocketPair.new().object_values()
        self.ctx.acceptWebSocket(server)
        server.send(json.dumps({"type": "rejected", "error": message}))
        return Response(None, status=101, web_socket=client)

    async def fetch(self, request):
        params = parse_qs(urlsplit(request.url).query)
        username = params.get("username", [""])[0].strip()
        room = params.get("room", [""])[0].strip().upper()
        players = self._players()
        if len(players) >= MAX_PLAYERS_PER_ROOM:
            return self._rejected_socket("That room is full (8 players maximum).")
        if any(player["username"].casefold() == username.casefold() for player in players):
            return self._rejected_socket("That username is already in this room.")

        client, server = WebSocketPair.new().object_values()
        player = {
            "id": new_player_id(),
            "username": username,
            "color": PALETTE[len(players) % len(PALETTE)],
            "room": room,
            "position": [0.0, 0.0, -30.0],
            "quaternion": [0.0, 0.0, 0.0, 1.0],
            "last_pose_at": 0,
        }
        server.serializeAttachment(json.dumps(player, separators=(",", ":")))
        self.ctx.acceptWebSocket(server)
        server.send(json.dumps({
            "type": "joined",
            "room": room,
            "player_id": player["id"],
            "players": [self._public_player(item) for item in players],
        }, separators=(",", ":")))
        self._broadcast({"type": "player_joined", "player": self._public_player(player)}, exclude_id=player["id"])
        return Response(None, status=101, web_socket=client)

    async def webSocketMessage(self, websocket, message):
        if not isinstance(message, str) or len(message) > 2048:
            return
        try:
            data = json.loads(message)
        except (TypeError, ValueError):
            return
        if data.get("type") != "pose":
            return
        player = self._player_for(websocket)
        pose = clean_pose(data)
        now = int(Date.now())
        if not player or not pose or now - player["last_pose_at"] < 45:
            return
        player["position"], player["quaternion"] = pose
        player["last_pose_at"] = now
        websocket.serializeAttachment(json.dumps(player, separators=(",", ":")))
        self._broadcast({"type": "player_pose", "player": self._public_player(player)}, exclude_id=player["id"])

    async def webSocketClose(self, websocket, code, reason, was_clean):
        player = self._player_for(websocket)
        if player:
            self._broadcast({"type": "player_left", "id": player["id"]}, exclude_id=player["id"])

    async def webSocketError(self, websocket, error):
        websocket.close(1011, "WebSocket error")