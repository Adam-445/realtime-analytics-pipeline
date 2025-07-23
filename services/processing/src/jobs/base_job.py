from abc import ABC, abstractmethod

from src.core.logger import get_logger


class BaseJob(ABC):
    def __init__(self, name: str, sink_name: str):
        self.name = name
        self.sink_name = sink_name
        self.logger = get_logger(name)

    @abstractmethod
    def build_pipeline(self, t_env):
        """Build and return the pipeline Table"""
        pass
