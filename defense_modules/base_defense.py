from abc import ABC, abstractmethod

class BaseDefense(ABC):

    @abstractmethod
    def score(self, sample):
        pass
