#
# TWWordPress - Integration with WordPress server
#
# Copyright (C)    2021 Hans Boldt
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""Integration with WordPress server"""

#------------------#
# Python modules   #
#------------------#
import os
from datetime import datetime
import json
import operator
from functools import reduce

from html import escape

import pdb

NUM_SUBDIRS = 20
CHECKSUM_DIGITS = 6
CHECKSUM_HASH = 2**(CHECKSUM_DIGITS*4)
CHECKSUM_FORMAT = '%0' + str(CHECKSUM_DIGITS) + 'x'


class TWDataWriter():
    """
    """

    def __init__(self):
        """
        """
        return


    def start(self):
        """
        """
        raise NotImplementedError


    @classmethod
    def checksum(cls, st):
        return CHECKSUM_FORMAT % (reduce(operator.add, map(ord, st)) % CHECKSUM_HASH)


    @classmethod
    def get_dir_for_gramps_id(cls, gramps_id):
        """
        Get (possibly create) directories for person
        """
        pnum = int(''.join((c for c in gramps_id if c.isnumeric())))
        dir1 = chr(ord('a') + (pnum % NUM_SUBDIRS))
        dir2 = chr(ord('a') + ((pnum//NUM_SUBDIRS) % NUM_SUBDIRS))
        return (dir1, dir2)


    def export_individual(self, index_summary, info):
        """
        Export file. Must be implemented by a derived class.
        """
        raise NotImplementedError


    def export_json(self, subdir, gramps_id, data):
        """
        Export file. Must be implemented by a derived class.
        """
        raise NotImplementedError


    def export_image(self, subdir, gramps_id, ext, data):
        """
        Export image. Must be implemented by a derived class.
        """
        raise NotImplementedError


    def export_file(self, subdir, tgtfile, srcfile):
        """
        Export file to file system. Must be implemented by a derived class
        """
        raise NotImplementedError


    def finish(self):
        """
        Final processing for this instance.
        """
        return
