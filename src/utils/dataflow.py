from java.java_structures import JavaClass
from .datatypes import Stack, Queue


def isUsableExpression(expr: str) -> bool:
    # must not be a literal or of type 'class'.
    if expr.startswith("$"):
        return False
    # must not be a method-call or parenthesized expression
    if expr.endswith(")"):
        return False
    # must not be an array-indexing expression
    if expr.endswith("]"):
        return False
    # must not be post unary operation expression
    if expr.endswith("++") or expr.endswith("--"):
        return False
    # must not be a pre unary operation expression
    if expr.startswith("+") or expr.startswith("-") or expr.startswith("!") or expr.startswith("~"):
        return False
    # must not be an array initialization expression
    if expr.endswith("}"):
        return False
    # must not be an explicit generic invocation expression
    if expr.startswith("<"):
        return False

    return True


def getParExpression(code: str) -> str:
    if code.startswith("if"):
        return code[4:-1]
    if code.startswith("for"):
        return code[5:-1]
    if code.startswith("while"):
        return code[7:-1]


# Вынесенный метод из MethodInfo. Нужен для того, чтобы не вызывать findDefInfo
def doesMethodStateDef(name: str):
    prefixes = ["set", "put", "add", "insert", "push", "append"]
    for pre in prefixes:
        if name.lower().startswith(pre):
            return True

    return False

def nodeContainsCall(node):
    from db import Database
    from graphs.ast.ast_node import ASNodeKind
    ast_node = None
    current_ast = None
    for AST in Database().getAllASTs().values():
        ast_node = AST.getNodeByID(node.shared_id)
        current_ast = AST
        break

    if ast_node is None:
        return False

    queue = Queue()
    queue.push(ast_node)

    contains_call = False
    while not queue.isEmpty():
        current = queue.pop()

        if current.kind == ASNodeKind.CALL:
            contains_call = current
            break

        for on in current_ast.outNodes(current):
            queue.push(on)

    return contains_call

def getCallName(node):
    from db import Database
    from graphs.ast.ast_node import ASNodeKind
    ast_node = None
    current_ast = None
    for AST in Database().getAllASTs().values():
        ast_node = AST.getNodeByID(node.shared_id)
        current_ast = AST
        break
    if ast_node is None:
        return None
    queue = Queue()
    queue.push(ast_node)

    call_node = None
    while not queue.isEmpty():
        current = queue.pop()

        if current.kind == ASNodeKind.CALL:
            call_node = current
            break

        for on in current_ast.outNodes(current):
            queue.push(on)

    for on in current_ast.outNodes(call_node):
        if on.kind == ASNodeKind.NAME:
            return on.getCode()

def getCallArgs(node, ast):
    from graphs.ast.ast_node import ASNodeKind
    ast_node = ast.getNodeByID(node.shared_id)
    queue = Queue()
    queue.push(ast_node)

    call_node = None
    while not queue.isEmpty():
        current = queue.pop()

        if current.kind == ASNodeKind.CALL:
            call_node = True
            break

        for on in ast.outNodes(current):
            queue.push(on)

    for on in ast.outNodes(call_node):
        if on.kind == ASNodeKind.PARAMS:
            pass


def nodeContainsReturn(node):
    from db import Database
    from graphs.ast.ast_node import ASNodeKind
    ast_node = None

    for AST in Database().getAllASTs().values():
        ast_node = AST.getNodeByID(node.shared_id)
        break

    if ast_node is None:
        return False

    if ast_node.kind == ASNodeKind.RETURN:
        return True

    return False




def isOperator(x):
    if x in ['+', '-', '/', '*']:
        return True
    else:
        return False

def preToInfix(pre_exp_list):
    s = Stack()
    for el in pre_exp_list[::-1]:
        if isOperator(el):
            op1 = s.pop()
            op2 = s.pop()
            temp = "(" + op1 + el + op2 + ")"
            s.push(temp)
        else:
            s.push(el)
    return s.peek()


def has_super_class(child_java_class_name, super_java_class_name, java_classes: dict[str, JavaClass]) -> bool:
    current = child_java_class_name

    while True:
        jc = java_classes.get(current)

        if jc is None:
            break

        if jc.extends is None:
            break

        if jc.extends == super_java_class_name:
            return True

        current = jc.package + "." + jc.extends

    return False
#
# def findCallers(methodQN: str) -> List[str]:
#     db = Database()
#     search = methodQN.split(".")[-1]
#
#     callers = []
#     for method in db.getCallGraphMethods():
#         if search in db.getCallees(method):
#             callers.append(method)
#     return callers






