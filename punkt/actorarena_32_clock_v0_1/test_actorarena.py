import unittest

from actorarena import ActorArena, Request


class ActorArenaTests(unittest.TestCase):
    def test_open_realizes_and_witnesses(self) -> None:
        arena = ActorArena()
        result = arena.process(Request("open", 32, {"x": 1}), 32)
        self.assertEqual(result.decision, "OPEN")
        self.assertTrue(result.state_changed)
        self.assertTrue(result.witnessed)
        self.assertEqual(len(arena.state), 1)
        self.assertEqual(len(arena.witness), 1)

    def test_hold_is_fail_closed(self) -> None:
        arena = ActorArena()
        result = arena.process(Request("hold", 7, {}, ready=False), 7)
        self.assertEqual(result.decision, "HOLD")
        self.assertFalse(result.state_changed)
        self.assertEqual(arena.state, [])
        self.assertEqual(arena.witness, [])

    def test_kill_dominates_not_ready(self) -> None:
        arena = ActorArena()
        result = arena.process(
            Request("kill", 8, {}, ready=False, integrity=False), 8
        )
        self.assertEqual(result.decision, "KILL")
        self.assertEqual(result.reason, "integrity_failure")
        self.assertFalse(result.state_changed)

    def test_zero_window_miss_is_terminal_rejection(self) -> None:
        arena = ActorArena()
        result = arena.process(Request("late", 12, {}), 13)
        self.assertEqual(result.decision, "REJECTED")
        self.assertEqual(result.reason, "zero_window_miss")
        self.assertFalse(result.witnessed)

    def test_all_32_positions_are_addressable(self) -> None:
        arena = ActorArena()
        for position in range(1, 33):
            result = arena.process(Request(f"r-{position}", position, {}), position)
            self.assertEqual(result.decision, "OPEN")
        self.assertEqual(len(arena.state), 32)
        self.assertEqual(len(arena.witness), 32)

    def test_witness_chain_links_forward(self) -> None:
        arena = ActorArena()
        arena.process(Request("one", 1, {"n": 1}), 1)
        arena.process(Request("two", 2, {"n": 2}), 2)
        self.assertEqual(arena.witness[1]["prev_hash"], arena.witness[0]["hash"])


if __name__ == "__main__":
    unittest.main()
