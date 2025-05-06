from pathlib import Path

from graph_builders import AbstractSyntaxForestBuilder
from graph_builders import ASTBuilder
from graph_builders import CFGBuilder
from graph_builders import DFGBuilder
from graphs.ddg.dfg_edge import DFEdgeKind
from java.java_class_extractor import JavaClassExtractor


def test_build_from_string():
    code=r"""
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.IOException;

public class CommandExecutor {
    public static void main(String[] args) {
        System.out.print("Введите команду для выполнения: ");
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in))) {
            String command = reader.readLine();

            Process process = Runtime.getRuntime().exec(command);

            // Читаем вывод команды
            BufferedReader stdInput = new BufferedReader(new InputStreamReader(process.getInputStream()));
            BufferedReader stdError = new BufferedReader(new InputStreamReader(process.getErrorStream()));

            String s;
            System.out.println("Результат выполнения команды:\n");
            while ((s = stdInput.readLine()) != null) {
                System.out.println(s);
            }

            // Ошибки, если есть
            System.out.println("\nОшибки (если есть):\n");
            while ((s = stdError.readLine()) != null) {
                System.out.println(s);
            }

        } catch (IOException e) {
            System.out.println("Произошла ошибка при выполнении команды: " + e.getMessage());
        }
    }
}

    """
    ast = ASTBuilder.build_from_string(code)
    cfg = CFGBuilder.build_from_string(code)
    java_classes = JavaClassExtractor.extract_info_from_string(code)
    dfg_builder = DFGBuilder(
        ast=ast,
        cfg=cfg,
        java_classes=java_classes,
    )
    dfg = dfg_builder.build_from_string(code)
    dfg.export()
    assert len(list(dfg.nodes)) == 16
    assert len(list(dfg.edges)) == 9

def test_ipdf():
    file = Path(__file__).resolve().parent / "assets" / "command_executor_ipdf" / "CommandExecutor.java"
    ast = ASTBuilder.build_from_file(file)
    cfg = CFGBuilder.build_from_file(file)
    java_classes = JavaClassExtractor.extract_info_from_file(file)
    dfg_builder = DFGBuilder(
        ast=ast,
        cfg=cfg,
        java_classes=java_classes
    )
    dfg = dfg_builder.build_from_file(file)

    dfg_inter_edges = [e for e in dfg.edges if e.kind == DFEdgeKind.INTER]
    assert len(dfg_inter_edges) == 1
    dfg_inter_edge = dfg_inter_edges[0]
    assert dfg_inter_edge.source.code == 'process = runCommand(command)'
    assert dfg_inter_edge.target.code == 'Process runCommand(String com)'

def test_dvja():
    dvja_path = Path(__file__).resolve().parent / "assets" / "dvja"
    as_forest = AbstractSyntaxForestBuilder.build(dvja_path)
    cfg = CFGBuilder.build_from_directory(dvja_path)
    java_classes = JavaClassExtractor.extract_from_directory(dvja_path)
    dfg_builder = DFGBuilder(
        ast=as_forest,
        cfg=cfg,
        java_classes=java_classes
    )
    dfg = dfg_builder.build_from_directory(dvja_path)
    assert len(list(dfg.nodes)) == 509
    assert len(list(dfg.edges)) == 198
