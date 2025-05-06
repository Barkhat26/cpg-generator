from log import general_logger as logger


class TraversalBuilder:
    def __init__(self, steps=None):
        self.steps = steps or []

    def __getattr__(self, name):
        def step_fn(*args, **kwargs):
            return TraversalBuilder(self.steps + [(name, args, kwargs)])

        return step_fn

    def apply(self, query):
        for name, args, kwargs in self.steps:
            method = getattr(query, name)
            query = method(*args, **kwargs)
        return query

    def and_(self, *sub_traversals):
        def and_logic(query):
            return all(
                traversal.apply(Query(query.graph, [n])).current_nodes
                for traversal in sub_traversals
                for n in query.current_nodes
            )

        return TraversalBuilder(self.steps + [("filter", (and_logic,), {})])

    def or_(self, *sub_traversals):
        def or_logic(query):
            return any(
                traversal.apply(Query(query.graph, [n])).current_nodes
                for traversal in sub_traversals
                for n in query.current_nodes
            )

        return TraversalBuilder(self.steps + [("filter", (or_logic,), {})])

    def not_(self, sub_traversal):
        def not_logic(query):
            return all(
                not sub_traversal.apply(Query(query.graph, [n])).current_nodes
                for n in query.current_nodes
            )

        return TraversalBuilder(self.steps + [("filter", (not_logic,), {})])


__ = TraversalBuilder()


