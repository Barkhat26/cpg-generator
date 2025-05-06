from abc import ABC, abstractmethod


class BaseAttackEndpointExtractor(ABC):
    @abstractmethod
    def extractEndpoints(self):
        pass

    @abstractmethod
    def dump(self):
        pass
