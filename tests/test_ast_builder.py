from pathlib import Path

from graph_builders import ASTBuilder
from storage import ASTStorage


def test_build_from_file():
    source_file = Path(__file__).resolve().parent /  "assets" / "helloworld.java"
    ast = ASTBuilder.build_from_file(source_file)
    assert len(list(ast.nodes)) == 22
    assert len(list(ast.edges)) == 21


def test_build_from_string():
    code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, world!");
    }
}
    """

    ast = ASTBuilder.build_from_string(code)
    ast.export()

    storage = ASTStorage("ast_graph", overwrite=True)
    storage.dump(ast.g)

    g = storage.load()
    assert len(list(g.nodes())) == 22
    assert len(list(g.edges())) == 21
