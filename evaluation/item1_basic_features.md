# 항목 1 평가 분석: 기본 기능 구현 및 CLI 동작 검증 (5문항)

> **대상 모듈**: `mini_redis/string_commands.py`, `mini_redis/memory.py`, `mini_redis/ttl.py`, `mini_redis/errors.py`, `mini_redis/mini_redis.py`, `mini_redis/main.py`

---

## 문항 1-1. String 타입 기본 동작: `SET`, `GET`, `DEL`, `EXISTS`, `DBSIZE`, `KEYS` 명령어가 모두 정상 동작하는가?

### 1) 질문 의도 해석
- Redis의 가장 기본적인 Key-Value 저장·조회·삭제·통계 연산 6종이 파이썬 내장 `dict`/`set`/`collections` 없이 직접 구현한 해시맵 위에서 정확히 동작하는지, 그리고 CLI 따옴표 파싱(`"Kim Min"`)과 반환 포맷(`OK`, `"값"`, `(nil)`, `(integer) N`, `(empty array)`, `1. "key"`)까지 규격에 맞는지 묻는 항목입니다.

### 2) 실생활 비유
- **도서관 기본 대출 데스크**: 책 등록/교체(`SET`), 책 찾기(`GET`), 폐기(`DEL`), 보유 여부 확인(`EXISTS`), 총 권수 세기(`DBSIZE`), 전체 책 제목 목록 출력(`KEYS`)에 해당합니다.

### 3) 우리 코드 구현 방식
- **`mini_redis/string_commands.py`** 에서 6개 함수로 명확히 분리 구현하고 **`mini_redis/mini_redis.py`** 가 조율합니다.
  - `set_key`: 기존 키면 값 교체·`used_memory` 차분 반영·TTL 초기화(`None`)·LRU 맨 앞 이동, 신규 키면 `LRU insert_front` + `Entry` 생성 + `HashMap put`.
  - `get_key`: 만료 검사 후 유효할 때만 LRU 맨 앞 이동 및 값 반환(`"value"`), 없으면 `(nil)`.
  - `delete_key`: 만료 검사 후 `delete_entry(key)` 호출해 해시맵·LRU 리스트·`used_memory` 동시 제거, 성공 시 `(integer) 1`, 미존재 시 `(integer) 0`.
  - `exists_key`: 만료 검사 후 `_map.contains(key)` 결과에 따라 `(integer) 1` 또는 `0`.
  - `dbsize_keys`: `purge_expired()` 수행 후 `_map.size()` 반환.
  - `all_keys`: `purge_expired()` 수행 후 `_map.keys()`를 `1. "key"` 형식으로 출력, 비었으면 `(empty array)`.
- **`mini_redis/main.py`의 `tokenize()`**: `"..."` 안의 공백을 하나의 토큰으로 묶고 빈 문자열 `""`도 인식합니다.

### 4) 평가 모범 답변 (요약)
> "String 6종 명령어는 `string_commands.py`에 분리되어 있으며 `MiniRedis` 조율기를 통해 직접 구현한 체이닝 `HashMap`과 `DoublyLinkedList`를 동시에 갱신합니다. 큰따옴표가 포함된 공백 문자열도 `tokenize()`로 정확히 파싱하고, 명령 실행 전 만료 키 정리를 선행해 `DBSIZE`와 `KEYS`에 만료된 유령 키가 남지 않도록 구현했습니다."

---

## 문항 1-2. LRU 자동 제거: `maxmemory` 설정 후 제한 초과 시 가장 오래된 키가 자동 제거되는가?

### 1) 질문 의도 해석
- `CONFIG SET maxmemory N`으로 메모리 상한이 지정된 상태에서 `SET`을 반복해 한도를 넘겼을 때, 단순히 거부하는 것이 아니라 **가장 오랫동안 사용되지 않은 키(Least Recently Used)부터 자동으로 방출(Eviction)** 해 `used_memory <= maxmemory` 불변식을 유지하는지 확인합니다. 또한 `GET` 조회가 성공하면 최근 사용 순서가 최신화되어 제거 우선순위에서 뒤로 밀리는지도 핵심입니다.

### 2) 실생활 비유
- **책상 크기 제한**: 책상 용량이 30권인데 새 책이 들어와 35권이 되면, 가장 오래 손대지 않은 맨 아래 책부터 서랍으로 치웁니다. 방금 다시 펼쳐 본 책은 맨 위로 올라가므로 치워지지 않습니다.

