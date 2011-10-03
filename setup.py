#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
from setuptools import find_packages, setup

setup(
    name = 'TracTicketRelationsPlugin',
    version='1.0.2',
    packages = ['ticketrelations'],
    package_data = { 'ticketrelations': ['htdocs/*.js'] },

    author = 'Leif Högberg',
    author_email = 'leihog@gmail.com',
    description = 'Provides dependency relations between tickets. (blocked by/blocking)',
    long_description = open(os.path.join(os.path.dirname(__file__), 'README')).read(),
    url = 'http://github.com/leihog/trac-ticketrelations',
    license = 'BSD',

    install_requires = ['Trac>=0.12'],
    entry_points = {
        'trac.plugins': [
            'ticketrelations.web_ui = ticketrelations.web_ui',
            'ticketrelations.api = ticketrelations.api',
        ],
    },
)