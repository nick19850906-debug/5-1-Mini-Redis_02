"""Mini Redis 전체 상태 조율 모듈 (Entry + MiniRedis).

[핵심 설계 문제 해결]
  '키는 하나인데 해시맵, 이중 연결 리스트(LRU), 최소 힙(TTL) 세 곳에서 관리하면 상태가 어긋나지 않을까?'
  해결 방법 2가지:
    1) Entry 객체 통합: 해시맵에 단순 값 대신 Entry(value, lru_node, expire_at)를 저장합니다.
       키로 해시맵을 한 번 조회하면 값뿐 아니라 LRU 리스트 노드 주소와 만료 시각을 즉시 얻습니다.
    2) 공통 삭제 메서드(delete_entry) + 힙 Lazy Deletion:
       키를 삭제할 때는 반드시 delete_entry(key) 한 곳을 통과해
       [LRU 리스트 노드 제거 -> 해시맵 제거 -> used_memory 감소]를 동시에 처리합니다.
       최소 힙은 중간 삭제가 O(n)이라 즉시 지우지 않고, pop 시 Entry.expire_at 일치 여부로 걸러 냅니다.
"""
import time

from .doubly_linked_list import DoublyLinkedList
from .hashmap import HashMap
from .memory import MemoryManager, calc_entry_size
from .min_heap import MinHeap
from .string_commands import all_keys, dbsize_keys, delete_key, exists_key, get_key, set_key
from .ttl import TTLManager


# ===== 1구역: 엔트리(Entry) 객체 =====
class Entry:
    """해시맵의 value 자리에 저장되는 통합 관리 객체.

    Attributes:
        value: 실제 저장된 문자열 값
        lru_node: 이중 연결 리스트 안에서 이 키가 위치한 Node 객체 (O(1) 이동/삭제용)
        expire_at: 만료 시각(초). 만료 시간이 설정되지 않았으면 None
    """

    def __init__(self, value, lru_node, expire_at=None):
        self.value = value
        self.lru_node = lru_node
        self.expire_at = expire_at

    @property
    def node(self):
        """lru_node의 짧은 별칭 (하위 호환용)."""
        return self.lru_node


# ===== 2구역: 전체 상태 조율기 (MiniRedis) =====
class MiniRedis:
    """해시맵, LRU 이중 연결 리스트, TTL 최소 힙이 항상 일관된 상태를 유지하도록 조율합니다."""

    def __init__(self, clock=time.time):
        self._map = HashMap()                 # 키 -> Entry 저장소 (평균 O(1) 조회)
        self._lru = DoublyLinkedList()        # 최근 사용 순서 관리 (head=최신, tail=가장 오래됨)
        self._heap = MinHeap()                # (expire_at, key) 만료 우선순위 큐
        self._clock = clock                   # 시간 공급 함수
        self.memory = MemoryManager()         # 메모리 사용량/한도/evicted_keys 관리자
        self.ttl_manager = TTLManager(clock)  # TTL 설정/조회/만료 청소 관리자

    @property
    def used_memory(self):
        return self.memory.used_memory

    @property
    def maxmemory(self):
        return self.memory.maxmemory

    @property
    def evicted_keys(self):
        return self.memory.evicted_keys

    def create_entry(self, value, lru_node):
        """Entry 객체 생성 도우미."""
        return Entry(value, lru_node)

    def delete_entry(self, key):
        """[공통 삭제 로직] 해시맵, LRU 리스트, used_memory를 한꺼번에 일관성 있게 제거합니다.

        힙에 남아 있을 수 있는 옛 만료 기록은 TTLManager.purge_expired에서
        Entry 존재 여부 및 expire_at 일치 검사(Lazy Deletion)를 통해 자동으로 폐기됩니다.
        """
        entry = self._map.get(key)
        if entry is None:
            return False
        self._lru.remove_node(entry.lru_node)
        self._map.remove(key)
        self.memory.used_memory -= calc_entry_size(key, entry.value)
        return True

    # 내부 별칭
    _delete = delete_entry

    # ----- TTL & 만료 청소 -----
    def purge_expired(self):
        """명령 실행 전 힙 루트부터 만료된 키들을 일괄 제거합니다."""
        self.ttl_manager.purge_expired(self)

    def expire(self, key, seconds):
        """EXPIRE 명령 위임."""
        return self.ttl_manager.expire(self, key, seconds)

    def ttl(self, key):
        """TTL 명령 위임."""
        return self.ttl_manager.ttl(self, key)

    # ----- String 명령 6종 -----
    def set(self, key, value):
        set_key(self, key, value)

    def get(self, key):
        return get_key(self, key)

    def delete(self, key):
        return delete_key(self, key)

    def exists(self, key):
        return exists_key(self, key)

    def dbsize(self):
        return dbsize_keys(self)

    def keys(self):
        return all_keys(self)

    # ----- 메모리 관리 명령 -----
    def set_maxmemory(self, limit):
        self.memory.set_maxmemory(self, limit)

    def get_used_memory(self):
        return self.memory.get_used_memory()

    def get_maxmemory(self):
        return self.memory.get_maxmemory()

    def get_evicted_keys(self):
        return self.memory.get_evicted_keys()

    def info_memory(self):
        return self.memory.info_memory()


# 기존 이름(Store)으로도 가져다 쓸 수 있도록 별칭 제공
Store = MiniRedis
