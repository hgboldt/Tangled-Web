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
from html import escape
import requests

import pdb

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

from TWDataServices import TWDataWriter


class WordPress(TWDataWriter):
    """
    """

    def __init__(self, url, instance_id):
        """
        """
        self.url = url
        self.instance_id = instance_id
        self.logon_creds = None

        if not self.url.endswith('/'):
            self.url += '/'


    def start(self):
        """
        Start processing
        """
        # Request logon creds
        logon = WPLogon()
        rc = logon.run()
        self.logon_creds = logon.status()
        logon.destroy()
        if rc == WPLogon.CANCEL:
            return None

        # Logon to WordPress site
        self.session = requests.Session()
        parms = {'id': self.logon_creds['userid'],
                 'pw': self.logon_creds['password']}
        res = self.session.post(url=self.url + 'wp-json/tangled_web/start',
                                data=parms);
        if res.status_code != 200 or len(res.cookies.keys()) <= 1:
            return 'Login failed'

        data = json.loads(res.text);
        nonce = data['gonk']

        if not nonce:
            return 'Nonce not found'

        self.session.headers.update({'X-WP-Nonce': nonce})

        # Get checksums for all json files
        res = self.session.post(url=self.url + 'wp-json/tangled_web/status',
                                data={'tab': self.instance_id})
        if res.status_code != 200:
            data = json.loads(res.content)
            return data['message']

        data = json.loads(res.text)
        self.checksums = dict()
        for item in data['checksums']:
            self.checksums[item['pid']] = {'ind': item['csi'], 'fam': item['csf']}

        return None


    def export_json(self, subdir, gramps_id, data):
        """
        Export data as json file.
        """
        json_data = json.dumps(data)
        cs = self.checksum(json_data)
        if subdir:
            if gramps_id in self.checksums:
                if self.checksums[gramps_id][subdir] == cs:
                    return 0

        # Upload data

        return self.checksum(json_data)


    def export_image(self, subdir, gramps_id, ext, data):
        """
        Export image. Must be implemented by a derived class.
        """
        return


    def export_file(self, subdir, tgtfile, srcfile):
        """
        Export file to file system. Must be implemented by a derived class
        """
        return


    def finish(self):
        """
        Final processing for this instance.
        """
        return


class WPLogon(Gtk.Dialog):
    """
    """

    CANCEL = 1
    LOGON = 2

    def __init__(self):
        """
        """
        Gtk.Window.__init__(self, title='Logon to WordPress Site')
        self.set_border_width(10)
        self.set_default_size(400, 300)
        self.canceled = False
        self.logon_status = None

        box = self.get_content_area()
        grid = Gtk.Grid()
        grid.set_border_width(6)
        grid.set_row_spacing(6)
        grid.set_column_spacing(20)

        id_lab = Gtk.Label(label='User id:')
        grid.attach(id_lab, 0, 0, 1, 1)
        self.id_entry = Gtk.Entry()
        grid.attach(self.id_entry, 1, 0, 1, 1)
        pw_lab = Gtk.Label(label='Password')
        grid.attach(pw_lab, 0, 1, 1, 1)
        self.pw_entry = Gtk.Entry()
        grid.attach(self.pw_entry, 1, 1, 1, 1)
        box.pack_start(grid, expand=True, fill=True, padding=5)

        self.add_button('Cancel', self.CANCEL)
        self.add_button('Logon', self.LOGON)
        self.show_all()


    def status(self):
        """
        Return logon status
        """
        userid = self.id_entry.get_text()
        password = self.pw_entry.get_text()
        return {'userid': userid, 'password': password}
