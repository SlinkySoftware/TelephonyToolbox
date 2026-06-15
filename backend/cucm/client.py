from abc import ABC, abstractmethod

from cucm.schemas import CucmDirectoryNumber, CucmHealthResult, CucmUpdateResult


class CucmClient(ABC):
    @abstractmethod
    def get_directory_number(self, pattern: str, route_partition: str) -> CucmDirectoryNumber:
        raise NotImplementedError

    @abstractmethod
    def update_call_forward_all(self, pattern: str, route_partition: str, destination: str) -> CucmUpdateResult:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> CucmHealthResult:
        raise NotImplementedError