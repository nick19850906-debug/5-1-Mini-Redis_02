"""메모리 관리 및 LRU 자동 제거(Eviction) 모듈.

[실생활 비유]
  책상(maxmemory) 크기를 재고 관리하는 집사입니다.
  - 현재 책상 위에 올라간 책들의 무게(used_memory)를 계산하고,
  - 한도(maxmemory)가 꽉 차서 넘치면 가장 오래 펼치지 않은 책(LRU tail)부터 서랍으로 치웁니다.
  - 몇 권을 치웠는지(evicted_keys) 장부에 기록합니다.

[메모리 계산 규칙]
  used_memory = 현재 저장된 모든 키에 대해 len(utf8(key)) + len(utf8(value)) 의 합계.
  (단순화 모델: Node, Entry, 버킷 포인터 등의 파이썬 객체 오버헤드는 제외합니다.)
"""
from .errors import OOMError


def calc_entry_size(key, value):
    """키와 값의 UTF-8 바이트 길이를 합산해 엔트리 1개의 논리적 메모리 크기를 계산합니다."""
    return len(key.encode("utf-8")) + len(value.encode("utf-8"))


class MemoryManager:
    """메모리 제한 설정, 사용량 조회, 최대치 조회, 제거된 키 개수 반환 및 LRU 방출 담당."""

    def __init__(self):
        self.used_memory = 0   # 현재 사용 중인 메모리 크기(바이트)
        self.maxmemory = 0     # 허용 최대 메모리(바이트). 0이면 제한 없음(무제한)
        self.evicted_keys = 0  # maxmemory 초과로 자동 제거(evict)된 총 키 개수

    def set_maxmemory(self, redis_store, limit):
        """1. 메모리 제한 설정 함수: maxmemory를 변경하고 이미 초과 상태면 즉시 LRU 제거를 수행합니다."""
        self.maxmemory = limit
        self.evict_if_needed(redis_store)

    def get_used_memory(self):
        """2. 메모리 사용량 조회 함수: 현재 used_memory(바이트)를 반환합니다."""
        return self.used_memory

    def get_maxmemory(self):
        """3. 메모리 최대치 조회 함수: 현재 maxmemory(바이트)를 반환합니다."""
        return self.maxmemory

    def get_evicted_keys(self):
        """4. 제거된 키 개수 반환 함수: 지금까지 LRU로 쫓겨난 키 총 개수를 반환합니다."""
        return self.evicted_keys

    def check_single_entry_fit(self, entry_size):
        """단일 엔트리(key+value)만으로도 maxmemory를 초과하면 저장을 거부(OOMError)합니다."""
        if self.maxmemory > 0 and entry_size > self.maxmemory:
            raise OOMError()

    def evict_if_needed(self, redis_store):
        """used_memory가 maxmemory를 초과하는 동안 가장 오래된 키(LRU tail)를 반복 제거합니다."""
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            if redis_store._lru.tail is None:
                break
            oldest_key = redis_store._lru.tail.data
            # 공통 삭제 메서드(delete_entry)를 호출해 해시맵·LRU 리스트·used_memory를 한꺼번에 갱신
            if not redis_store.delete_entry(oldest_key):
                break
            self.evicted_keys += 1

    def info_memory(self):
        """INFO memory 명령어의 표준 3줄 출력 문자열을 생성합니다."""
        return "used_memory:%d\nmaxmemory:%d\nevicted_keys:%d" % (
            self.used_memory,
            self.maxmemory,
            self.evicted_keys,
        )
