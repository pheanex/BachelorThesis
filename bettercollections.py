import collections
class Counter2(collections.Counter):
    def __add__(self, other):
        if not isinstance(other, Counter2):
            return NotImplemented
        result = Counter2()
        for elem, count in self.items():
            newcount = count + other[elem]
            result[elem] = newcount
        for elem, count in other.items():
            if elem not in self:
                result[elem] = count
        return result

