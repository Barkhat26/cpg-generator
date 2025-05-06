from abc import ABC, abstractmethod


class BaseChecker(ABC):
    def __init__(self):
        self.rightNumberOfTokens = None

    def setSafeQuery(self, query):
        self.rightNumberOfTokens = self._getNumberOfTokens(query)

    def checkPotentialUnsafeQuery(self, query):
        number_of_tokens2 = self._getNumberOfTokens(query)
        return self.rightNumberOfTokens == number_of_tokens2

    @abstractmethod
    def _getNumberOfTokens(self, query):
        pass
