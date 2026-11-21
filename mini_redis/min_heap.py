"""최소 힙 (Min Heap) 직접 구현 모듈.

[실생활 비유]
  유통기한 임박 순으로 관리하는 냉장고 선반입니다.
  전체 음식을 유통기한 순서대로 1등부터 100등까지 줄 세우지 않고도(전체 정렬 O(n log n) 생략),
  '가장 유통기한이 빠른 음식 1개'만 맨 꼭대기(루트)에 올려 두어 O(1)로 바로 확인합니다.

[자료구조 원리]
  배열(파이썬 리스트 self._a) 하나로 완전 이진 트리를 표현합니다.
  - 루트(최솟값) 인덱스: 0
  - i번 노드의 부모 인덱스: (i - 1) // 2
  - i번 노드의 왼쪽 자식 인덱스: 2 * i + 1
  - i번 노드의 오른쪽 자식 인덱스: 2 * i + 2
  - 불변 조건(Min-Heap Property): 모든 부모의 값 <= 자식의 값

[TTL에서의 활용]
  항목 형태는 (expire_at, key) 튜플입니다.
  파이썬 튜플 비교 규칙상 첫 번째 원소인 expire_at(만료 시각)이 가장 작은 항목이 항상 맨 위에 옵니다.
"""


class MinHeap:
    """배열 기반 완전 이진 트리 최소 힙."""

    def __init__(self):
        self._a = []  # 힙 트리의 노드들을 레벨 순서로 담는 배열

    def size(self):
        """현재 힙에 저장된 항목 수를 반환합니다. O(1)"""
        return len(self._a)

    def peek(self):
        """가장 작은 항목(만료가 가장 임박한 항목)을 꺼내지 않고 확인합니다. 비었으면 None. O(1)"""
        return self._a[0] if self._a else None

    def push(self, item):
        """새 항목을 힙 맨 끝에 추가한 뒤, 부모와 비교해 위로 올립니다(_heapify_up). O(log n)"""
        self._a.append(item)
        self._heapify_up(len(self._a) - 1)

    def pop(self):
        """가장 작은 항목(루트)을 꺼내 반환하고, 힙 성질을 복구합니다. 비었으면 None. O(log n)"""
        if not self._a:
            return None
        top = self._a[0]             # 반환할 최솟값(루트) 보관
        last = self._a.pop()         # 배열의 맨 마지막 요소를 떼어 옴
        if self._a:
            self._a[0] = last        # 마지막 요소를 빈 루트 자리에 올린 뒤
            self._heapify_down(0)    # 자식과 비교해 자기 자리를 찾아 내려감
        return top

    def _heapify_up(self, i):
        """인덱스 i의 요소가 부모보다 작으면 맞바꾸며 위로 올라갑니다."""
        while i > 0:
            parent = (i - 1) // 2
            if self._a[i] >= self._a[parent]:
                break                # 부모가 나보다 작거나 같으면 최소 힙 규칙 만족 -> 종료
            self._a[i], self._a[parent] = self._a[parent], self._a[i]
            i = parent

    def _heapify_down(self, i):
        """인덱스 i의 요소를 왼쪽/오른쪽 자식 중 더 작은 쪽과 맞바꾸며 아래로 내립니다."""
        n = len(self._a)
        while True:
            smallest = i
            left = 2 * i + 1
            right = 2 * i + 2
            if left < n and self._a[left] < self._a[smallest]:
                smallest = left
            if right < n and self._a[right] < self._a[smallest]:
                smallest = right
            if smallest == i:
                return               # 두 자식보다 내가 작거나 같으면 제자리 -> 종료
            self._a[i], self._a[smallest] = self._a[smallest], self._a[i]
            i = smallest
