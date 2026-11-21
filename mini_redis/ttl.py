"""TTL (Time To Live, 만료 시간) 관리 및 최소 힙 Lazy Deletion 모듈.

[실생활 비유]
  유통기한 관리 담당자입니다.
  1) EXPIRE key N: 상품(키)에 '현재 시각 + N초'짜리 유통기한 스티커를 붙이고,
     가장 임박한 순서대로 냉장고 알림판(최소 힙)에 메모해 둡니다.
  2) TTL key: 냉장고를 열어 남은 시간을 알려 줍니다. (없는 키 -2, 기한 없음 -1)
  3) Lazy Deletion(지연 삭제):
     사용자가 DEL로 미리 버렸거나 SET으로 새 상품을 덮어써도,
     힙 안의 옛날 메모를 억지로 찾아 지우지 않습니다(중간 삭제 O(n) 방지).
     나중에 힙 맨 위에서 꺼낼 때 실제 해시맵의 현재 만료 시각과 비교해 다르면 그냥 버립니다.
"""
import time


class TTLManager:
    """키 만료 시간 설정, 남은 시간 조회, 만료 키 청소 담당."""

    def __init__(self, clock=time.time):
        # 현재 시각을 알려 주는 시계 함수 (실제 실행은 time.time, 테스트에서는 가짜 시계 주입)
        self._clock = clock

    def now(self):
        """현재 시각(초 단위 float)을 반환합니다."""
        return self._clock()

    def expire_if_needed(self, redis_store, key):
        """특정 키에 접근하기 직전에 만료 여부를 확인(Passive Expiration)합니다.

        만료 시각이 현재 시각 이하(clock >= expire_at)이면 공통 삭제(delete_entry)로 제거하고 True 반환.
        """
        entry = redis_store._map.get(key)
        if entry is not None and entry.expire_at is not None and self._clock() >= entry.expire_at:
            redis_store.delete_entry(key)
            return True
        return False

    def purge_expired(self, redis_store):
        """명령 실행 전 최소 힙 루트(peek)부터 확인해 만료된 키들을 일괄 정리(Active Expiration)합니다.

        Lazy Deletion 검증:
          힙에서 꺼낸 (expire_at, key)가 현재 해시맵에 남아 있는 Entry의 expire_at과
          정확히 일치할 때만 진짜 만료된 것이므로 삭제합니다.
          이미 DEL로 지워졌거나 EXPIRE/SET으로 덮어쓰여 만료 시각이 달라진 옛 기록은 무시합니다.
        """
        current_time = self._clock()
        heap = redis_store._heap
        while heap.peek() is not None and heap.peek()[0] <= current_time:
            expire_at, key = heap.pop()
            entry = redis_store._map.get(key)
            if entry is not None and entry.expire_at == expire_at:
                redis_store.delete_entry(key)

    def expire(self, redis_store, key, seconds):
        """1. 키 만료시간 설정 함수: 성공 시 1, 키가 없으면 0을 반환합니다.

        seconds가 0 이하이면 즉시 만료로 간주하여 키를 삭제한 뒤 1을 반환합니다.
        """
        self.expire_if_needed(redis_store, key)
        entry = redis_store._map.get(key)
        if entry is None:
            return 0
        if seconds <= 0:
            redis_store.delete_entry(key)
            return 1
        entry.expire_at = self._clock() + seconds
        redis_store._heap.push((entry.expire_at, key))
        return 1

    def ttl(self, redis_store, key):
        """2. 키 남은시간 조회 함수: 없는 키 -2, 만료 미설정 -1, 설정된 경우 남은 초(int)를 반환합니다."""
        if self.expire_if_needed(redis_store, key):
            return -2
        entry = redis_store._map.get(key)
        if entry is None:
            return -2
        if entry.expire_at is None:
            return -1
        remaining = int(entry.expire_at - self._clock())
        return remaining if remaining >= 0 else 0
