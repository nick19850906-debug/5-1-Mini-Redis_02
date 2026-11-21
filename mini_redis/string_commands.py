"""String 명령어 모듈 (해시맵 + LRU 리스트 + TTL 조율기를 통한 6종 기본 연산).

[실생활 비유]
  도서관 대출/반납 창구의 6가지 기본 업무입니다.
  1. set_key   : 새 책 등록 또는 기존 책 내용 교체 (SET)
  2. get_key   : 책 꺼내 보기 + 최근 읽은 책 맨 앞 이동 (GET)
  3. delete_key: 책 폐기 (DEL)
  4. exists_key: 책 보유 여부 확인 (EXISTS)
  5. dbsize_keys: 전체 보유 권수 확인 (DBSIZE)
  6. all_keys  : 전체 책 제목 목록 보기 (KEYS)
"""
from .memory import calc_entry_size


def set_key(redis_store, key, value):
    """1. 키 값 저장 함수 (SET): 해시맵 저장, LRU 맨 앞 이동, TTL 초기화, 초과 시 자동 방출."""
    # 먼저 이 키가 만료 상태였다면 정리
    redis_store.ttl_manager.expire_if_needed(redis_store, key)

    new_size = calc_entry_size(key, value)
    # 단일 키+값만으로도 maxmemory를 넘으면 저장하지 않고 OOMError 발생
    redis_store.memory.check_single_entry_fit(new_size)

    entry = redis_store._map.get(key)
    if entry is not None:
        # 이미 존재하는 키 덮어쓰기: 사용량 차분 반영 + TTL 초기화(-1) + LRU 맨 앞으로 이동
        old_size = calc_entry_size(key, entry.value)
        redis_store.memory.used_memory += new_size - old_size
        entry.value = value
        entry.expire_at = None  # 덮어쓰기 시 기존 TTL은 해제됨 (힙의 옛 기록은 lazy deletion)
        redis_store._lru.move_to_front(entry.lru_node)
    else:
        # 신규 키 삽입: LRU 리스트 맨 앞에 노드 생성 -> Entry에 노드 연결 -> 해시맵 저장
        node = redis_store._lru.insert_front(key)
        entry = redis_store.create_entry(value, node)
        redis_store._map.put(key, entry)
        redis_store.memory.used_memory += new_size

    # 메모리 한도 초과 시 가장 오래된 키(tail)부터 제거
    redis_store.memory.evict_if_needed(redis_store)


def get_key(redis_store, key):
    """2. 키 값 조회 함수 (GET): 만료 확인 -> 삭제 여부 -> 값 반환 -> 존재 시에만 LRU 갱신."""
    # 1) TTL 만료 여부 확인 (만료됐으면 삭제하고 None 반환, LRU 갱신 안 함!)
    if redis_store.ttl_manager.expire_if_needed(redis_store, key):
        return None
    # 2) 해시맵에서 Entry 조회 (없으면 None 반환, LRU 갱신 안 함)
    entry = redis_store._map.get(key)
    if entry is None:
        return None
    # 3) 유효한 키가 존재할 때만 LRU 리스트 맨 앞으로 이동(O(1))
    redis_store._lru.move_to_front(entry.lru_node)
    # 4) 저장된 문자열 값 반환
    return entry.value


def delete_key(redis_store, key):
    """3. 키 삭제 함수 (DEL): 만료 정리 후 공통 삭제 로직으로 해시맵·LRU·메모리를 함께 정리합니다."""
    redis_store.ttl_manager.expire_if_needed(redis_store, key)
    return redis_store.delete_entry(key)


def exists_key(redis_store, key):
    """4. 키 존재 확인 함수 (EXISTS): 만료 확인 후 키 존재 여부(True/False)를 반환합니다."""
    redis_store.ttl_manager.expire_if_needed(redis_store, key)
    return redis_store._map.contains(key)


def dbsize_keys(redis_store):
    """5. 키 개수 반환 함수 (DBSIZE): 만료 청소를 반영한 현재 유효 키 개수를 반환합니다."""
    redis_store.purge_expired()
    return redis_store._map.size()


def all_keys(redis_store):
    """6. 키 전체 조회 함수 (KEYS): 만료 청소를 반영한 전체 키 목록을 반환합니다."""
    redis_store.purge_expired()
    return redis_store._map.keys()
