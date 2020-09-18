"""
Copyright 2015 Jorgen Maas <jorgen.maas@gmail.com>
This file is part of koan.
Koan is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.
Zenossctl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with zenossctl. If not, see <http://www.gnu.org/licenses/>.
"""

from setuptools import setup

VERSION = "2.9.0"

setup(
    name='koan',
    version=VERSION,
    description='Kickstart over a Network Client for Cobbler',
    long_description='This client can initiate and prepare a reinstallation of your operation system with the help of'
                     'cobbler.',
    author='xxx',
    author_email='xxx',
    url='http://www.github.com/cobbler/koan',
    packages=['koan'],
    license='GPLv2',
    scripts=['bin/koan', 'bin/cobbler-register'],
    install_requires=[
        'simplejson',
        'distro',
        'libvirt-python',
        'netifaces',
    ],
    extras_require={'lint': ['pyflakes', 'pycodestyle'], 'test': ['pytest', 'nose']},
    # data_files=[('/etc/zenossctl', ['config/zenossctl.json'])],
)

# EOF
