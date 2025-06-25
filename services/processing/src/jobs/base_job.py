import logging
from abc import ABC, abstractmethod


class BaseJob(ABC):
    def __init__(self, name: str, sink_name: str):
        self.name = name
        self.sink_name = sink_name
        self.logger = logging.getLogger(name)

    @abstractmethod
    def build_pipeline(self, t_env):
        """Build and return the pipeline Table"""
        pass
