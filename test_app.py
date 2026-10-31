import unittest

import app as multiplayer_app


class MultiplayerRoomTests(unittest.TestCase):
    def setUp(self):
        multiplayer_app.rooms.clear()
        multiplayer_app.players.clear()
        self.first = multiplayer_app.socketio.test_client(multiplayer_app.app)
        self.second = multiplayer_app.socketio.test_client(multiplayer_app.app)
        self.other_room = multiplayer_app.socketio.test_client(multiplayer_app.app)

    def tearDown(self):
        self.first.disconnect()
        self.second.disconnect()
        self.other_room.disconnect()
        multiplayer_app.rooms.clear()
        multiplayer_app.players.clear()

    def join(self, client, username, room="TRACK1"):
        return client.emit("join_game", {"username": username, "room": room}, callback=True)

    def test_room_join_and_duplicate_username_validation(self):
        created = self.join(self.first, "Driver One")
        joined = self.join(self.second, "Driver Two")
        duplicate = self.join(self.other_room, "driver one")

        self.assertTrue(created["ok"])
        self.assertEqual(created["room"], "TRACK1")
        self.assertTrue(joined["ok"])
        self.assertEqual(len(joined["players"]), 1)
        self.assertFalse(duplicate["ok"])
        self.assertIn("already", duplicate["error"])

    def test_pose_is_relayed_only_to_room_members(self):
        self.join(self.first, "Driver One")
        self.join(self.second, "Driver Two")
        self.join(self.other_room, "Driver Three", "TRACK2")
        self.first.get_received()
        self.second.get_received()
        self.other_room.get_received()

        self.first.emit("player_pose", {"position": [12, 3, -45], "quaternion": [0, 0, 0, 1]})

        received = self.second.get_received()
        isolated = self.other_room.get_received()
        pose_events = [event for event in received if event["name"] == "player_pose"]
        self.assertEqual(len(pose_events), 1)
        self.assertEqual(pose_events[0]["args"][0]["position"], [12, 3, -45])
        self.assertFalse(any(event["name"] == "player_pose" for event in isolated))

    def test_invalid_pose_is_not_broadcast(self):
        self.join(self.first, "Driver One")
        self.join(self.second, "Driver Two")
        self.second.get_received()

        self.first.emit("player_pose", {"position": [float("nan"), 0, 0], "quaternion": [0, 0, 0, 1]})

        self.assertFalse(any(event["name"] == "player_pose" for event in self.second.get_received()))


if __name__ == "__main__":
    unittest.main()