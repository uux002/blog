#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Default configurations.
'''

__author__ = 'Michael Liao'

configs = {
    'debug': True,
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'jkilopqcv0968',
        'db': 'db_fredshao_blog'
    },
    'session': {
        'secret': 'FredShao_Blog'
    },
    #'domain':'http://fredshao.cc/static/blog_images/',
    'domain':'http://127.0.0.1:9000/static/blog_images/',
}


