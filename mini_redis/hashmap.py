"""체이닝 기반 해시맵 (Hash Map) 직접 구현 모듈.

[실생활 비유]
  아파트 우편함 건물입니다.
  1) 해시 함수(hash_key): 입주민 이름(문자열 키)을 보고 몇 번 우편함(정수)으로 갈지 계산합니다.
  2) 버킷(buckets): 여러 개의 우편함 칸(배열)을 미리 만들어 둡니다.
  3) 충돌 해결(체이닝): 우연히 다른 두 사람이 같은 번호의 우편함에 배정되면,
     그 우편함 칸 안에 이중 연결 리스트로 줄을 세워 나란히 보관합니다.
  4) 리사이즈(2배 확장): 전체 편지 수 / 우편함 칸 수(로드 팩터)가 0.75를 넘으면
     우편함이 붐비기 시작하므로, 칸을 2배로 증축하고 모든 편지를 새 칸 번호에 맞춰 재배치(rehash)합니다.

[주의]
  파이썬 내장 dict, set, collections는 일절 사용하지 않습니다.
  파이썬 리스트([])는 오직 고정 길이 버킷 배열을 흉내 내기 위한 용도로만 사용합니다.

[구역]
  1구역: 상수 및 djb2 해시 함수 (hash_key)
  2구역: HashMap 기본 연산 (_find, put, get, contains, remove, keys)
  3구역: 로드 팩터 초과 시 버킷 2배 확장 (_resize)
"""
from .doubly_linked_list import DoublyLinkedList

# ===== 1구역: 상수 및 해시 함수 =====
LOAD_FACTOR_LIMIT = 0.75  # 로드 팩터(저장 항목 수 / 전체 버킷 수) 임계치


def hash_key(key):
    """문자열 키를 32비트 부호 없는 정수 해시값으로 변환합니다 (djb2 알고리즘).

    변환 과정:
      1) 초기값 h = 5381 에서 시작합니다. (영문/소문자 분포에서 충돌이 적다고 알려진 소수)
      2) key.encode("utf-8") 로 문자열을 바이트(0~255 정수) 시퀀스로 변환합니다.
         -> 한글, 이모지, 공백 등 모든 유니코드 키도 일관된 바이트열로 처리할 수 있습니다.
      3) 각 바이트 b마다 h = (h * 33 + b) & 0xFFFFFFFF 를 반복합니다.
         - * 33: 비트 시프트((h << 5) + h)와 같아 연산이 빠르고 글자 순서/차이를 크게 퍼뜨립니다.
         - & 0xFFFFFFFF: 32비트 범위(0 ~ 4,294,967,295) 안으로 잘라 파이썬 정수가 무한히 커지는 것을 막습니다.
    """
    h = 5381
    for b in key.encode("utf-8"):
        h = (h * 33 + b) & 0xFFFFFFFF
    return h


# ===== 2구역: 체이닝 해시맵 =====
class HashMap:
    """직접 구현한 체이닝 방식 해시맵.

    각 버킷은 충돌 시 항목들을 [key, value] 형태로 저장하는 DoublyLinkedList입니다.
    버킷 내부에 이중 연결 리스트를 선택한 이유:
      - 충돌이 발생한 체인 내에서 키를 찾은 뒤 삭제할 때,
        버킷.remove_node(node)로 리스트 중간 요소를 O(1)에 끊어 낼 수 있고,
      - 일반 파이썬 list.pop(i)처럼 뒤 요소를 한 칸씩 당기는 O(k) 비용이 들지 않습니다.
    """

    def __init__(self, capacity=8):
        cap = capacity if capacity >= 1 else 8
        # 버킷 배열: 각 칸마다 독립적인 이중 연결 리스트(체이닝 저장소)를 배치
        self._buckets = [DoublyLinkedList() for _ in range(cap)]
        self._size = 0  # 현재 해시맵에 저장된 전체 (key, value) 쌍 개수

    def size(self):
        """현재 저장된 키 개수를 O(1)로 반환합니다."""
        return self._size

    def bucket_count(self):
        """현재 버킷 배열의 전체 칸 수를 반환합니다."""
        return len(self._buckets)

    def _bucket_index(self, key):
        """해시값 % 전체 버킷 수 로 0 ~ (버킷수-1) 범위의 배열 인덱스를 구합니다."""
        return hash_key(key) % len(self._buckets)

    def _find(self, key):
        """키가 속할 (버킷 리스트, 해당 키의 Node 또는 None)을 반환합니다. 평균 O(1)"""
        bucket = self._buckets[self._bucket_index(key)]
        node = bucket.head
        while node is not None:
            if node.data[0] == key:  # node.data 는 [키, 값] 2칸 리스트
                return bucket, node
            node = node.next
        return bucket, None

    def put(self, key, value):
        """키와 값을 저장합니다. 이미 같은 키가 있으면 값만 덮어씁니다. 평균 O(1)"""
        bucket, node = self._find(key)
        if node is not None:
            node.data[1] = value     # 기존 키가 있으면 새 노드를 만들지 않고 값만 교체
            return
        bucket.insert_back([key, value])  # 새 키면 해당 버킷 체인 끝에 추가
        self._size += 1
        # 로드 팩터 = 현재 항목 수 / 버킷 수. 0.75 초과 시 버킷을 2배로 늘리고 재해싱
        if (self._size / len(self._buckets)) > LOAD_FACTOR_LIMIT:
            self._resize()

    def get(self, key):
        """키로 값을 조회합니다. 존재하지 않으면 None을 반환합니다. 평균 O(1)"""
        _, node = self._find(key)
        return node.data[1] if node is not None else None

    def contains(self, key):
        """키가 존재하는지 True/False로 반환합니다. 평균 O(1)"""
        _, node = self._find(key)
        return node is not None

    def remove(self, key):
        """키를 삭제합니다. 삭제에 성공하면 True, 키가 없었으면 False를 반환합니다. 평균 O(1)"""
        bucket, node = self._find(key)
        if node is None:
            return False
        bucket.remove_node(node)     # 이중 연결 리스트 덕분에 노드 참조만으로 O(1) 삭제
        self._size -= 1
        return True

    def keys(self):
        """해시맵에 들어 있는 모든 키 목록을 수집해 반환합니다. O(버킷수 + 항목수)"""
        result = []
        for bucket in self._buckets:
            node = bucket.head
            while node is not None:
                result.append(node.data[0])
                node = node.next
        return result

    # ===== 3구역: 버킷 2배 확장 및 재해싱 =====
    def _resize(self):
        """로드 팩터가 0.75를 초과했을 때 버킷을 2배로 늘리고 전체 항목을 재배치합니다.

        왜 반드시 전부 다시 계산(rehash)해야 하는가?
          - 기존 인덱스 = hash_key(k) % old_cap
          - 새 인덱스   = hash_key(k) % (old_cap * 2)
          나누는 수(모듈러)가 2배로 바뀌므로 기존 키들이 들어가야 할 버킷 번호도 달라집니다.
          재배치하지 않으면 이후 조회 시 엉뚱한 버킷을 뒤져서 키를 못 찾게 됩니다.
        """
        old_buckets = self._buckets
        new_capacity = len(old_buckets) * 2
        self._buckets = [DoublyLinkedList() for _ in range(new_capacity)]
        for bucket in old_buckets:
            node = bucket.head
            while node is not None:
                k, v = node.data
                new_idx = hash_key(k) % new_capacity
                self._buckets[new_idx].insert_back([k, v])
                node = node.next
