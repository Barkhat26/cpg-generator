from pathlib import Path
from typing import List
import os.path

from graph_builders.as_forest_builder import AbstractSyntaxForestBuilder
from graph_builders.ast_builder import ASTBuilder
from graph_builders.cfg_builder import CFGBuilder
from graph_builders.dfg_builder import DFGBuilder
from graphs.ddg.dfg_node import DFNode
from java.java_class_extractor import JavaClassExtractor
from taint_flow.analyzer import TaintFlowAnalyzer
from taint_flow.taintflow import TaintFlow
from taint_flow.web_framework_kind import WebFrameworkKind


class DataFlowNodePattern:
    def __init__(self, file: str | None, line: int, code: str):
        self.file = file
        self.line = line
        self.code = code

    def compare_with_data_flow_node(self, data_flow_node: DFNode, base_path: str | None):
        normalized_code = data_flow_node.code.replace('\r\n', '\n')
        normalized_file = os.path.relpath(data_flow_node.file, base_path) if base_path is not None else None

        return self.line == self.line and self.code == normalized_code and self.file == normalized_file


class TaintFlowPattern:
    def __init__(self, source: DataFlowNodePattern, vulnerability: str, sink: DataFlowNodePattern):
        self.source = source
        self.vulnerability = vulnerability
        self.sink = sink

    def __str__(self):
        return f'taint [{self.vulnerability}]: {self.source.code} -> {self.sink.code}'

    def compare_with_taint_flow(self, taint_flow: TaintFlow, base_path: str):
        return self.vulnerability == taint_flow.vulnerability and \
            self.source.compare_with_data_flow_node(taint_flow.source, base_path) and \
            self.sink.compare_with_data_flow_node(taint_flow.sink, base_path)


def match(results: List[TaintFlow], patterns: List[TaintFlowPattern], base_path: str | None = None):
    if len(results) != len(patterns):
        return False

    matched = 0

    for pattern in patterns:
        for result in results:
            if pattern.compare_with_taint_flow(result, base_path):
                matched += 1
                break

    return matched == len(patterns)


