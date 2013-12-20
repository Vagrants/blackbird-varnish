#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""Parse /proc/net/"protocol" and put Queue"""

import re
import subprocess
import json

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

        self.hostname = options['hostname']

    def looped_method(self):
        u"""This method called by Executer.
        """

        #varnishstat
        for stat in self.get_varnishstat():
            self.queue.put( VarnishItem(key="varnish.varnishstat["  +stat.get("key").replace("." , ",") +"]",
                                       value=stat.get("value"),
                                       host=self.hostname
                                       ),
                           block=False
                           )
                           

        #ban.list
        self.queue.put( VarnishItem(key="varnish.varnishadm[ban.list]",
                                       value=self.get_varnishadm("ban.list"),
                                       host=self.hostname
                                       ),
                           block=False
                           )
        
        #lld storage
        lld_values = []
        for storage in self.get_storages():
            lld_values.append({"{#STORAGE_NAME}":storage, "{#STORAGE_TYPE}":"file"})

        self.queue.put(VarnishDicoveryItem(
                                   key="varnish.storage.LLD" , value={'data' : lld_values} , host=self.hostname
                                   ),
                       block=False
                       )

    @staticmethod
    def get_varnishstat():
        cwd = "/tmp"
        cmdline = "varnishstat -1"
        out , err = subprocess.Popen(cmdline, shell=True, cwd=cwd, stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     close_fds=True).communicate()
        result = []
        lines = out.splitlines()
        
        for line in lines:
            parts = re.split(' +' , line , 3)
            result.append({"key":parts[0] , "value":parts[1]})
            
        return result


    @staticmethod
    def get_varnishadm(arg):
        cwd = "/tmp"
        cmdline = "sudo varnishadm %s| wc -l" % (arg)
        out , err = subprocess.Popen(cmdline, shell=True, cwd=cwd, stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     close_fds=True).communicate()
 
        result = out.splitlines()[0]            
        return result
    
    @staticmethod
    def get_storages():
        cwd = "/"
        cmdline = "sudo varnishadm storage.list |grep file"
        out , err = subprocess.Popen(cmdline, shell=True, cwd=cwd, stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     close_fds=True).communicate()      
         
        result = []
        lines = out.splitlines()
        for line in lines:
            m = re.search("storage\.(.*) = file", line)
            result.append(m.group(1))
        return result

        
class VarnishItem(base.ItemBase):
    u"""Enqueued item. Take an argument as redis.info()."""

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
    u"""Enqueued item. Take an argument as redis.info()."""

    def __init__(self, key, value, host):
        super(VarnishDicoveryItem, self).__init__(key, value, host)

        self._data = {}
        self._generate()

    @property
    def data(self):
        u"""Dequeued data. ListType object.
        [{key1:value1}, {key2:value2}...]
        """
        return  self._data
    
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
            "hostname = string(default={0})".format(self.gethostname()),
        )
        return self.__spec

if __name__ == '__main__':
    OPTIONS = {
            'stats_socket': '/var/lib/haproxy/stats',
            'hostname': 'hogehoge.com'
    }

    BBL_VARNISH = ConcreteJob(options=OPTIONS)
    BBL_VARNISH.looped_method()
