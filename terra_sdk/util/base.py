"""Some useful base classes to inherit from."""

from typing import List, Dict, Any, Callable

from .json import dict_to_data, JSONSerializable


class BaseTerraData(JSONSerializable):

    type: str

    def to_data(self) -> dict:
        return {"type": self.type, "value": dict_to_data(self.__dict__)}


def create_demux(inputs: List) -> Callable[[Dict[str, Any]], Any]:
    table = {i.type: i.from_data for i in inputs}

    def from_data(data: dict):
        return table[data["type"]](data)

    return from_data