def test_ci():
    code = r"""
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
        java_classes=java_classes
    )
    dfg = dfg_builder.build_from_string(code)
    taint_flow_analyzer = TaintFlowAnalyzer(ast, dfg, java_classes, WebFrameworkKind.none)
    taint_flows = taint_flow_analyzer.analyze()
    assert len(taint_flows) == 1
    assert match(taint_flows, [
        TaintFlowPattern(
            DataFlowNodePattern(
                None,
                10,
                "command = reader.readLine()"
            ),
            "CI",
            DataFlowNodePattern(
                None,
                12,
                "process = Runtime.getRuntime().exec(command)"
            )
        ),
    ])


def test_dvja():
    patterns = [
        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ProductAction.java",
                66,
                "products = productService.findContainingName(searchQuery);"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\ProductService.java",
                48,
                "query = entityManager.createQuery(\"SELECT p FROM Product p WHERE p.name LIKE '%\" + name + \"%'\")"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ApiAction.java",
                75,
                "user = userService.findByLogin(getLogin())"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                63,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = :login\").\n                setParameter(\"login\", login).\n                setMaxResults(1)"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserAuthenticationService.java",
                20,
                "user = userService.findByLogin(login);"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                63,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = :login\").\n                setParameter(\"login\", login).\n                setMaxResults(1)"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                63,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = :login\").\n                setParameter(\"login\", login).\n                setMaxResults(1)"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                63,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = :login\").\n                setParameter(\"login\", login).\n                setMaxResults(1)"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                96,
                "user = findByLogin(login)"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                63,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = :login\").\n                setParameter(\"login\", login).\n                setMaxResults(1)"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\Login.java",
                49,
                "if ((user = userAuthenticationService.authenticate(getLogin(), getPassword())) != null)"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                63,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = :login\").\n                setParameter(\"login\", login).\n                setMaxResults(1)"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ResetPassword.java",
                74,
                "ret = userService.resetPasswordByLogin(getLogin(), getKey(),\n                    getPassword(), getPasswordConfirmation());"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                63,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = :login\").\n                setParameter(\"login\", login).\n                setMaxResults(1)"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                109,
                "user = userService.findByLoginUnsafe(getLogin());"
            ),
            "SQL",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                75,
                "query = entityManager.createQuery(\"SELECT u FROM User u WHERE u.login = '\" + login + \"'\")"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ProductAction.java",
                66,
                "products = productService.findContainingName(searchQuery);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ProductAction.java",
                66,
                "products = productService.findContainingName(searchQuery);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\PingAction.java",
                45,
                "command = { \"/bin/bash\", \"-c\", \"ping -t 5 -c 5 \" + getAddress() }"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\PingAction.java",
                62,
                "setCommandOutput(output);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                97,
                "user.setPassword(getPassword());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                97,
                "user.setPassword(getPassword());"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                95,
                "user.setEmail(getEmail());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                97,
                "user.setPassword(getPassword());"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                88,
                "user = userService.find(getUserId());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                97,
                "user.setPassword(getPassword());"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                77,
                "setEmail(getUser().getEmail());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                77,
                "setEmail(getUser().getEmail());"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                95,
                "user.setEmail(getEmail());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                95,
                "user.setEmail(getEmail());"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                88,
                "user = userService.find(getUserId());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                95,
                "user.setEmail(getEmail());"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                76,
                "setUserId(getUser().getId());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                76,
                "setUserId(getUser().getId());"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\example\\HelloWorld.java",
                30,
                "setMessage(getText(MESSAGE));"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\example\\HelloWorld.java",
                30,
                "setMessage(getText(MESSAGE));"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ProductAction.java",
                86,
                "productService.save(product);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ProductAction.java",
                86,
                "productService.save(product);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                99,
                "userService.save(user);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                99,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                97,
                "user.setPassword(getPassword());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                99,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                95,
                "user.setEmail(getEmail());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                99,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                98,
                "user.setId(getUserId());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                99,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                88,
                "user = userService.find(getUserId());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\UserAction.java",
                99,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                31,
                "user.setLogin(login);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                35,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                32,
                "user.setPassword(password);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                35,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\Register.java",
                85,
                "user = userRegistrationService.register(getName(), getLogin(), getEmail(),\n                    getPassword(), getPasswordConfirmation());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                35,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                30,
                "user.setName(name);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                35,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                33,
                "user.setEmail(email);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                35,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                35,
                "userService.save(user);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserRegistrationService.java",
                35,
                "userService.save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                96,
                "user = findByLogin(login)"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                99,
                "save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                98,
                "user.setPassword(password);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                99,
                "save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\ResetPassword.java",
                74,
                "ret = userService.resetPasswordByLogin(getLogin(), getKey(),\n                    getPassword(), getPasswordConfirmation());"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                99,
                "save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                99,
                "save(user);"
            ),
            "XSS",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\services\\UserService.java",
                99,
                "save(user);"
            )
        ),

        TaintFlowPattern(
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\PingAction.java",
                45,
                "command = { \"/bin/bash\", \"-c\", \"ping -t 5 -c 5 \" + getAddress() }"
            ),
            "CI",
            DataFlowNodePattern(
                "src\\main\\java\\com\\appsecco\\dvja\\controllers\\PingAction.java",
                46,
                "process = runtime.exec(command)"
            )
        ),
    ]

    # project_config = {
    #     "name": "djva-analysis",
    #     "DB": r"C:\Workspace\cpg-generator\tmp\djva-analysis\djva-analysis.db",
    #     "target-dir": "C:\\tmp\\dvja",
    # }
    # database = Database(project_config=project_config)
    # taint_flows = database.getAllTaintFlows()
    # assert len(taint_flows) == 35
    # assert match(taint_flows, patterns, project_config["target-dir"])
    sources_directory = Path(__file__).resolve().parent / "assets" / "dvja"

    asf = AbstractSyntaxForestBuilder.build(sources_directory)
    cfg = CFGBuilder.build_from_directory(sources_directory)
    java_classes = JavaClassExtractor.extract_from_directory(sources_directory)
    dfg = DFGBuilder(asf, cfg, java_classes).build_from_directory(sources_directory)
    taint_flow_analyzer = TaintFlowAnalyzer(asf, dfg, java_classes, WebFrameworkKind.struts2)
    taint_flows = taint_flow_analyzer.analyze()
    assert len(taint_flows) == 45
