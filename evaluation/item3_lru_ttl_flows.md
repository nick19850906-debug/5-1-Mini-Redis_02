# 항목 3 평가 분석: LRU·TTL·Eviction·GET 핵심 동작 흐름 (5문항)

> **대상 모듈**: `mini_redis/mini_redis.py`, `mini_redis/string_commands.py`, `mini_redis/memory.py`, `mini_redis/ttl.py`

---

## 문항 3-1. LRU 구현에서 "해시맵 + 이중 연결 리스트"가 각각 어떤 역할을 하고, 왜 둘 다 필요한지 설명할 수 있는가?

### 1) 질문 의도 해석
- 단일 자료구조(해시맵만 쓰거나 리스트만 쓰는 경우)로는 왜 LRU 캐시를 `O(1)`로 만들 수 없는지, 두 자료구조의 **상호 보완성**을 정확히 짚어내는지 평가합니다.

### 2) 실생활 비유
- **도서관 검색대(해시맵) + 최근 대출 줄(이중 연결 리스트)**:
  - **검색대만 있으면**: 책 위치는 1초 만에 찾지만, "누가 제일 오래 안 읽혔는지" 알기 위해 도서관 책 전부를 뒤져야 합니다(`O(n)`).
  - **대출 줄만 있으면**: 맨 뒤 책을 버리는 건 1초(`O(1)`)지만, 방금 찾으려는 책이 줄 어디에 서 있는지 처음부터 찾아야 합니다(`O(n)`).
  - **둘을 합치면**: 검색대 카드(`Entry`)에 "대출 줄 몇 번째 손잡이(`lru_node`)" 주소까지 적어 두어 **찾기도 `O(1)`, 줄 맨 앞으로 옮기기도 `O(1)`** 이 됩니다.

### 3) 역할 분담 정리
| 자료구조 | 담당 역할 | 단독 사용 시 한계 |
| :--- | :--- | :--- |
| **해시맵 (`HashMap`)** | `key → Entry(value, lru_node, expire_at)` 매핑으로 키의 존재 여부, 값, 리스트 노드 주소를 평균 **`O(1)`** 로 즉시 찾음 | 키 간 **접근 순서(최신/오래됨)** 를 전혀 알 수 없음 (방출 대상 찾기에 `O(n)` 소요) |
| **이중 연결 리스트 (`DoublyLinkedList`)** | `head`(가장 최근 사용) ↔ `tail`(가장 오래 미사용) 순서를 유지하고, 임의 노드의 제거·맨 앞 이동·`tail` 방출을 **`O(1)`** 에 수행 | 특정 `key`가 리스트의 어디에 있는지 이름으로 **탐색하는 데 `O(n)`** 이 걸림 |

### 4) 평가 모범 답변 (요약)
> "해시맵은 '키로 데이터를 빠르게 찾는 역할(`O(1)`)'을, 이중 연결 리스트는 '사용 순서를 유지하고 가장 오래된 키(`tail`)를 빠르게 빼내는 역할(`O(1)`)'을 담당합니다. 해시맵만으로는 순서 추적이 불가능하고, 이중 연결 리스트만으로는 키 탐색이 `O(n)`이 되므로 두 자료구조를 결합해 서로의 단점을 보완해야 비로소 완전한 `O(1)` LRU가 됩니다."

---

## 문항 3-2. `O(1)` LRU 달성 원리를 "조회(해시) + 갱신(리스트 이동)" 관점에서 설명할 수 있는가?

### 1) 질문 의도 해석
- `Entry` 객체가 `lru_node` 포인터를 직접 들고 있는 연결 고리를 통해 어떻게 탐색(`O(1)`)에서 순서 갱신(`O(1)`)으로 즉시 이어지는지 메커니즘을 설명하는 항목입니다.

