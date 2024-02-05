import abc

from typing import Dict


class Worker(abc.ABC):
    block_name: str
    block_def: Dict
    credential_def: Dict = None

    @abc.abstractmethod
    def handler(self, task, workflow_context, credential_data):
        pass
