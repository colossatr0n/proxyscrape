# MIT License
#
# Copyright (c) 2018 Jared Gillespie
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = ['Proxy', 'ProxyResource', 'RESOURCE_MAP', 'RESOURCE_TYPE_MAP']


from bs4 import BeautifulSoup
from collections import namedtuple
from threading import Lock
import requests
import re
import time

from .errors import InvalidHTMLError, RequestNotOKError


Proxy = namedtuple('Proxy', ['host', 'port', 'code', 'country', 'anonymous', 'type', 'source'])


class ProxyResource:
    def __init__(self, url, func, refresh_interval):
        self._url = url
        self._func = func
        self._refresh_interval = refresh_interval
        self._lock = Lock()
        self._last_refresh_time = 0

    def refresh(self, force=False):
        if not force and self._last_refresh_time + self._refresh_interval > time.time():
            return False, None

        with self._lock:
            # Check if updated before
            if force or self._last_refresh_time + self._refresh_interval <= time.time():

                try:
                    proxies = self._func(self._url)
                    self._last_refresh_time = time.time()
                    return True, proxies
                except (InvalidHTMLError, RequestNotOKError):
                    pass

        return False, None


def get_anonymous_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'id': 'proxylisttable'})
        proxies = set()

        for row in table.find('tbody').find_all('tr'):
            data = list(map(lambda x: x.text, row.find_all('td')))
            host = data[0]
            port = data[1]
            code = data[2].lower()
            country = data[3].lower()
            anonymous = data[4].lower() in ('anonymous', 'elite proxy')
            version = 'https' if data[6].lower() == 'yes' else 'http'

            proxies.add(Proxy(host, port, code, country, anonymous, version, 'anonymous-proxy'))

        return proxies
    except (AttributeError, KeyError):
        raise InvalidHTMLError()


def get_free_proxy_list_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'id': 'proxylisttable'})
        proxies = set()

        for row in table.find('tbody').find_all('tr'):
            data = list(map(lambda x: x.text, row.find_all('td')))
            host = data[0]
            port = data[1]
            code = data[2].lower()
            country = data[3].lower()
            anonymous = data[4].lower() in ('anonymous', 'elite proxy')
            version = 'https' if data[6].lower() == 'yes' else 'http'

            proxies.add(Proxy(host, port, code, country, anonymous, version, 'free-proxy-list'))

        return proxies
    except (AttributeError, KeyError):
        raise InvalidHTMLError()


def _get_proxy_daily_proxies_parse_inner(text, type, source):
    inner_reg = re.findall(r'''
            ([0-9]{1,3}\. # Host Address
            [0-9]{1,3}\.
            [0-9]{1,3}\.
            [0-9]{1,3}
            :[0-9]{1,5}) # Port Number
        ''', text, re.X | re.S)

    if not inner_reg:
        raise InvalidHTMLError()

    return {Proxy(*i.split(':'), None, None, None, type, source)
            for i in inner_reg}


def get_proxy_daily_http_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    outer_reg = re.findall(r'''
        Free\sHttp/Https\sProxy\sList 
        .*
        Free\sSocks4\sProxy\sList
    ''', response.text, re.X | re.S)

    if not outer_reg:
        raise InvalidHTMLError()

    return _get_proxy_daily_proxies_parse_inner(outer_reg[0], 'http', 'proxy-daily-http')


def get_proxy_daily_socks4_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    outer_reg = re.findall(r'''
         Free\sSocks4\sProxy\sList
        .*
        Free\sSocks5\sProxy\sList
    ''', response.text, re.X | re.S)

    if not outer_reg:
        raise InvalidHTMLError()

    return _get_proxy_daily_proxies_parse_inner(outer_reg[0], 'socks4', 'proxy-daily-socks4')


def get_proxy_daily_socks5_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    outer_reg = re.findall(r'''
         Free\sSocks5\sProxy\sList
        .*
    ''', response.text, re.X | re.S)

    if not outer_reg:
        raise InvalidHTMLError()

    return _get_proxy_daily_proxies_parse_inner(outer_reg[0], 'socks5', 'proxy-daily-socks5')


