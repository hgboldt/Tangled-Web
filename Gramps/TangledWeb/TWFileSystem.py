#
# TWFileSystem - Integration with local file system
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

"""Integration with local file server"""

#------------------#
# Python modules   #
#------------------#
import os
from datetime import datetime
from shutil import copyfile
import json

import pdb

from TWDataServices import TWDataWriter

INDEX_FILENAME = 'search-index.json'


class FileSystem(TWDataWriter):
    """
    Services to write data to the file system.
    """

    def __init__(self, dirname):
        """
        Initialize this instance.
        """
        self.dirname = dirname

        # Create directories
        self.subdir_cache = dict()
        self.index = list()


    def start(self):
        """
        Start processing
        """
        os.mkdir(self.dirname)
        os.mkdir(os.path.join(self.dirname, 'ind'))
        os.mkdir(os.path.join(self.dirname, 'fam'))
        os.mkdir(os.path.join(self.dirname, 'img'))
        os.mkdir(os.path.join(self.dirname, 'thm'))
        return None


    def export_individual(self, index_summary, info):
        """
        Export file. Must be implemented by a derived class.
        """
        pid = info['pid']
        cs_info = self.export_json('ind', pid, info['info'])
        cs_fam = self.export_json('fam', pid, info['fam'])

        # Write out summary records
        for rec in index_summary:
            rec['csi'] = cs_info
            rec['csf'] = cs_fam
        self.index.extend(index_summary)


    def export_json(self, subdir, gramps_id, data):
        """
        Export a json string to the file system.
        """
        json_data = json.dumps(data)
        if subdir:
            dirs = self.get_dir_for_gramps_id(gramps_id)
            self._create_subdirs(self.dirname, subdir, *dirs)
            fname = os.path.join(self.dirname, subdir, *dirs, gramps_id + '.json')
        else:
            fname = os.path.join(self.dirname, gramps_id + '.json')
        with open(fname, 'w') as ofile:
            ofile.write(json_data)
        return self.checksum(json_data)


    def export_image(self, subdir, gramps_id, ext, image):
        """
        Export an image to the file system.
        """
        dirs = self.get_dir_for_gramps_id(gramps_id)
        self._create_subdirs(self.dirname, subdir, *dirs)
        destfile = os.path.join(self.dirname, subdir, *dirs, gramps_id + ext)
        image.savev(destfile, 'jpeg', ['quality'], ['85'])


    def export_file(self, subdir, tgtfile, srcfile):
        """
        Export file to file system.
        """
        gramps_id = tgtfile.split('.')[0]
        dirs = self.get_dir_for_gramps_id(gramps_id)
        self._create_subdirs(self.dirname, subdir, *dirs)
        destfile = os.path.join(self.dirname, subdir, *dirs, tgtfile)
        copyfile(srcfile, destfile)


    def _create_subdirs(self, basedir, subdir, dir1, dir2):
        """
        Create subdirectories if necessary
        """
        # To speedup processing, check if we've already created these
        # subdirectories
        dirs = (subdir, dir1, dir2)
        if dirs in self.subdir_cache:
            return
        self.subdir_cache[dirs] = True

        # Create subdirectories
        dpath1 = os.path.join(basedir, subdir, dir1)
        if not os.path.isdir(dpath1):
            os.mkdir(dpath1)

        dpath2 = os.path.join(dpath1, dir2)
        if not os.path.isdir(dpath2):
            os.mkdir(dpath2)


    def finish(self):
        with open(os.path.join(self.dirname, INDEX_FILENAME), 'w') as outfile:
            for rec in self.index:
                outfile.write(json.dumps(rec) + "\n")
