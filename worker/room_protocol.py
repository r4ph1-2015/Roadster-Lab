import math
import re
import secrets

MAX_PLAYERS_PER_ROOM = 8
ROOM_PATTERN = re.compile(r"^[A-Z0-9]{4,8}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]{2,20}$")
PALETTE = ["#e85d4a", "#41a6a0", "#e4b54a", "#658bd6", "#c276aa", "#83ad64", "#d8874a", "#9b83d5"]


def valid_username(value):
    return isinstance(value, str) and USERNAME_PATTERN.fullmatch(value) is not None


def valid_room(value):
    return isinstance(value, str) and ROOM_PATTERN.fullmatch(value) is not None


def new_player_id():
    return secrets.token_hex(16)


def clean_pose(data):
    if not isinstance(data, dict):
        return None
    position = data.get("position")
    quaternion = data.get("quaternion")
    if not isinstance(position, list) or len(position) != 3:
        return None
    if not isinstance(quaternion, list) or len(quaternion) != 4:
        return None
    values = position + quaternion
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in values):
        return None
    x, y, z = position
    if abs(x) > 5000 or abs(z) > 5000 or not -100 <= y <= 5000:
        return None
    length = math.sqrt(sum(value * value for value in quaternion))
    if not 0.5 <= length <= 1.5:
        return None
    return [float(value) for value in position], [value / length for value in quaternion]