def get_socks_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'id': 'proxylisttable'})
        proxies = set()

        for row in table.find('tbody').find_all('tr'):
            data = list(map(lambda x: x.text, row.find_all('td')))
            host = data[0]
            port = data[1]
            code = data[2].lower()
            country = data[3].lower()
            version = data[4].lower()
            anonymous = data[5].lower() in ('anonymous', 'elite proxy')

            proxies.add(Proxy(host, port, code, country, anonymous, version, 'socks-proxy'))

        return proxies
    except (AttributeError, KeyError):
        raise InvalidHTMLError()


def get_ssl_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'id': 'proxylisttable'})
        proxies = set()

        for row in table.find('tbody').find_all('tr'):
            data = list(map(lambda x: x.text, row.find_all('td')))
            host = data[0]
            port = data[1]
            code = data[2].lower()
            country = data[3].lower()
            anonymous = data[4].lower() in ('anonymous', 'elite proxy')

            proxies.add(Proxy(host, port, code, country, anonymous, 'https', 'ssl-proxy'))

        return proxies
    except (AttributeError, KeyError):
        raise InvalidHTMLError()


def get_uk_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'id': 'proxylisttable'})
        proxies = set()

        for row in table.find('tbody').find_all('tr'):
            data = list(map(lambda x: x.text, row.find_all('td')))
            host = data[0]
            port = data[1]
            code = data[2].lower()
            country = data[3].lower()
            anonymous = data[4].lower() in ('anonymous', 'elite proxy')
            version = 'https' if data[6].lower() == 'yes' else 'http'

            proxies.add(Proxy(host, port, code, country, anonymous, version, 'uk-proxy'))

        return proxies
    except (AttributeError, KeyError):
        raise InvalidHTMLError()


def get_us_proxies(url):
    response = requests.get(url)
    if not response.ok:
        raise RequestNotOKError()

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'id': 'proxylisttable'})
        proxies = set()

        for row in table.find('tbody').find_all('tr'):
            data = list(map(lambda x: x.text, row.find_all('td')))
            host = data[0]
            port = data[1]
            code = data[2].lower()
            country = data[3].lower()
            anonymous = data[4].lower() in ('anonymous', 'elite proxy')
            version = 'https' if data[6].lower() == 'yes' else 'http'

            proxies.add(Proxy(host, port, code, country, anonymous, version, 'us-proxy'))

        return proxies
    except (AttributeError, KeyError):
        raise InvalidHTMLError()


RESOURCE_MAP = {
    'anonymous-proxy': {
        'url': 'https://free-proxy-list.net/anonymous-proxy.html',
        'func': get_anonymous_proxies
    },
    'free-proxy-list': {
        'url': 'http://www.free-proxy-list.net',
        'func': get_free_proxy_list_proxies
    },
    'proxy-daily-http': {
        'url': 'http://www.proxy-daily.com',
        'func': get_proxy_daily_http_proxies
    },
    'proxy-daily-socks4': {
        'url': 'http://www.proxy-daily.com',
        'func': get_proxy_daily_socks4_proxies
    },
    'proxy-daily-socks5': {
        'url': 'http://www.proxy-daily.com',
        'func': get_proxy_daily_socks5_proxies
    },
    'socks-proxy': {
        'url': 'https://www.socks-proxy.net',
        'func': get_socks_proxies
    },
    'ssl-proxy': {
        'url': 'https://www.sslproxies.org/',
        'func': get_ssl_proxies
    },
    'uk-proxy': {
        'url': 'https://free-proxy-list.net/uk-proxy.html',
        'func': get_uk_proxies
    },
    'us-proxy': {
        'url': 'https://www.us-proxy.org',
        'func': get_us_proxies,
    }
}

RESOURCE_TYPE_MAP = {
    'http': {
        'us-proxy',
        'uk-proxy',
        'free-proxy-list',
        'proxy-daily-http',
        'anonymous-proxy'
    },
    'https': {
        'us-proxy',
        'uk-proxy',
        'free-proxy-list',
        'ssl-proxy',
        'anonymous-proxy'
    },
    'socks4': {
        'socks-proxy',
        'proxy-daily-socks4'
    },
    'socks5': {
        'socks-proxy',
        'proxy-daily-socks5'
    }
}
