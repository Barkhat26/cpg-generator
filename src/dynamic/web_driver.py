import requests


class WebDriver:
    def __init__(self):
        self.s = requests.sessions.Session()

    def prepare(self):
        ...

    def authenticate(self):
        ...

    def post(self, full_uri: str, data: dict[str, str]):
        # TODO:
        self.s.post(full_uri, data=data)

