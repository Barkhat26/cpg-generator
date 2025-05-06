from dynamic.checkers.base_checker import BaseChecker

METACHARACTERS = [";", "&&", "||"]

# TODO: переделать на использование лексического анализа
class CIChecker(BaseChecker):
    def _getNumberOfTokens(self, _query):
        number_of_meta_chars = 0
        for metaChar in METACHARACTERS:
            number_of_meta_chars += _query.count(metaChar)
        return number_of_meta_chars