### 3) 우리 코드 구현 방식
- **`mini_redis/memory.py` (`MemoryManager.evict_if_needed`)**:
  - `while self.maxmemory > 0 and self.used_memory > self.maxmemory:` 루프를 돌며 `redis_store._lru.tail.data`(가장 오래된 키)를 꺼내 `redis_store.delete_entry(oldest_key)`를 호출하고 `self.evicted_keys += 1`을 기록합니다.
- **최신화 규칙**: `set_key`와 유효한 `get_key` 시 `_lru.move_to_front(entry.lru_node)`를 호출해 방금 쓴 키를 `head`로 보냅니다.
- **예외 보호**: `check_single_entry_fit()`을 통해 새로 저장할 단일 키+값 크기 자체가 `maxmemory`보다 크면 다른 키를 지워도 들어갈 수 없으므로 `OOMError`를 발생시키고 기존 데이터를 보호합니다.
- **한도 축소 대응**: `CONFIG SET maxmemory N`으로 기존 `used_memory`보다 작게 제한을 줄일 때도 즉시 `evict_if_needed()`가 실행됩니다.

### 4) 평가 모범 답변 (요약)
> "`CONFIG SET maxmemory`로 한도를 지정하면 `SET` 직후 `MemoryManager.evict_if_needed()`가 `used_memory <= maxmemory`가 될 때까지 이중 연결 리스트의 `tail`(가장 오래된 키)을 `O(1)`로 제거합니다. `GET`으로 읽힌 키는 `move_to_front()`로 `head`로 이동해 보호되며, 단일 엔트리만으로 한도를 초과할 때는 기존 데이터를 지우지 않고 OOM 에러를 반환합니다."

---

## 문항 1-3. 메모리 정보 확인: `INFO memory`에서 `used_memory`/`maxmemory`/`evicted_keys`가 규칙에 맞게 출력되는가?

### 1) 질문 의도 해석
- 메모리 지표 3종이 지정된 계산 규칙(`len(utf8(key)) + len(utf8(value))`)과 출력 포맷(`used_memory:N\nmaxmemory:N\nevicted_keys:N`)에 맞춰 실시간으로 정확히 계산·증감하는지 묻는 항목입니다.

### 2) 실생활 비유
- **창고 현황판**: 현재 적재된 짐 무게(`used_memory`), 창고 최대 적재 한도(`maxmemory`), 꽉 차서 밖으로 내보낸 짐 개수(`evicted_keys`)를 실시간으로 보여 주는 계기판입니다.

### 3) 우리 코드 구현 방식
- `calc_entry_size(key, value)` = `len(key.encode("utf-8")) + len(value.encode("utf-8"))`
- 지표 갱신 규칙:
  - **신규 `SET`**: `used_memory += calc_entry_size(key, value)`
  - **덮어쓰기 `SET`**: `used_memory += new_size - old_size` (차분만큼 정확히 보정)
  - **`DEL` / TTL 만료 삭제**: `delete_entry()`에서 `used_memory -= calc_entry_size(key, entry.value)` (단, **자발적 삭제·만료는 `evicted_keys`를 올리지 않음**)
  - **LRU 메모리 초과 방출**: `evict_if_needed()`에서만 `evicted_keys += 1` 증가
- **검증 예시 (`CONFIG SET maxmemory 30` 후 `user:1:"Alice"`, `user:2:"Bob"`, `user:3:"Charlie"`)**:
  - `user:1`(6) + `Alice`(5) = 11바이트
  - `user:2`(6) + `Bob`(3) = 9바이트 (누적 20)
  - `user:3`(6) + `Charlie`(7) = 13바이트 (누적 33 > 30 → 가장 오래된 `user:1` 방출)
  - 결과: `used_memory:22`, `maxmemory:30`, `evicted_keys:1`.

### 4) 평가 모범 답변 (요약)
> "`calc_entry_size`로 키와 값의 UTF-8 바이트 합을 구해 모든 저장·덮어쓰기·삭제 시 `used_memory`를 실시간으로 가감합니다. `evicted_keys`는 오직 `maxmemory` 초과로 인한 LRU 강제 제거 시에만 증가시키며, `INFO memory` 호출 시 3줄 표준 포맷으로 출력합니다."

---

## 문항 1-4. TTL 관리: `EXPIRE`/`TTL` 규칙이 동작하며 만료된 키가 적절히 제거되는가?

### 1) 질문 의도 해석
- 만료 시간 설정(`EXPIRE`)과 남은 시간 조회(`TTL`)의 반환 규칙(`1`/`0`, `-2`/`-1`/`남은 초`), 그리고 시간이 흘러 만료된 키가 해시맵·LRU 리스트·메모리 사용량에서 깔끔히 제거되는지 확인합니다.

