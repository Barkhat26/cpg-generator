from pathlib import Path

from graph_builders import CFGBuilder
from storage import CFGStorage


def test_build_from_file():
    source_file = Path(__file__).resolve().parent / "assets" / "helloworld.java"
    cfg = CFGBuilder.build_from_file(source_file)
    assert len(list(cfg.nodes)) == 2
    assert len(list(cfg.edges)) == 1
    assert True


def test_build_from_string():
    code = """
public class Example {

    public static void main(String[] args) {
        String[] names = {"Alice", "Bob", "Charlie", null};

        for (int i = 0; i < names.length; i++) {
            try {
                String name = names[i];

                if (name != null && name.startsWith("A")) {
                    System.out.println("Name starts with A: " + name);
                } else {
                    System.out.println("Other name: " + name);
                }

            } catch (Exception e) {
                System.out.println("⚠️ Exception at index " + i + ": " + e.getMessage());
            }
        }
    }
}
"""
    cfg = CFGBuilder.build_from_string(code)
    cfg.export()
    storage = CFGStorage("test2", overwrite=True)

    storage.dump(cfg.g)

    g = storage.load()

    assert len(list(g.nodes())) == 16
    assert len(list(g.edges())) == 18
