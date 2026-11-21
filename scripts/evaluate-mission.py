"""미션 B5-1 (5-1-Mini-Redis_02) 자동 검증 스크립트.

[실생활 비유]
  자동 채점기입니다. 금지 자료형(dict/set/collections) 미사용 여부부터
  모듈 분리, evaluation 폴더 문서, String/LRU/TTL/OOM/에러 형식, REPL, 단위 테스트까지
  12개 항목을 자동으로 채점해 PASS/FAIL을 출력합니다.

[실행 방법]
  cd C:\\Users\\domod\\5-1-Mini-Redis_02
  python scripts\\evaluate-mission.py
"""
import ast
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mini_redis.main import execute  # noqa: E402
from mini_redis.mini_redis import MiniRedis  # noqa: E402

results = []


def check(name, ok):
    """검증 항목 한 줄을 채점하고 결과를 출력합니다."""
    results.append(bool(ok))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))


class FakeClock:
    """실제 대기 시간 없이 TTL 만료를 테스트하기 위한 가짜 시계."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def run_cmds(store, *lines):
    """여러 줄의 CLI 명령어를 순서대로 실행해 출력 리스트를 반환합니다."""
    return [execute(store, ln) for ln in lines]


# ===== 1구역: 정적 규칙 및 파일 구조 검사 =====
def check_no_forbidden_builtins():
    """mini_redis 패키지 내부에 dict, set, collections 사용이 없는지 AST로 검사합니다."""
    pkg_dir = os.path.join(ROOT, "mini_redis")
    violations = []
    for filename in os.listdir(pkg_dir):
        if not filename.endswith(".py"):
            continue
        path = os.path.join(pkg_dir, filename)
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filename)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Dict, ast.Set, ast.DictComp, ast.SetComp)):
                violations.append("%s:literal" % filename)
            if isinstance(node, ast.Name) and node.id in ("dict", "set", "defaultdict", "OrderedDict", "Counter", "deque"):
                violations.append("%s:%s" % (filename, node.id))
            if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "collections" for a in node.names):
                violations.append("%s:import_collections" % filename)
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "collections":
                violations.append("%s:from_collections" % filename)
    return len(violations) == 0


expected_modules = (
    "main.py",
    "mini_redis.py",
    "string_commands.py",
    "memory.py",
    "ttl.py",
    "errors.py",
    "hashmap.py",
    "doubly_linked_list.py",
    "min_heap.py",
)

expected_eval_docs = (
    "README.md",
    "item1_basic_features.md",
    "item2_data_structures.md",
    "item3_lru_ttl_flows.md",
    "item4_advanced_design.md",
)

check("1. dict/set/collections 미사용 (AST 정적 검사)", check_no_forbidden_builtins())
check(
    "2. GPT 설계 기반 mini_redis 핵심 모듈 9종 분리 존재",
    all(os.path.isfile(os.path.join(ROOT, "mini_redis", fn)) for fn in expected_modules),
)
check(
    "3. 평가항목 전용 폴더(evaluation/) 5개 문서 존재",
    all(os.path.isfile(os.path.join(ROOT, "evaluation", fn)) for fn in expected_eval_docs),
)

# ===== 2구역: 핵심 기능 요구사항 점검 =====
s = MiniRedis()
r = run_cmds(s, 'SET a "x y"', "GET a", "EXISTS a", "DBSIZE", "KEYS", "DEL a", "DEL a", "GET a")
check(
    "4. String 명령 6종 (SET/GET/EXISTS/DBSIZE/KEYS/DEL)",
    r == ["OK", '"x y"', "(integer) 1", "(integer) 1", '1. "a"', "(integer) 1", "(integer) 0", "(nil)"],
)

s = MiniRedis()
r = run_cmds(
    s,
    "CONFIG SET maxmemory 30",
    'SET user:1 "Alice"',
    'SET user:2 "Bob"',
    'SET user:3 "Charlie"',
    "GET user:1",
    "INFO memory",
)
check(
    "5. LRU 자동 제거 + INFO memory (22/30/1 예시 일치)",
    r[4] == "(nil)" and r[5] == "used_memory:22\nmaxmemory:30\nevicted_keys:1",
)

s = MiniRedis()
run_cmds(s, "CONFIG SET maxmemory 20", "SET a 1234567", "SET b 1234567", "GET a", "SET c 1234567")
check(
    "6. GET 시 LRU 갱신 (a 생존, b 방출)",
    run_cmds(s, "EXISTS a", "EXISTS b") == ["(integer) 1", "(integer) 0"],
)

s = MiniRedis()
run_cmds(s, "CONFIG SET maxmemory 5", "SET ok 1")
oom_out = execute(s, "SET key value")
check(
    "7. 단일 엔트리 maxmemory 초과 시 OOM 에러 및 기존 상태 보존",
    oom_out == "(error) OOM command not allowed when used_memory > 'maxmemory'"
    and execute(s, "GET ok") == '"1"',
)

clk = FakeClock()
s = MiniRedis(clk)
run_cmds(s, "SET a 1", "SET b 2")
r_ttl = run_cmds(s, "TTL a", "EXPIRE a 3", "TTL a", "EXPIRE nokey 3", "EXPIRE b 0")
clk.t += 3
r_after = run_cmds(s, "GET a", "TTL a", "EXISTS b", "DBSIZE")
check(
    "8. TTL/EXPIRE 규칙 (-1, 3, 만료 후 nil/-2, 없는 키 0, <=0 즉시 삭제)",
    r_ttl == ["(integer) -1", "(integer) 1", "(integer) 3", "(integer) 0", "(integer) 1"]
    and r_after == ["(nil)", "(integer) -2", "(integer) 0", "(integer) 0"],
)

clk = FakeClock()
s = MiniRedis(clk)
run_cmds(s, "SET a 1", "EXPIRE a 5", "SET a 2")
clk.t += 6
check(
    "9. SET 덮어쓰기 시 TTL 초기화 및 힙 Lazy Deletion 정합성",
    run_cmds(s, "TTL a", "GET a") == ["(integer) -1", '"2"'],
)

s = MiniRedis()
r_err = run_cmds(s, "CONFIG SET maxmemory abc", "GET", "HELLO", "INFO cpu", "CONFIG SET other 10")
check(
    "10. 표준 에러 형식 (정수/인자/미지원 명령/INFO/CONFIG)",
    r_err == [
        "(error) ERR value is not an integer or out of range",
        "(error) ERR wrong number of arguments for 'GET' command",
        "(error) ERR unknown command 'HELLO'",
        "(error) ERR unknown section 'cpu'",
        "(error) ERR unsupported CONFIG subcommand",
    ],
)

# ===== 3구역: 실제 CLI 프로세스로 REPL 및 단위 테스트 검증 =====
proc = subprocess.run(
    [sys.executable, os.path.join(ROOT, "main.py")],
    input='SET k "hello world"\nGET k\nquit\n',
    capture_output=True,
    text=True,
    encoding="utf-8",
)
check(
    "11. REPL 프로세스: 프롬프트 출력 + quit 정상 종료",
    "mini-redis>" in proc.stdout and '"hello world"' in proc.stdout and proc.returncode == 0,
)

suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"), top_level_dir=ROOT)
with open(os.devnull, "w") as devnull:
    test_res = unittest.TextTestRunner(stream=devnull).run(suite)
check("12. 단위 테스트 %d개 전체 통과" % test_res.testsRun, test_res.wasSuccessful())

print("RESULT: %d/%d PASS" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