### 2) 실생활 비유
- **유통기한 관리 스티커**: 제품에 3초 뒤 유통기한을 붙이고(`EXPIRE` → `1`), 남은 시간을 확인하며(`TTL`), 기한이 지나면 먹기 전이든(`purge_expired`) 꺼낼 때든(`expire_if_needed`) 폐기하고 없는 상품(`-2`)으로 처리합니다.

### 3) 우리 코드 구현 방식
- **`mini_redis/ttl.py` (`TTLManager`)**:
  - `EXPIRE key seconds`:
    - 없는 키 → `(integer) 0`
    - `seconds <= 0` → 즉시 `delete_entry(key)` 호출해 삭제 후 `(integer) 1`
    - `seconds > 0` → `entry.expire_at = now + seconds` 저장 및 `_heap.push((entry.expire_at, key))` 후 `(integer) 1`
  - `TTL key`:
    - 없는 키 또는 방금 만료 삭제된 키 → `(integer) -2`
    - 만료 설정 없음(`expire_at is None`) → `(integer) -1`
    - 유효한 만료 설정 → `int(entry.expire_at - now)` 반환
  - **덮어쓰기 규칙**: `SET key new_val`로 덮어쓰면 Redis 표준대로 `entry.expire_at = None`으로 TTL이 초기화(`TTL` → `-1`)됩니다.
  - **이중 청소 구조**:
    1. 매 명령 실행 전 `purge_expired()`가 힙 루트를 확인해 만료된 키를 일괄 정리(Active)
    2. 키 단위 명령(`GET`, `SET`, `DEL`, `EXISTS`, `EXPIRE`, `TTL`) 진입 시 `expire_if_needed()`로 재확인(Passive)

### 4) 평가 모범 답변 (요약)
> "`TTLManager`가 현재 시각 + 초 단위로 `expire_at`을 기록하고 최소 힙에 `(expire_at, key)`를 등록합니다. 명령 실행 전 힙 루트 기반 `purge_expired()`와 키 접근 시 `expire_if_needed()`를 이중 적용하며, 없는 키 `-2`·만료 없음 `-1`·0 이하 즉시 삭제·`SET` 덮어쓰기 시 TTL 초기화 규칙까지 모두 Redis 표준에 맞춰 구현했습니다."

---

## 문항 1-5. 에러 처리: 잘못된 명령/인자/정수 오류/OOM이 표준 형식으로 출력되는가?

### 1) 질문 의도 해석
- 예외적인 사용자 입력이 들어왔을 때 프로그램이 크래시(`Traceback`)하지 않고, Redis 프로토콜 형식(`(error) ERR ...` 또는 `(error) OOM ...`)의 명확한 오류 메시지를 출력한 뒤 REPL을 정상 유지하는지 묻는 항목입니다.

### 2) 실생활 비유
- **안내 데스크 표준 응대**: 메뉴판에 없는 메뉴를 부르거나 주문 개수를 틀리거나, 숫자 칸에 글자를 쓰거나, 창고가 꽉 찼을 때 직원이 당황해 문을 닫지 않고 규격화된 안내 문구를 들려줍니다.

### 3) 우리 코드 구현 방식
- **`mini_redis/errors.py` & `mini_redis/main.py`**:
  1. **알 수 없는 명령 (`HELLO`)**: `(error) ERR unknown command 'HELLO'`
  2. **인자 개수 불일치 (`GET`, `SET a`)**: `(error) ERR wrong number of arguments for 'GET' command`
  3. **정수 파싱/범위 오류 (`CONFIG SET maxmemory abc`, `CONFIG SET maxmemory -1`, `EXPIRE a xyz`)**: `(error) ERR value is not an integer or out of range`
  4. **메모리 한도 초과 (`OOM`)**: `(error) OOM command not allowed when used_memory > 'maxmemory'`
  5. **기타 하위 명령 오류**: `(error) ERR unknown section '...'` (`INFO`), `(error) ERR unsupported CONFIG subcommand` (`CONFIG`)

### 4) 평가 모범 답변 (요약)
> "`errors.py`에 Redis 표준 에러 포맷을 중앙 집중화하고 `execute()`에서 명령 존재 여부·인자 수(arity)·정수 변환·`OOMError`를 순차 검증합니다. 잘못된 입력이 들어와도 예외가 REPL 바깥으로 새지 않고 표준 `(error) ...` 문자열을 출력한 뒤 다음 명령을 계속 처리합니다."
