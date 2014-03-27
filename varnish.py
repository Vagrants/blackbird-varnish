#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""get various information about varnish"""

__VERSION__ = '0.1.0'

import re
import subprocess
import json
import requests

from blackbird.plugins import base


class ConcreteJob(base.JobBase):
    u"""This Class is called by "Executer".
    ConcreteJob is registerd as a job of Executer.
    """

    def __init__(self, options, queue=None, logger=None):
        super(ConcreteJob, self).__init__(options,
                                          queue,
                                          logger
                                          )

        self.hostname = options.get('hostname')

    def build_items(self):
        u"""This method called by Executer.
        """

        # ping item
        self._ping()

        # detect varnish version
        self._get_version()

        # varnishstat
        for stat in self.get_varnishstat():
            self.enqueue(VarnishItem(
                key='varnish.varnishstat[{0}]'.format(
                    stat.get('key').replace('.', ',')
                ),
                value=stat.get("value"),
                host=self.hostname,
            ))

        # ban.list
        self.enqueue(VarnishItem(
            key="varnish.varnishadm[ban.list]",
            value=self.count_banlist(),
            host=self.hostname,
        ))

        host = self.options.get('response_check_host')
        port = self.options.get('response_check_port')
        uri = self.options.get('response_check_uri')
        vhost = (
            self.options.get('response_check_vhost')
            or
            self.options.get('response_check_host')
        )
        host = self.options.get('response_check_host')
        user_agent = self.options.get('response_check_uagent')
        scheme = 'https' if self.options.get('response_check_ssl') else 'http'
        ext_headers = {}

        try:
            (response, time) = self._get_response(
                scheme=scheme, host=host, port=port, uri=uri,
                vhost=vhost, user_agent=user_agent, ext_headers=ext_headers,
            )
        except requests.exceptions.RequestException as exception:
            self.logger.debug(exception)
        else:
            self.enqueue(VarnishItem(
                key='varnish.stat[response_check,time]',
                value=time,
                host=self.options['hostname'],
            ))
            self.enqueue(VarnishItem(
                key='varnish.stat[response_check,status_code]',
                value=response.status_code,
                host=self.options['hostname'],
            ))

    def build_discovery_items(self):
        # lld storage
        lld_values = []
        for storage in self.get_storages():
            lld_values.append({
                "{#STORAGE_NAME}": storage,
                "{#STORAGE_TYPE}": "file",
            })

        self.enqueue(VarnishDicoveryItem(
            key="varnish.storage.LLD",
            value={'data': lld_values},
            host=self.hostname,
        ))

    def _ping(self):
        """
        send ping item
        """

        self.enqueue(
            VarnishItem(
                key='blackbird.varnish.ping',
                value=1,
                host=self.options['hostname']
            )
        )

        self.enqueue(
            VarnishItem(
                key='blackbird.varnish.version',
                value=__VERSION__,
                host=self.options['hostname']
            )
        )

    def _get_version(self):
        """
        detect varnish version

        $ varnishd -V
        varnishd (varnish-N.N.N revision ....)
        Copyright (c) ....
        """

        varnish_version = 'Unknown'
        try:
            output = subprocess.Popen([self.options['path'], '-V'],
                                      stderr=subprocess.PIPE).communicate()[1]
            match = re.match(r"varnishd \(varnish-(\S+) ", output)
            if match:
                varnish_version = match.group(1)

        except OSError:
            self.logger.debug(
                'can not exec "{0} -V", failed to get varnish version'
                ''.format(self.options['path'])
            )

        self.enqueue(
            VarnishItem(
                key='varnish.version',
                value=varnish_version,
                host=self.options['hostname']
            )
        )

    @staticmethod
    def get_varnishstat():
        u"""get stat from varnishstat"""
        cwd = "/tmp"
        cmdline = "varnishstat -1"
        out, _ = subprocess.Popen(
            cmdline, shell=True, cwd=cwd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True,
        ).communicate()
        result = []
        lines = out.splitlines()

        for line in lines:
            parts = re.split(' +', line, 3)
            result.append({"key": parts[0], "value": parts[1]})

        return result

    @staticmethod
    def count_banlist():
        u"""count ban.list from varnishadm"""
        cwd = "/tmp"
        vadm = subprocess.Popen(
            "varnishadm ban.list", shell=True, cwd=cwd, stdout=subprocess.PIPE,
        )
        wcl = subprocess.Popen(
            "wc -l", shell=True, stdin=vadm.stdout, stdout=subprocess.PIPE,
        )
        out, _ = wcl.communicate()

        result = out.splitlines()[0]
        return result

    @staticmethod
    def get_storages():
        u"""get storage information"""
        cwd = "/tmp"
        cmdline = "varnishadm storage.list |grep file"
        out, _ = subprocess.Popen(
            cmdline, shell=True, cwd=cwd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True,
        ).communicate()

        result = []
        lines = out.splitlines()
        for line in lines:
            match = re.search(r"storage\.(.*) = file", line)
            if match:
                result.append(match.group(1))
        return result

    @staticmethod
    def _get_response(scheme="http", host="localhost", port=80,
                      uri="/", vhost=None, user_agent=None, ext_headers=None):
        u"""get response and measure latency"""
        if not ext_headers:
            ext_headers = {}

        url = (
            '{scheme}://{host}:{port}{uri}'
            ''.format(
                scheme=scheme,
                host=host,
                port=port,
                uri=uri
            )
        )
        headers = {}
        if vhost is not None:
            headers['Host'] = vhost
        if user_agent is not None:
            headers['User-Agent'] = user_agent

        headers.update(ext_headers)

        with base.Timer() as timer:
            response = requests.get(url, headers=headers)

        time = timer.sec
        return (response, time)


class VarnishItem(base.ItemBase):
    u"""."""

    def __init__(self, key, value, host):
        super(VarnishItem, self).__init__(key, value, host)

        self._data = {}
        self._generate()

    @property
    def data(self):
        u"""Dequeued data. ListType object.
        [{key1:value1}, {key2:value2}...]
        """
        return self._data


class VarnishDicoveryItem(base.ItemBase):
    u"""."""

    def __init__(self, key, value, host):
        super(VarnishDicoveryItem, self).__init__(key, value, host)

        self._data = {}
        self._generate()

    @property
    def data(self):
        u"""Dequeued data. ListType object.
        [{key1:value1}, {key2:value2}...]
        """
        return self._data

    def _generate(self):
        self._data['host'] = self.host
        self._data['clock'] = self.clock
        self._data['key'] = self.key
        self._data['value'] = json.dumps(self.value)


class Validator(base.ValidatorBase):
    def __init__(self):
        self.__spec = None
        self.__module = None

    @property
    def spec(self):
        self.__spec = (
            "[{0}]".format(__name__),
            "response_check_host = string(default='127.0.0.1')",
            "response_check_port = integer(0, 65535, default=80)",
            "response_check_timeout = integer(0, 600, default=3)",
            "response_check_vhost = string(default='localhost')",
            "response_check_uagent = string(default='blackbird response check')",
            "response_check_ssl = boolean(default=False)",
            "path = string(default='/usr/sbin/varnishd')",
            "hostname = string(default={0})".format(self.detect_hostname()),
        )
        return self.__spec

if __name__ == '__main__':
    OPTIONS = {
    }

    BBL_VARNISH = ConcreteJob(options=OPTIONS)
    BBL_VARNISH.build_items()
