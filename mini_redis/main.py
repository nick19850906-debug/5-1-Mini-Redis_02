"""CLI 입력, 파싱(tokenize), 명령 실행(execute), REPL 반복 루프 모듈.

[실생활 비유]
  식당 카운터 접수대입니다.
  손님이 말한 한 줄 주문(예: SET user:1 "Kim Min")을 단어로 쪼개고(tokenize),
  메뉴판에 있는지와 재료 개수(인자 수)가 맞는지 검증한 뒤(execute)
  주방장(MiniRedis)에게 전달해 결과를 표준 형식으로 돌려줍니다.
"""
from .errors import (
    ERR_INT,
    ERR_OOM,
    OOMError,
    err_unknown_command,
    err_unknown_section,
    err_unsupported_config,
    err_wrong_arity,
)
from .mini_redis import MiniRedis


# ===== 1구역: 한 줄 명령어 토큰화 =====
def tokenize(line):
    """공백으로 단어를 나누되 큰따옴표("...")로 감싼 문자열은 공백을 포함해 한 덩어리로 묶습니다."""
    tokens = []
    cur = ""
    in_quotes = False
    has_token = False  # 빈 문자열 "" 도 유효한 토큰으로 인정하기 위한 플래그

    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            has_token = True
        elif ch.isspace() and not in_quotes:
            if has_token or cur:
                tokens.append(cur)
            cur = ""
            has_token = False
        else:
            cur += ch

    if has_token or cur:
        tokens.append(cur)
    return tokens


def _to_int(text):
    """문자열을 정수로 변환합니다. 정수가 아니면 None을 반환합니다."""
    try:
        return int(text)
    except ValueError:
        return None


# ===== 2구역: 명령어 실행기 =====
def execute(store, line):
    """CLI 한 줄을 파싱하고 실행한 뒤 표준 출력 문자열을 반환합니다. 빈 줄이면 None."""
    tokens = tokenize(line)
    if not tokens:
        return None

    raw_cmd = tokens[0]
    cmd = raw_cmd.upper()  # 명령어는 대소문자를 구분하지 않음 (set == SET)
    args = tokens[1:]

    # 모든 명령 실행 직전에 힙에서 만료 시각이 지난 키들을 먼저 청소
    store.purge_expired()

    # dict 사용 금지 규칙에 따라 (명령어, 필요 인자 수) 튜플 목록으로 검증
    arity_table = (
        ("SET", 2),
        ("GET", 1),
        ("DEL", 1),
        ("EXISTS", 1),
        ("DBSIZE", 0),
        ("KEYS", 0),
        ("EXPIRE", 2),
        ("TTL", 1),
        ("INFO", 1),
        ("CONFIG", 3),
    )

    expected_arity = -1
    for name, count in arity_table:
        if name == cmd:
            expected_arity = count
            break

    if expected_arity < 0:
        return err_unknown_command(raw_cmd)
    if len(args) != expected_arity:
        return err_wrong_arity(cmd)

    if cmd == "SET":
        try:
            store.set(args[0], args[1])
        except OOMError:
            return ERR_OOM
        return "OK"

    if cmd == "GET":
        value = store.get(args[0])
        return "(nil)" if value is None else '"%s"' % value

    if cmd == "DEL":
        return "(integer) %d" % (1 if store.delete(args[0]) else 0)

    if cmd == "EXISTS":
        return "(integer) %d" % (1 if store.exists(args[0]) else 0)

    if cmd == "DBSIZE":
        return "(integer) %d" % store.dbsize()

    if cmd == "KEYS":
        key_list = store.keys()
        if not key_list:
            return "(empty array)"
        return "\n".join('%d. "%s"' % (i + 1, k) for i, k in enumerate(key_list))

    if cmd == "EXPIRE":
        seconds = _to_int(args[1])
        if seconds is None:
            return ERR_INT
        return "(integer) %d" % store.expire(args[0], seconds)

    if cmd == "TTL":
        return "(integer) %d" % store.ttl(args[0])

    if cmd == "INFO":
        if args[0].lower() != "memory":
            return err_unknown_section(args[0])
        return store.info_memory()

    # 마지막 남은 명령: CONFIG SET maxmemory <바이트>
    if args[0].upper() != "SET" or args[1].lower() != "maxmemory":
        return err_unsupported_config()
    limit = _to_int(args[2])
    if limit is None or limit < 0:
        return ERR_INT
    store.set_maxmemory(limit)
    return "OK"


# ===== 3구역: REPL (Read-Eval-Print Loop) =====
def repl():
    """프롬프트(mini-redis>)를 띄워 사용자 명령을 계속 받아 처리하는 메인 루프."""
    store = MiniRedis()
    while True:
        try:
            line = input("mini-redis> ")
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip().lower() in ("exit", "quit"):
            break
        output = execute(store, line)
        if output is not None:
            print(output)


if __name__ == "__main__":
    repl()
