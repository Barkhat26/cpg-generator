import networkx as nx
import pytest
from graph_dsl import Query, __


@pytest.fixture
def simple_graph():
    G = nx.DiGraph()
    G.add_node("Alice", label="Person", name="Alice")
    G.add_node("Bob", label="Person", name="Bob")
    G.add_node("Cat", label="Animal", name="Whiskers")
    G.add_edge("Alice", "Bob", type="knows")
    G.add_edge("Alice", "Cat", type="owns")
    return G


def test_basic_node_filter(simple_graph):
    q = Query(simple_graph).V().has("label", "Person").values("name")
    assert set(q) == {"Alice", "Bob"}


def test_out_navigation(simple_graph):
    q = Query(simple_graph).V("Alice").out().values("name")
    assert set(q) == {"Bob", "Whiskers"}


def test_outE_filter_inV(simple_graph):
    q = Query(simple_graph).V("Alice").outE().has("type", "knows").inV().values("name")
    assert q == ["Bob"]


def test_inE_outV(simple_graph):
    q = Query(simple_graph).V("Bob").inE().has("type", "knows").outV().values("name")
    assert q == ["Alice"]


def test_repeat_until(simple_graph):
    G = nx.DiGraph()
    G.add_edges_from([
        ("A", "B"),
        ("B", "C"),
        ("C", "D"),
        ("D", "E"),
    ])
    G.add_node("E", kind="TARGET")

    q = Query(G).V("A").repeat(__.out()).until(__.has("kind", "TARGET"))
    assert q.nodes() == ["E"]


def test_edges(simple_graph):
    q = Query(simple_graph).V("Alice").outE().has("type", "knows").edges()
    assert ("Alice", "Bob") in q


def test_nodes(simple_graph):
    q = Query(simple_graph).V("Alice").nodes()
    assert q == ["Alice"]


def test_path_tracking(simple_graph):
    G = nx.DiGraph()
    G.add_edges_from([
        ("X", "Y"),
        ("Y", "Z"),
    ])
    q = Query(G).V("X").out().out()
    assert q.path() == [["X", "Y", "Z"]]
