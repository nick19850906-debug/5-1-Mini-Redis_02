# 퍼실리테이터 1:1 평가 발표 대본 (미션 B5-1 Mini Redis)

> 그대로 읽으면 약 5분 분량입니다.  
> **사전 준비 (Windows CMD)**:  
> `cd C:\Users\domod\5-1-Mini-Redis_02`  
> `python scripts\evaluate-mission.py` → `RESULT: 12/12 PASS` 확인

---

## 1. 한 줄 소개 (20초)
"안녕하세요. Redis가 왜 정보를 빠르게 찾고 메모리를 관리하는지 직접 구현하며 확인하기 위해, 파이썬의 `dict`, `set`, `collections`를 일절 쓰지 않고 **해시맵·이중 연결 리스트·최소 힙**을 밑바닥부터 구현해 LRU와 TTL이 동작하는 CLI Mini Redis를 완성했습니다."

## 2. 아키텍처와 핵심 설계 문제 해결 (40초)
"프로젝트는 기능별로 `doubly_linked_list.py`, `hashmap.py`, `min_heap.py`, `string_commands.py`, `memory.py`, `ttl.py`, `errors.py`, `main.py`로 분리했습니다.  
특히 **'키는 하나인데 해시맵, LRU 리스트, TTL 힙 세 곳에서 관리할 때 상태가 어긋나는 문제'** 를 해결하기 위해 `mini_redis.py`를 중심 조율기로 두었습니다. 해시맵에 `Entry(value, lru_node, expire_at)` 객체를 저장하고, 모든 삭제는 공통 메서드 `delete_entry()` 한 곳을 통과해 세 구조가 항상 일관성을 유지하도록 설계했습니다."

## 3. 평가항목 핵심 답변 5대 포인트 (2분)
1. **해시맵 & 리사이즈**: "`djb2` 해시 함수로 UTF-8 바이트열을 32비트 정수로 바꾼 뒤 버킷 수로 나눈 나머지를 인덱스로 씁니다. 충돌은 버킷마다 이중 연결 리스트를 둔 체이닝으로 해결했고, 로드 팩터가 `0.75`를 넘으면 버킷을 2배로 늘리고 전원 재해싱합니다."
2. **`O(1)` LRU 원리**: "해시맵에서 키로 `Entry`를 평균 `O(1)`에 찾고, `Entry`가 쥔 `lru_node` 참조를 이중 연결 리스트 `move_to_front()`에 넘겨 앞뒤 포인터만 `O(1)`에 바꿉니다. 방출은 `tail`에서 즉시 꺼냅니다."
3. **TTL 최소 힙 & Lazy Deletion**: "가장 빨리 만료될 키 하나만 알면 되므로 최소 힙 루트(`peek`)를 `O(1)`로 확인합니다. 덮어쓰기나 삭제로 낡은 힙 항목은 pop할 때 현재 `Entry.expire_at`과 비교해 버리는 Lazy Deletion을 적용했습니다."
4. **Eviction 흐름**: "`SET` 시 UTF-8 바이트 합으로 `used_memory`를 늘리고 `maxmemory` 초과 동안 `tail` 키를 공통 삭제하며 `evicted_keys`를 1씩 증가시킵니다. 한 건만으로 한도를 넘기면 OOM 에러를 냅니다."
5. **`GET` 흐름**: "만료 확인 → 만료면 삭제 후 `(nil)`(LRU 갱신 안 함) → 없으면 `(nil)` → 유효할 때만 `move_to_front()`로 LRU 갱신 후 값을 반환합니다."

## 4. 라이브 시연 (1분 30초) — `python main.py`
```text
CONFIG SET maxmemory 30
SET user:1 "Alice"
SET user:2 "Bob"
SET user:3 "Charlie"
GET user:1                 -> (nil)   # LRU로 자동 제거됨
INFO memory                -> used_memory:22 / maxmemory:30 / evicted_keys:1
KEYS                       -> user:3, user:2 출력
EXPIRE user:2 3            -> (integer) 1
TTL user:2                 -> (integer) 2 또는 3
(3초 후) GET user:2        -> (nil)
CONFIG SET maxmemory abc   -> (error) ERR value is not an integer or out of range
GET                        -> (error) ERR wrong number of arguments for 'GET' command
HELLO                      -> (error) ERR unknown command 'HELLO'
quit
```

## 5. 심화 질문(항목 4) 즉답 요약 (30초)
- **LFU 전환**: "단일 리스트 대신 `freq → DoublyLinkedList` 해시맵과 `min_freq` 변수를 두고, `Entry`에 `freq`를 추가해 `O(1)` LFU를 구성합니다."
- **10만 건 병목**: "`_resize()` 일괄 재해싱은 점진적 재해싱으로, 대량 동시 만료는 배치 상한(Budget)으로, 낡은 힙 누적은 재구축 임계치로, `KEYS`는 `SCAN`으로, 파이썬 객체 메모리 오버헤드는 `__slots__`로 개선합니다."
- **오버헤드 포함 모델**: "작은 키도 수백 바이트가 되므로 테스트 `maxmemory` 스케일링과 고정 추상 바이트 모델 합의, 그리고 `DEL` 후 메모리 복원·방출 순서 중심 채점이 필요합니다."