class Query:
    def __init__(self, graph, nodes=None, edges=None, mode="nodes"):
        self.graph = graph
        self.current_nodes = set(nodes) if nodes is not None else set(graph.nodes)
        self.current_edges = set(edges) if edges is not None else set()
        self.mode = mode  # "nodes" or "edges"
        self._paths = {n: [[n]] for n in self.current_nodes} if nodes else None

        # repeat support
        self._repeat_fn = None
        self._repeat_times = None
        self._repeat_until = None
        self._repeat_emit = False
        self._repeat_emit_condition = None
        self._repeat_depth = 0

    def V(self, *node_ids):
        self.mode = "nodes"
        self.current_nodes = set(node_ids) if node_ids else set(self.graph.nodes)
        self._paths = {n: [[n]] for n in self.current_nodes}
        return self

    def has(self, key, value):
        if self.mode == "nodes":
            self.current_nodes = {
                n for n in self.current_nodes
                if self.graph.nodes[n].get(key) == value
            }
            if self._paths:
                self._paths = {n: self._paths[n] for n in self.current_nodes if n in self._paths}
        elif self.mode == "edges":
            self.current_edges = {
                e for e in self.current_edges
                if self.graph.edges[e].get(key) == value
            }
        return self

    def out(self):
        next_nodes = set()
        new_paths = {}
        for n in self.current_nodes:
            neighbors = self.graph.successors(n) if self.graph.is_directed() else self.graph.neighbors(n)
            for nbr in neighbors:
                next_nodes.add(nbr)
                if self._paths:
                    for path in self._paths.get(n, []):
                        new_paths.setdefault(nbr, []).append(path + [nbr])
        self.current_nodes = next_nodes
        if self._paths:
            self._paths = new_paths
        self.mode = "nodes"
        return self

    def in_(self):
        if not self.graph.is_directed():
            return self.out()
        next_nodes = set()
        new_paths = {}
        for n in self.current_nodes:
            for pred in self.graph.predecessors(n):
                next_nodes.add(pred)
                if self._paths:
                    for path in self._paths.get(n, []):
                        new_paths.setdefault(pred, []).append(path + [pred])
        self.current_nodes = next_nodes
        if self._paths:
            self._paths = new_paths
        self.mode = "nodes"
        return self

    def outE(self):
        edge_set = set()
        for n in self.current_nodes:
            for succ in self.graph.successors(n) if self.graph.is_directed() else self.graph.neighbors(n):
                edge_set.add((n, succ))
        self.current_edges = edge_set
        self.mode = "edges"
        return self

    def inE(self):
        if not self.graph.is_directed():
            return self.outE()
        edge_set = set()
        for n in self.current_nodes:
            for pred in self.graph.predecessors(n):
                edge_set.add((pred, n))
        self.current_edges = edge_set
        self.mode = "edges"
        return self

    def outV(self):
        self.current_nodes = {u for (u, _) in self.current_edges}
        self.mode = "nodes"
        return self

    def inV(self):
        self.current_nodes = {v for (_, v) in self.current_edges}
        self.mode = "nodes"
        return self

    def values(self, key):
        if self.mode == "nodes":
            return [self.graph.nodes[n].get(key) for n in self.current_nodes]
        elif self.mode == "edges":
            return [self.graph.edges[e].get(key) for e in self.current_edges]

    def valueMap(self):
        if self.mode != "nodes":
            raise ValueError("valueMap() применяется только к вершинам")
        return [self.graph.nodes[n] for n in self.current_nodes]

    def nodes(self):
        return list(self.current_nodes)

    def edges(self):
        return list(self.current_edges)

    def path(self):
        if not self._paths:
            return [[n] for n in self.current_nodes]
        paths = []
        for path_list in self._paths.values():
            paths.extend(path_list)
        return paths

    def where(self, traversal):
        if isinstance(traversal, TraversalBuilder):
            return self.filter(lambda q: traversal.apply(q).current_nodes)
        else:
            raise TypeError("where(...) принимает только TraversalBuilder (__)")

    def filter(self, fn):
        self.current_nodes = {n for n in self.current_nodes if fn(Query(self.graph, [n]))}
        return self

    def as_(self, label):
        if not hasattr(self, "_aliases"):
            self._aliases = {}
        self._aliases[label] = list(self.current_nodes)
        return self


    def select(self, *labels):
        if not hasattr(self, "_aliases"):
            raise ValueError("Нет сохранённых alias через as_()")
        self._selected_labels = labels
        self._select_funcs = []
        return self


    def by(self, fn=None):
        if fn is None:
            fn = lambda nodes: list(nodes)[0] if nodes else None
        self._select_funcs.append(fn)
        if len(self._select_funcs) < len(self._selected_labels):
            return self
        return self._apply_select()


    def _apply_select(self):
        result = []
        zipped = zip(*[self._aliases[label] for label in self._selected_labels])
        for values in zipped:
            entry = {
                label: self._select_funcs[i](Query(self.graph, [node]))
                for i, (label, node) in enumerate(zip(self._selected_labels, values))
            }
            result.append(entry)
        return result

    def simplePath(self):
        if not self._paths:
            return self
        new_nodes = set()
        new_paths = {}
        for n in self.current_nodes:
            for path in self._paths.get(n, []):
                if len(path) == len(set(path)):  # все узлы уникальны
                    new_nodes.add(n)
                    new_paths.setdefault(n, []).append(path)
        self.current_nodes = new_nodes
        self._paths = new_paths
        return self

    # === repeat/emit/until/times ===
    def repeat(self, traversal, max_depth=None):
        if isinstance(traversal, TraversalBuilder):
            self._repeat_fn = lambda q: traversal.apply(q)
        else:
            self._repeat_fn = traversal

        self._repeat_times = None
        self._repeat_until = None
        self._repeat_emit = False
        self._repeat_emit_condition = None
        self._repeat_depth = 0
        self._repeat_max_depth = max_depth
        return self

    def times(self, n):
        self._repeat_times = n
        return self._run_repeat()

    def until(self, condition):
        if isinstance(condition, TraversalBuilder):
            self._repeat_until = lambda q: any(
                condition.apply(Query(self.graph, [n])).current_nodes
                for n in q.current_nodes
            )
        else:
            self._repeat_until = condition
        return self._run_repeat()

    def emit(self, condition=True):
        if isinstance(condition, TraversalBuilder):
            self._repeat_emit_condition = lambda q: any(
                condition.apply(Query(self.graph, [n])).current_nodes
                for n in q.current_nodes
            )
        elif callable(condition):
            self._repeat_emit_condition = condition
        elif condition is True:
            self._repeat_emit_condition = lambda q: True
        else:
            raise ValueError("emit(...) должен принимать TraversalBuilder, callable или True")

        # если until и times не заданы, сразу запускаем repeat
        if self._repeat_until is None and self._repeat_times is None:
            return self._run_repeat()
        return self

    def _run_repeat(self):
        seen_nodes = set()
        emitted_nodes = set()
        seen_paths = {}
        steps = 0
        max_steps = self._repeat_max_depth or 50
        depth_exceeded = False

        while True:
            if self._repeat_emit_condition and self._repeat_depth > 0:
                emit_now = {n for n in self.current_nodes if self._repeat_emit_condition(Query(self.graph, [n]))}
                emitted_nodes.update(emit_now)
                if self._paths:
                    for n in emit_now:
                        seen_paths.setdefault(n, []).extend(self._paths.get(n, []))

            if self._repeat_until and self._repeat_until(self):
                break
            if self._repeat_times is not None and steps >= self._repeat_times:
                break
            if steps >= max_steps:
                depth_exceeded = True
                break

            self._repeat_depth += 1
            self = self._repeat_fn(self)
            steps += 1

        if self._repeat_emit_condition:
            self.current_nodes = emitted_nodes
            if self._paths:
                self._paths = seen_paths

        if depth_exceeded and self._repeat_until:
            logger.debug(
                f"Traversal stopped at max_depth={max_steps} without meeting `until()` condition."
            )

        return self

