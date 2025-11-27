# -*- coding: utf-8 -*-
import pytest


class DummyClient(object):

    def __init__(self):
        self.response = lambda link: {}

    def request(self, link, *args, **kwargs):
        return self.response(link)


@pytest.fixture
def dummy_client(request):
    """
    A client that returns whatever the current value of response is as the
    response.
    """
    return DummyClient()
