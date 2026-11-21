"""Mini Redis 자료구조 및 전체 명령어 단위 테스트 스위트."""
import unittest

from mini_redis.doubly_linked_list import DoublyLinkedList
from mini_redis.hashmap import HashMap
from mini_redis.main import execute
from mini_redis.min_heap import MinHeap
from mini_redis.mini_redis import MiniRedis


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def run(store, *lines):
    return [execute(store, ln) for ln in lines]


class StructTests(unittest.TestCase):
    def test_doubly_linked_list(self):
        dll = DoublyLinkedList()
        a = dll.insert_back(1)
        b = dll.insert_back(2)
        c = dll.insert_back(3)
        self.assertEqual(len(dll), 3)
        dll.move_to_front(c)
        self.assertEqual((dll.head.data, dll.tail.data), (3, 2))
        dll.remove_node(a)
        self.assertEqual((dll.head.data, dll.tail.data, len(dll)), (3, 2, 2))
        self.assertEqual(dll.remove_front(), 3)
        self.assertEqual(dll.remove_back(), 2)
        self.assertEqual(len(dll), 0)
        self.assertIsNone(dll.remove_front())
        self.assertIsNone(dll.remove_back())
        # 단일 노드일 때 move_to_front 안전 동작 확인
        x = dll.insert_front(99)
        dll.move_to_front(x)
        self.assertEqual((dll.head.data, dll.tail.data, len(dll)), (99, 99, 1))
        self.assertEqual(dll.remove_node(b if False else x), 99)

    def test_hashmap_chaining_and_resize(self):
        hm = HashMap(2)
        for i in range(100):
            hm.put("k%d" % i, i)
        self.assertEqual(hm.size(), 100)
        self.assertEqual(hm.get("k57"), 57)
        # 덮어쓰기 시 크기가 늘지 않고 값만 바뀌어야 함
        hm.put("k57", 570)
        self.assertEqual(hm.get("k57"), 570)
        self.assertEqual(hm.size(), 100)
        # 삭제 및 미존재 확인
        self.assertTrue(hm.remove("k57"))
        self.assertFalse(hm.remove("k57"))
        self.assertFalse(hm.contains("k57"))
        # 100개 기준 0.75 로드팩터 이하 유지를 위해 버킷 >= 128 이상으로 2배씩 확장
        self.assertGreaterEqual(hm.bucket_count(), 128)

    def test_min_heap(self):
        heap = MinHeap()
        for x in [5, 3, 8, 1, 9, 2]:
            heap.push((x, "k%d" % x))
        self.assertEqual(heap.peek()[0], 1)
        self.assertEqual([heap.pop()[0] for _ in range(6)], [1, 2, 3, 5, 8, 9])
        self.assertIsNone(heap.pop())
        self.assertIsNone(heap.peek())


class CommandTests(unittest.TestCase):
    def test_string_commands_basic(self):
        s = MiniRedis()
        self.assertEqual(
            run(s, "KEYS", 'SET k "a b"', "GET k", "EXISTS k", "DBSIZE", "KEYS", "DEL k", "DEL k", "DBSIZE"),
            [
                "(empty array)",
                "OK",
                '"a b"',
                "(integer) 1",
                "(integer) 1",
                '1. "k"',
                "(integer) 1",
                "(integer) 0",
                "(integer) 0",
            ],
        )

    def test_spec_example_lru_and_info_memory(self):
        s = MiniRedis()
        r = run(
            s,
            "CONFIG SET maxmemory 30",
            'SET user:1 "Alice"',
            'SET user:2 "Bob"',
            'SET user:3 "Charlie"',
            "GET user:1",
            "INFO memory",
        )
        self.assertEqual(r[:5], ["OK", "OK", "OK", "OK", "(nil)"])
        self.assertEqual(r[5], "used_memory:22\nmaxmemory:30\nevicted_keys:1")

    def test_lru_get_refresh(self):
        s = MiniRedis()
        run(s, "CONFIG SET maxmemory 20", "SET a 1234567", "SET b 1234567", "GET a", "SET c 1234567")
        self.assertEqual(run(s, "EXISTS a", "EXISTS b", "EXISTS c"), ["(integer) 1", "(integer) 0", "(integer) 1"])

    def test_oom_single_entry(self):
        s = MiniRedis()
        run(s, "CONFIG SET maxmemory 5", "SET ok 1")
        self.assertEqual(
            execute(s, "SET key value"),
            "(error) OOM command not allowed when used_memory > 'maxmemory'",
        )
        self.assertEqual(execute(s, "GET ok"), '"1"')

    def test_config_maxmemory_shrink_evicts_immediately(self):
        s = MiniRedis()
        run(s, "SET a 12345", "SET b 12345", "CONFIG SET maxmemory 6")
        self.assertEqual(
            run(s, "EXISTS a", "EXISTS b", "INFO memory"),
            ["(integer) 0", "(integer) 1", "used_memory:6\nmaxmemory:6\nevicted_keys:1"],
        )

    def test_ttl_and_expire_rules(self):
        c = FakeClock()
        s = MiniRedis(c)
        run(s, "SET a 1", "SET b 2")
        self.assertEqual(
            run(s, "TTL a", "EXPIRE a 3", "TTL a", "EXPIRE x 3", "EXPIRE b 0"),
            ["(integer) -1", "(integer) 1", "(integer) 3", "(integer) 0", "(integer) 1"],
        )
        self.assertEqual(execute(s, "EXISTS b"), "(integer) 0")
        c.t += 3
        self.assertEqual(
            run(s, "GET a", "TTL a", "DBSIZE", "INFO memory"),
            ["(nil)", "(integer) -2", "(integer) 0", "used_memory:0\nmaxmemory:0\nevicted_keys:0"],
        )

    def test_set_resets_ttl_and_lazy_deletion(self):
        c = FakeClock()
        s = MiniRedis(c)
        run(s, "SET a 1", "EXPIRE a 5", "SET a 2")
        c.t += 6
        self.assertEqual(run(s, "TTL a", "GET a"), ["(integer) -1", '"2"'])

    def test_del_then_reinsert_does_not_get_killed_by_stale_heap(self):
        c = FakeClock()
        s = MiniRedis(c)
        run(s, "SET A 100", "EXPIRE A 5", "DEL A", "SET A 200")
        c.t += 6
        # 옛 (expire_at=1005, "A") 힙 레코드가 pop되더라도 새 A("200")의 expire_at(None)과 달라 삭제되지 않아야 함
        self.assertEqual(run(s, "GET A", "TTL A", "DBSIZE"), ['"200"', "(integer) -1", "(integer) 1"])

    def test_standard_errors(self):
        s = MiniRedis()
        self.assertEqual(
            run(
                s,
                "CONFIG SET maxmemory abc",
                "CONFIG SET maxmemory -1",
                "EXPIRE a xyz",
                "GET",
                "HELLO",
                "INFO cpu",
                "CONFIG SET other 10",
                "CONFIG GET",
            ),
            [
                "(error) ERR value is not an integer or out of range",
                "(error) ERR value is not an integer or out of range",
                "(error) ERR value is not an integer or out of range",
                "(error) ERR wrong number of arguments for 'GET' command",
                "(error) ERR unknown command 'HELLO'",
                "(error) ERR unknown section 'cpu'",
                "(error) ERR unsupported CONFIG subcommand",
                "(error) ERR wrong number of arguments for 'CONFIG' command",
            ],
        )


if __name__ == "__main__":
    unittest.main()