### 2) 두 단계 연결 메커니즘 (`mini_redis/mini_redis.py` & `string_commands.py`)
```python
class Entry:
    def __init__(self, value, lru_node, expire_at=None):
        self.value = value
        self.lru_node = lru_node  # 이중 연결 리스트 안의 내 노드 참조
        self.expire_at = expire_at
```
1. **1단계 — 조회(해시맵, 평균 `O(1)`)**:
   - 사용자가 `GET user:1`을 요청하면 `self._map.get("user:1")`이 `hash_key("user:1") % bucket_count` 위치의 버킷에서 `Entry` 객체를 즉시 꺼냅니다.
   - 이 `Entry` 안에 **이중 연결 리스트 안의 정확한 `Node` 객체 주소(`entry.lru_node`)** 가 이미 들어 있으므로 리스트를 훑을 필요가 없습니다.
2. **2단계 — 갱신(리스트 이동, 최악 `O(1)`)**:
   - `self._lru.move_to_front(entry.lru_node)`를 호출합니다.
   - `entry.lru_node`의 `prev`와 `next` 포인터를 바꿔 현재 위치에서 분리(`remove_node`)하고 `head` 자리에 끼워 넣으므로(`_link_front`), 총 데이터 수가 100개든 100만 개든 **포인터 조작 몇 번(`O(1)`)** 으로 최신화가 완료됩니다.
   - 반대로 메모리 초과 시 제거할 때는 `self._lru.tail.data`를 읽어 `O(1)`로 대상을 확정합니다.

### 3) 평가 모범 답변 (요약)
> "핵심 연결 고리는 해시맵에 저장되는 `Entry` 객체가 이중 연결 리스트의 `Node` 참조(`lru_node`)를 직접 보유하는 것입니다. 키가 조회되면 해시맵에서 `O(1)`로 `Entry`를 찾고(`조회`), 그 안에 담긴 `lru_node`를 그대로 `move_to_front()`에 넘겨 리스트를 순회하지 않고 앞뒤 포인터만 바꿔 맨 앞(`head`)으로 이동(`갱신`)시킴으로써 전체 LRU 갱신을 `O(1)`에 달성합니다."

---

## 문항 3-3. TTL 관리에 힙을 사용한 이유(가장 빠른 만료를 빠르게 찾는 성질)를 설명할 수 있는가?

### 1) 질문 의도 해석
- 해시맵을 매번 전체 스캔하거나(`O(n)`), 전체 키를 매번 정렬하는(`O(n log n)`) 대신 왜 **최소 힙(Min Heap)** 을 선택했는지, 그리고 중간 삭제가 어려운 힙의 약점을 **Lazy Deletion** 으로 어떻게 보완했는지 설명할 수 있는지 평가합니다.

### 2) 실생활 비유
- **유통기한 임박 알림판**: 냉장고에 음식이 10,000개 있어도 지금 버려야 할 음식이 있는지 확인하려면 "전체 줄 세우기"가 아니라 **"가장 유통기한이 빠른 음식 1개"** 만 맨 위에서 확인하면 됩니다.

### 3) 우리 코드에서의 선택 이유 (`mini_redis/min_heap.py` & `ttl.py`)
1. **필요한 것은 전체 정렬이 아니라 '최솟값(가장 빠른 만료 시각)' 하나**:
   - 최소 힙은 항상 루트(`_a[0]`)에 가장 작은 `expire_at`이 위치합니다.
   - 매 명령 전 `purge_expired()`에서 `heap.peek()[0] <= now`인지 **`O(1)`** 로 확인하고, 만료된 키가 없을 때는 즉시 루프를 끝내 추가 비용이 0에 가깝습니다.
   - 만료 키를 삽입(`EXPIRE` → `push`)하거나 만료된 루트를 꺼낼 때(`pop`)도 **`O(log n)`** 으로 매우 빠릅니다. (매번 전체 해시맵을 순회하면 `O(n)`이 걸려 키가 많을수록 급격히 느려집니다.)
