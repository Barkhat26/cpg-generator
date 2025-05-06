from typing import Generic, TypeVar, List, Type

T = TypeVar('T')


class Stack(Generic[T]):
    def __init__(self, item_type: Type[T]):
        self._items: List[T] = []
        self._item_type = item_type

    def push(self, item: T):
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

    def peek(self) -> T:
        return self._items[-1]

    def isEmpty(self) -> bool:
        return len(self._items) == 0

    def clear(self):
        self._items.clear()


class Queue(Generic[T]):
    def __init__(self, item_type: Type[T]):
        self.items: List[T] = []
        self.current = -1
        self._item_type = item_type

    def push(self, item: T):
        self.items.insert(0, item)

    def pop(self) -> T:
        return self.items.pop()

    def peek(self) -> T:
        return self.items[-1]

    def size(self) -> int:
        return len(self.items)

    def isEmpty(self) -> bool:
        return len(self.items) == 0

    def clear(self):
        self.items.clear()

    def __iter__(self):
        self.current = len(self.items) - 1
        return self

    def __next__(self):
        if self.current < 0:
            raise StopIteration
        el = self.items[self.current]
        self.current -= 1
        return el