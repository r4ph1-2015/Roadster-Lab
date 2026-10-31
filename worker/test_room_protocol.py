import unittest

from room_protocol import clean_pose, valid_room, valid_username


class RoomProtocolTests(unittest.TestCase):
    def test_username_and_room_validation(self):
        self.assertTrue(valid_username("Driver One"))
        self.assertFalse(valid_username("x"))
        self.assertFalse(valid_username("Bad/Name"))
        self.assertTrue(valid_room("AB12"))
        self.assertFalse(valid_room("bad-room"))

    def test_pose_is_normalized_and_checked(self):
        pose = clean_pose({"position": [1, 2, 3], "quaternion": [0, 0, 0, 1]})
        self.assertEqual(pose, ([1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0]))
        self.assertIsNone(clean_pose({"position": [float("nan"), 0, 0], "quaternion": [0, 0, 0, 1]}))
        self.assertIsNone(clean_pose({"position": [6000, 0, 0], "quaternion": [0, 0, 0, 1]}))


if __name__ == "__main__":
    unittest.main()