2. **상태 불일치와 중간 삭제 약점 해결 → Lazy Deletion(지연 삭제)**:
   - 키가 `DEL`되거나 `SET`/`EXPIRE`로 덮어쓰여도 힙 배열 중간을 뒤져 지우지 않습니다(`O(n)` 회피).
   - 대신 나중에 힙 루트에서 `(expire_at, key)`를 `pop()`했을 때, 해시맵의 현재 `Entry`를 조회해 **`entry is not None and entry.expire_at == expire_at`** 일 때만 진짜 만료로 삭제하고, 불일치하는 옛 힙 레코드는 조용히 버립니다.

### 4) 평가 모범 답변 (요약)
> "TTL 청소에서는 모든 키를 만료 순으로 정렬할 필요 없이 '가장 빨리 만료될 키'만 빠르게 알면 됩니다. 최소 힙은 루트 조회(`peek`)가 `O(1)`이라 만료된 키가 없을 때 즉시 종료할 수 있고, 삽입·삭제가 `O(log n)`이므로 전체 키 스캔(`O(n)`)보다 훨씬 효율적입니다. 또한 `DEL`이나 `SET` 덮어쓰기로 낡은 힙 항목은 pop 시 현재 `Entry.expire_at`과 비교해 무시하는 Lazy Deletion으로 정합성과 성능을 모두 확보했습니다."

---

## 문항 3-4. 메모리 초과 시 eviction 흐름을 단계별로 설명할 수 있는가? (`used_memory` 산정/갱신, LRU 제거, `evicted_keys` 증가 포함)

### 1) 질문 의도 해석
- `SET` 또는 `CONFIG SET maxmemory`로 메모리 한도 초과 상황이 발생했을 때, 내부에서 어떤 순서로 크기를 산정하고 예외(`OOM`)를 가려내며, LRU 방출과 지표 갱신이 어떤 단계를 밟아 일어나는지 정확히 추적하는지 평가합니다.

### 2) 단계별 실행 흐름 (`mini_redis/string_commands.py`, `memory.py`, `mini_redis.py`)
1. **1단계 — 사전 만료 정리 & 단일 엔트리 크기 산정**:
   - 명령 진입 시 `purge_expired()` 실행 후 `set_key` 내부에서 `expire_if_needed(key)`로 대상 키의 만료 여부를 정리합니다.
   - `new_size = len(key.encode("utf-8")) + len(value.encode("utf-8"))`로 엔트리 크기를 계산합니다.
2. **2단계 — 단일 엔트리 한도 검사 (OOM 가드)**:
   - `maxmemory > 0`이고 `new_size > maxmemory`라면 기존 키를 전부 비워도 이 키 하나를 담을 수 없으므로, 기존 데이터를 건드리지 않고 **`OOMError` 예외**를 발생시켜 `(error) OOM command not allowed when used_memory > 'maxmemory'`를 반환합니다.
3. **3단계 — 저장 및 `used_memory` 갱신 + LRU 최신화**:
   - **기존 키 덮어쓰기**: `used_memory += new_size - old_size`로 차분만 반영, `entry.expire_at = None`(TTL 초기화), `move_to_front(entry.lru_node)`.
   - **신규 키 삽입**: `_lru.insert_front(key)`로 새 노드를 맨 앞에 추가하고 `Entry`를 해시맵에 `put`, `used_memory += new_size`.
4. **4단계 — 한도 초과분 LRU 반복 방출 (`evict_if_needed`)**:
   - `while self.maxmemory > 0 and self.used_memory > self.maxmemory:` 조건 동안 반복합니다.
   - `_lru.tail.data`에서 가장 오래 사용되지 않은 키(`oldest_key`)를 꺼냅니다.
   - 공통 삭제 **`delete_entry(oldest_key)`** 를 호출해 ① `_lru.remove_node` ② `_map.remove` ③ `used_memory -= calc_entry_size(oldest_key, entry.value)`를 한 번에 처리합니다.
   - 방출 1건 완료마다 **`evicted_keys += 1`** 을 증가시킵니다.
   - *(방금 저장한 키는 `head`에 있고 `new_size <= maxmemory`이므로 자기 자신이 방출되지 않고 안전하게 살아남습니다.)*

