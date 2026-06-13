from collections import defaultdict


class UnionFind:
    """并查集，支持传递性分组。"""

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1

    def groups(self):
        """返回所有大小 > 1 的分组。"""
        buckets = defaultdict(list)
        for i in range(len(self.parent)):
            buckets[self.find(i)].append(i)
        return [g for g in buckets.values() if len(g) > 1]
