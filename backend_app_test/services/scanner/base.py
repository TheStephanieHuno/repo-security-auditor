from abc import ABC, abstractmethod
from typing import List, Dict, Any

class SecurityCheck(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        pass
