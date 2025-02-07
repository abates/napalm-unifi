import sys
from os import path
import json
from functools import cache

from pytest import mark

from . import get_mocked_driver

@cache
def config():
    data_dir = path.join(path.dirname(__file__), "testdata", "usw")
    with open(path.join(data_dir, "tests.json"), encoding="utf-8") as file:
        data = json.load(file)
        for command, command_output in data["command_table"].items():
            if command_output.startswith("!load_file:"):
                filename = command_output.removeprefix("!load_file:")
                with open(path.join(data_dir, filename), encoding="utf-8") as command_file:
                    data["command_table"][command] = command_file.read()
        return data

@mark.parametrize("test", config()["tests"])
def test_napalm_getters(test):
    driver = get_mocked_driver(config()["driver"], config()["prompt"], config()["command_table"])
    command = getattr(driver, test["method"])
    result = command()
    assert result == test["expected"]

