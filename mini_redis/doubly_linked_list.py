"""이중 연결 리스트 (Doubly Linked List) 모듈.

[실생활 비유]
  사람들이 줄을 설 때 각 사람이 '앞사람 손(prev)'과 '뒷사람 손(next)'을 양손으로 잡은 모습입니다.
  중간에 있는 한 사람이 줄에서 빠지거나 맨 앞으로 이동해도,
  줄 전체를 처음부터 끝까지 다시 세울 필요 없이 양옆 사람의 손잡기(포인터 2~4개)만 바꾸면 되므로
  항상 O(1) 시간에 끝납니다.

[구역]
  1구역: Node 클래스 (데이터와 앞뒤 포인터를 담는 한 칸)
  2구역: DoublyLinkedList 클래스 (head~tail 관리 및 O(1) 삽입·삭제·이동 메서드)
"""


# ===== 1구역: 노드(Node) 구조 =====
class Node:
    """이중 연결 리스트의 노드 한 개.

    Attributes:
        prev: 앞쪽 노드를 가리키는 참조(없으면 None)
        next: 뒤쪽 노드를 가리키는 참조(없으면 None)
        data: 노드에 저장하는 실제 데이터(예: LRU에서는 키 문자열, 해시맵 버킷에서는 [키, 값])
    """

    def __init__(self, data):
        self.prev = None  # 내 앞사람 주소 (맨 앞이면 None)
        self.next = None  # 내 뒷사람 주소 (맨 뒤면 None)
        self.data = data  # 내가 보관하는 실제 값


# ===== 2구역: 이중 연결 리스트(DoublyLinkedList) =====
class DoublyLinkedList:
    """head(맨 앞)와 tail(맨 뒤)을 유지하여 삽입/삭제/이동을 O(1)에 처리하는 리스트.

    LRU 캐시로 사용할 때:
      - head 쪽: 가장 최근에 사용된(MRU) 키
      - tail 쪽: 가장 오래 사용되지 않은(LRU) 키 -> 메모리 초과 시 가장 먼저 제거
    """

    def __init__(self):
        self.head = None  # 맨 앞 노드의 주소 (비어 있으면 None)
        self.tail = None  # 맨 뒤 노드의 주소 (비어 있으면 None)
        self._size = 0    # 현재 리스트에 들어 있는 노드 개수 (len() 호출 시 O(1) 반환)

    def __len__(self):
        """len(리스트) 호출 시 저장된 노드 개수를 O(1)로 반환합니다."""
        return self._size

    def _link_front(self, node):
        """이미 생성된 노드를 리스트의 맨 앞(head)에 연결하는 내부 공통 도우미. O(1)"""
        node.prev = None            # 맨 앞에 서므로 앞사람은 없음
        node.next = self.head       # 새 맨 앞 노드의 뒷사람은 기존 맨 앞(head)
        if self.head is not None:
            self.head.prev = node   # 기존 맨 앞 노드의 앞사람을 새 노드로 연결
        else:
            self.tail = node        # 리스트가 비어 있었다면 맨 뒤(tail)도 이 노드
        self.head = node            # head 표지판을 새 노드로 교체
        self._size += 1

    def insert_front(self, data):
        """새 데이터를 맨 앞(head)에 추가하고, 생성된 Node 객체를 반환합니다. O(1)"""
        node = Node(data)           # 새 노드 상자 생성
        self._link_front(node)      # 맨 앞 연결 로직 재사용
        return node                 # Entry가 이 노드 주소를 기억해야 나중에 O(1) 이동/삭제 가능

    def insert_back(self, data):
        """새 데이터를 맨 뒤(tail)에 추가하고, 생성된 Node 객체를 반환합니다. O(1)"""
        node = Node(data)
        node.prev = self.tail       # 내 앞사람은 기존 맨 뒤(tail)
        node.next = None            # 맨 뒤이므로 뒷사람은 없음
        if self.tail is not None:
            self.tail.next = node   # 기존 맨 뒤 노드의 뒷사람을 나로 연결
        else:
            self.head = node        # 리스트가 비어 있었다면 맨 앞(head)도 이 노드
        self.tail = node            # tail 표지판을 새 노드로 교체
        self._size += 1
        return node

    def remove_node(self, node):
        """노드 참조(주소)를 직접 받아 리스트에서 즉시 제거하고 data를 반환합니다. O(1)

        연결 리스트를 순회하지 않고 양옆 노드의 prev/next만 서로 이어 주므로 항상 O(1)입니다.
        """
        if node.prev is not None:
            node.prev.next = node.next  # 내 앞사람이 내 뒷사람의 손을 잡도록 변경
        else:
            self.head = node.next       # 내가 맨 앞이었다면 내 뒷사람이 새로운 head

        if node.next is not None:
            node.next.prev = node.prev  # 내 뒷사람이 내 앞사람의 손을 잡도록 변경
        else:
            self.tail = node.prev       # 내가 맨 뒤였다면 내 앞사람이 새로운 tail

        node.prev = None                # 제거된 노드의 포인터를 비워 참조 누수 방지
        node.next = None
        self._size -= 1
        return node.data

    def remove_front(self):
        """맨 앞(head) 노드를 제거하고 그 data를 반환합니다. 비어 있으면 None. O(1)"""
        if self.head is None:
            return None
        return self.remove_node(self.head)

    def remove_back(self):
        """맨 뒤(tail) 노드를 제거하고 그 data를 반환합니다. (LRU 방출 대상) 비어 있으면 None. O(1)"""
        if self.tail is None:
            return None
        return self.remove_node(self.tail)

    def move_to_front(self, node):
        """이미 리스트 안에 있는 노드를 맨 앞(head)으로 옮깁니다. (최근 사용 갱신) O(1)"""
        if node is self.head:
            return                  # 이미 맨 앞(가장 최근 사용)이면 이동할 필요 없음
        self.remove_node(node)      # 1단계: 현재 자리에서 포인터만 끊어 분리 (O(1))
        self._link_front(node)      # 2단계: 기존 node 객체를 그대로 맨 앞에 다시 연결 (O(1))
