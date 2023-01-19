from abc import ABC, abstractmethod


class BaseEndpointExtractor(ABC):
    @abstractmethod
    def extractEndpoints(self):
        pass

    @abstractmethod
    def dump(self):
        pass