### 3) 평가 모범 답변 (요약)
> "`SET` 시 먼저 UTF-8 바이트 기준으로 `new_size`를 산정해 단독으로 `maxmemory`를 넘으면 즉시 OOM 에러를 냅니다. 통과하면 해시맵과 LRU 맨 앞에 반영하고 `used_memory`를 갱신한 뒤, `used_memory > maxmemory`인 동안 `evict_if_needed()`가 LRU 리스트의 `tail` 키를 반복 꺼내 `delete_entry()`로 해시맵·리스트·`used_memory`에서 제거하고 `evicted_keys`를 1씩 올립니다."

---

## 문항 3-5. `GET` 명령어 전체 흐름을 순서대로 설명할 수 있는가? (TTL 확인 → 삭제 여부 → 값 반환 → LRU 갱신 조건)

### 1) 질문 의도 해석
- 단순 조회처럼 보이는 `GET` 명령 내부에서 **만료 확인이 LRU 갱신보다 먼저 와야 하는 이유**와, **어떤 경우에만 LRU를 갱신하고 어떤 경우에는 갱신하지 않는지** 상태 전이 순서를 정확히 이해하고 있는지 확인합니다.

### 2) 단계별 실행 흐름 (`mini_redis/main.py` → `string_commands.py` → `ttl.py`)
1. **0단계 — 명령 파싱 및 전역 만료 청소 (`execute`)**:
   - `tokenize()`로 인자 1개 검증 후 `store.purge_expired()`로 힙에 쌓인 만료 키를 먼저 정리합니다.
2. **1단계 — 대상 키 TTL 만료 확인 (`expire_if_needed`)**:
   - 해시맵에서 `entry`를 찾아 `entry.expire_at is not None and clock() >= entry.expire_at`인지 확인합니다.
   - **만료됨 → 삭제 분기**: 즉시 `delete_entry(key)`로 해시맵·LRU 리스트·`used_memory`에서 제거한 뒤 `None`을 반환합니다(CLI 출력: `(nil)`). **이미 죽은 키이므로 LRU를 갱신하지 않습니다.**
3. **2단계 — 해시맵 존재 여부 확인**:
   - `entry = self._map.get(key)` 조회.
   - **`entry is None` → 미존재 분기**: 키가 없으므로 `None`을 반환합니다(CLI 출력: `(nil)`). **없는 키이므로 LRU를 갱신할 노드도 없고 갱신해서도 안 됩니다.**
4. **3단계 — LRU 갱신 조건 충족 및 실행**:
   - 앞의 두 관문을 모두 통과해 **"만료되지 않고 실제로 존재하는 키"** 일 때만 `self._lru.move_to_front(entry.lru_node)`를 호출해 해당 노드를 `head`(가장 최근 사용)로 `O(1)` 이동합니다.
5. **4단계 — 값 반환**:
   - `entry.value`를 꺼내 CLI에서 `'"%s"' % value` 형식으로 출력합니다.

### 3) 평가 모범 답변 (요약)
> "`GET`은 **① TTL 만료 확인 → ② 만료 시 삭제 후 `(nil)` 반환(LRU 미갱신) → ③ 해시맵 미존재 시 `(nil)` 반환(LRU 미갱신) → ④ 유효 키가 존재할 때만 `move_to_front()`로 LRU 갱신 → ⑤ 값 반환** 순서로 동작합니다. 만료 검사를 가장 먼저 배치해 만료된 키가 잠깐이라도 다시 살아나거나 LRU 순위를 어지럽히는 문제를 차단했습니다."
