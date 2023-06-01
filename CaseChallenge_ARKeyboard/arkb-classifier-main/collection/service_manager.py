import requests
import atexit


def register(server_url: str, name: str) -> None:
    requests.post(server_url + "/service", json={"name": name})
    atexit.register(deregister, server_url, name)


def deregister(server_url: str, name: str) -> None:
    requests.delete(server_url + f"/service/{name}")
