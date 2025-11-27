# -*- coding: utf-8 -*-
from flipkart.api import PaginationIterator


class TestPaginationClient:

    def test_single_page(self, dummy_client):
        dummy_client.response = lambda link: {
            'page-1': {
                'items': range(1, 10),
            },
        }[link]
        iterator = PaginationIterator(
            dummy_client, dummy_client.response('page-1'), 'items'
        )
        assert list(iterator) == list(range(1, 10))

    def test_two_pages(self, dummy_client):
        dummy_client.response = lambda link: {
            'page-1': {
                'items': range(1, 10),
                'nextPageUrl': 'page-2'
            },
            'page-2': {
                'items': range(10, 20)
            }
        }[link]
        iterator = PaginationIterator(
            dummy_client, dummy_client.response('page-1'), 'items'
        )
        assert list(iterator) == list(range(1, 20))

    def test_three_pages(self, dummy_client):
        dummy_client.response = lambda link: {
            'page-1': {
                'items': range(1, 10),
                'nextPageUrl': 'page-2'
            },
            'page-2': {
                'items': range(10, 20),
                'nextPageUrl': 'page-3'
            },
            'page-3': {
                'items': range(20, 30),
            }
        }[link]
        iterator = PaginationIterator(
            dummy_client, dummy_client.response('page-1'), 'items'
        )
        assert list(iterator) == list(range(1, 30))
