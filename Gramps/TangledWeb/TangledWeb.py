#
# WordPressExport - Export files to be used in WordPress
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
"""Export data in a format to be used by a WordPress plugin."""

#------------------#
# Python modules   #
#------------------#
import os
import itertools
import operator
from functools import partial, reduce
from configparser import ConfigParser
from datetime import datetime
from shutil import copyfile
import json
from re import findall

import pdb

#----------------------------------------------------------------------------
# Gramps modules
#----------------------------------------------------------------------------
from gramps.gen.plug.report import Report, MenuReportOptions
from gramps.gen.plug.menu import (BooleanOption, StringOption,
                                  DestinationOption, PersonOption,
                                  NoteOption, MediaOption,
                                  FilterOption, EnumeratedListOption)
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.plug.docgen import ParagraphStyle, FontStyle, PARA_ALIGN_CENTER
from gramps.gen.config import config
from gramps.gen.plug.report import utils
from gramps.gen.const import HOME_DIR, USER_HOME, VERSION_DIR
from gramps.gen.utils.file import media_path_full, relative_path, media_path
from gramps.gen.utils.thumbnails import (get_thumbnail_image,
                                         SIZE_NORMAL, SIZE_LARGE)
from gramps.gen.plug.report import stdoptions
from gramps.gen.proxy import CacheProxyDb


#------------------#
# Gtk modules      #
#------------------#
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk


from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


#-------------------------#
# Tool specific modules   #
#-------------------------#
from TWHelper import TWPerson
from TWPedigree import Pedigree

Pedigree.set_max_generations(False)

MSG_REPORT_OPTIONS = _('Report Options')
MSG_DESTINATION = _('Destination')
MSG_DESTINATION_HELP = _('The destination directory for the web files')
MSG_WEBSITE_TITLE = _('Web site title')
MSG_DEFAULT_TITLE = _('My Family Tree')
MSG_WEBSITE_TITLE_HELP = _('The title of the web site')
MSG_FILTER = _('Filter')
MSG_FILTER_HELP = _('Select filter to restrict people that appear on web site')
MSG_FILTER_PERSON = _('Filter Person')
MSG_FILTER_PERSON_HELP = _('The center person for the filter')
MSG_BASE_PERSON = _('Base Person')
MSG_BASE_PERSON_HELP = _('Base person for default web page')

MSG_UPDATE_OPTIONS = _('Update Options')
MSG_LIMIT_CONTENT = _('What content to export')
MSG_LIMIT_ALL_CONTENT = _('All selected content')
MSG_LIMIT_LAST_UPDATE = _('Content changed since last report')
MSG_LIMIT_CONTENT_HELP = _('Just include content changed since specified date')
MSG_CONTENT_SINCE = _('Include content since')
MSG_CONTENT_SINCE_HELP = _('Defaults to date of last export')
MSG_TARGET = _('Target of export')
MSG_TARGET_DIRECTORY = _('Local file system')
MSG_TARGET_WORDPRESS = _('Wordpress')
MSG_TARGET_HELP = _('Output to file system, or to CMS')
MSG_TARGET_ID = _('Table identifier')
MSG_TARGET_ID_HELP = _('Table identifier on CMS')

MSG_INCLUDE = _('Include')
MSG_INCLUDE_IMAGES = _('Include images and media objects')
MSG_INCLUDE_IMAGES_HELP = _('Whether to include '
                            'a gallery of media objects')
MSG_INCLUDE_WITNESSES = _('Include witnesses')
MSG_INCLUDE_WITNESSES_HELP = _('Include witnesses to events')
MSG_INCLUDE_WITNESS_EVENTS = _('Include witness events')
MSG_INCLUDE_WITNESS_EVENTS_HELP = _('Include events where the primary person'
                                    ' is a witnesses to the event')
MSG_INCLUDE_NOTES = _('Include notes')
MSG_INCLUDE_NOTES_HELP = _('Include notes for persons and citations')
MSG_INCLUDE_LINKS = _('Include website links')
MSG_INCLUDE_LINKS_HELP = _('Include links to external websites')
MSG_INCLUDE_PEDIGREES = _('Include pedigrees')
MSG_INCLUDE_PEDIGREES_HELP = _('Include pedigrees for all individuals')
MSG_INCLUDE_RELS = _('Include relationships')
MSG_INCLUDE_RELS_HELP = _('Include relationship of referenced people')
MSG_INCLUDE_ALTERNATE_NAMES = _('Include alternate names in search index')
MSG_INCLUDE_ALTERNATE_NAMES_HELP = _('Include alternate names in search index file')
MSG_INCLUDE_RELFILE = _('Include relationships file')
MSG_INCLUDE_RELFILE_HELP = _('Include relationships file')

MSG_REDIRECT_OPTIONS = _('Redirects')
MSG_FROM_NARRATED = _('Generate redirects for existing narrated web site')
MSG_FROM_NARRATED_HELP = _('Generate redirects for persons on narrated web site')
MSG_NARRATED_DIR = _('Directory for existing narrated web site')
MSG_NARRATED_DIR_HELP = _('Full directory path for existing narrated web site')
MSG_CMS_PAGE = _('CMS page')
MSG_CMS_PAGE_HELP = _('Name of CMS page')
MSG_CMS_ID = _('CMS table id')
MSG_CMS_ID_HELP = _('CMS table id')

MSG_ERROR_NO_TARGET = _('Destination directory was not specified.')
MSG_ERROR_CREATING_DIR = _('Could not create the directory: %(dirname)s')

MSG_RESULT = _('Result of Tangled Web Export')
MSG_EXPORT_COMPLETE = _('Tangled Web export complete')
MSG_INDIVIDUALS_PROCESSED = _('Total individuals processed:')
MSG_IMAGES_PROCESSED = _('Total images processed:')
MSG_CLOSE = _('Close')


CONFIG_FILENAME = 'TangledWeb.ini'
INIFILE = os.path.join(VERSION_DIR, CONFIG_FILENAME)

MAX_CLOUD_NAMES = 40
NUM_SUBDIRS = 20

WP_config = ConfigParser()
if not WP_config.read(INIFILE):
    WP_config['WP'] = {'last_update': '' }

INDEX_FILENAME = 'search-index.json'
REDIR_INDEX_FILENAME = 'redir-index'
GLOBALS_FILENAME = 'globs.json'
DATA_DIR_LIMIT = 150


redirect_html = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="refresh" content="5; url=%(newurl)s" />
</head>
<body>
<div style="margin:auto">
<h1>Redirecting in...</h1>
<img style="border:none" src="/wp-content/plugins/TangledWeb/img/countdown.gif">
</div>
</body>
</html>
"""


def checksum(st):
    return reduce(operator.add, map(ord, st)) % 65536


#------------------------#
#                        #
# WordPressExport class  #
#                        #
#------------------------#

class TangledWeb(Report):
    """
    Export data in a format to be used by a WordPress plugin.
    """

    def __init__(self, database, options, user):
        Report.__init__(self, database, options, user)

        self.options = options
        self.menu = options.menu

        stdoptions.run_private_data_option(self, self.menu)
        stdoptions.run_living_people_option(self, self.menu)
        self.database = CacheProxyDb(self.database)

        TWPerson.set_database(self.database)

        optnames = ('incl_images',
                    'incl_witnesses',
                    'incl_witness_events',
                    'incl_notes',
                    'incl_links',
                    'incl_pedigrees',
                    'incl_rels',
                    'incl_altnames')
        opts = dict()
        get_option = self.menu.get_option_by_name;
        for optn in optnames:
            opts[optn] = get_option(optn).get_value()

        self.db = self.database
        self.user = user

        self.title = self.get_option('title')
        self.target = self.get_option('target')

        if not self.make_target_dirs():
            return

        self.all_people = None
        self.surnames = dict()
        self.home_image_path = ''
        self.home_image_desc = ''

        indi_count = self.process_individuals(opts)
        imgs_count = self.process_images(opts)
        self.process_summary()

        if get_option('redirect_narrated').get_value():
            narrdir = get_option('redirect_narr_dir').get_value()
            self._generate_redirects(narrdir)

        # Update .ini file
        WP_config['WP']['last_update'] = str(datetime.now())
        with open(INIFILE, 'w') as ini_file:
            WP_config.write(ini_file)

        CompletionWindow(indi_count, imgs_count)


    def get_option(self, opt):
        """
        Get option
        """
        return self.menu.get_option_by_name(opt).get_value()


    def make_target_dirs(self):
        """
        Check if target directory already exists. If so, exit with message.
        """
        dirname = self.target
        if not dirname:
            self.user.notify_error(MSG_ERROR_NO_TARGET)
            return

        try:
            os.mkdir(dirname)

            # Create lower level directories
            self.indis_path = os.path.join(dirname, 'ind')
            os.mkdir(self.indis_path)
            self.indsums_path = os.path.join(dirname, 'fam')
            os.mkdir(self.indsums_path)
            self.images_path = os.path.join(dirname, 'img')
            os.mkdir(self.images_path)
            self.thumbs_path = os.path.join(dirname, 'thm')
            os.mkdir(self.thumbs_path)

        except IOError as exc:
            msg = (MSG_ERROR_CREATING_DIR % {'dirname': dirname}) \
                  + "\n" + exc.strerror
            self.user.notify_error(msg)
            return False

        except Exception as exc:
            msg = MSG_ERROR_CREATING_DIR % dirname
            self.user.notify_error(msg)
            return False

        return True


    def process_individuals(self, options):
        """
        Process all selected individuals.
        """

        filters_option = self.menu.get_option_by_name('filter')
        filter = filters_option.get_filter()
        src_base = media_path(self.db)
        people_with_icons = dict()

        ind_list = self.db.iter_person_handles()
        ind_list = filter.apply(self.db, ind_list, user=self.user)
        self.all_people = list(ind_list)
        TWPerson.set_person_filter(self.all_people)

        # Create directories for individuals
        person_dirs = dict()
        for person_handle in self.all_people:
            person = self.db.get_person_from_handle(person_handle)
            pid = person.gramps_id
            dirnums = self._get_dir_for_object(pid)
            if dirnums not in person_dirs:
                person_dirs[dirnums] = True
                self._create_subdirs(self.indis_path, *dirnums)
                self._create_subdirs(self.indsums_path, *dirnums)

            # Create person icons for all people
            media_list = person.get_media_list()
            if media_list:
                media = self.db.get_media_from_handle(media_list[0].ref)
                med_path = media.get_path()
                if med_path[0] == os.sep:
                    srcfile = med_path
                else:
                    srcfile = os.path.join(src_base, med_path)

                people_with_icons[pid] = dirnums
                rect = media_list[0].get_rectangle()

                pixbuf = get_thumbnail_image(srcfile,
                                             rectangle=rect,
                                             size=SIZE_NORMAL)
                destfile = os.path.join(self.indsums_path, *dirnums,
                                        pid + '.jpg')
                pixbuf.savev(destfile, 'jpeg', ['quality'], ['85'])

                pixbuf = get_thumbnail_image(srcfile,
                                             rectangle=rect,
                                             size=SIZE_LARGE)
                destfile = os.path.join(self.indsums_path, *dirnums,
                                        pid + '.big.jpg')
                pixbuf.savev(destfile, 'jpeg', ['quality'], ['85'])

        TWPerson.set_people_with_icons(people_with_icons)

        with open(os.path.join(self.target, INDEX_FILENAME), 'w') as outfile:
            for person_handle in self.all_people:
                person = TWPerson(self.db, person_handle, options, self.menu)
                pid = person.person.gramps_id
                dirnums = self._get_dir_for_object(pid)

                # Get summary and info data
                summary = person.get_summary()
                info = person.get_info()
                info_info = json.dumps(info['info'])
                info_summ = json.dumps(info['summary'])
                cs = "%x,%x" % (checksum(info_info), checksum(info_summ))

                # Write out summary records
                for rec in summary:
                    rec['cs'] = cs
                    outfile.write(json.dumps(rec) + "\n")
                    surname = rec['surname']
                    if surname not in self.surnames:
                        self.surnames[surname] = 1
                    else:
                        self.surnames[surname] += 1

                # Write out info files
                have_icon = (pid in people_with_icons)
                info['summary']['ico'] = int(have_icon)
                fname = os.path.join(self.indis_path, *dirnums, pid + '.json')
                with open(fname, 'w') as ofile:
                    ofile.write(info_info)

                fname = os.path.join(self.indsums_path, *dirnums, pid + '.json')
                with open(fname, 'w') as ofile:
                    ofile.write(info_summ)

        return len(self.all_people)


    def _get_dir_for_object(self, gramps_id):
        """
        Get (possibly create) directories for person
        """
        pnum = int(''.join((c for c in gramps_id if c.isnumeric())))
        dir1 = chr(ord('a') + (pnum % NUM_SUBDIRS))
        dir2 = chr(ord('a') + ((pnum//NUM_SUBDIRS) % NUM_SUBDIRS))
        return (dir1, dir2)


    def _create_subdirs(self, basedir, dir1, dir2):
        """
        Ensure subdirectories are created
        """
        dpath1 = os.path.join(basedir, dir1)
        if not os.path.isdir(dpath1):
            os.mkdir(dpath1)

        dpath2 = os.path.join(dpath1, dir2)
        if not os.path.isdir(dpath2):
            os.mkdir(dpath2)


    def process_summary(self):
        """
        Output the summary record to the output.
        """

        # Get page generation options
        home_note_id = self.get_option('homenote')
        home_image_id = self.get_option('homeimg')

        if home_note_id:
            home_note = self.db.get_note_from_gramps_id(home_note_id)
            home_note_text = str(home_note.get_styledtext())
        else:
            home_note_text = ''

        surnames = sorted(self.surnames.items(), key=lambda x: x[1],
                          reverse=True)[0:MAX_CLOUD_NAMES]
        base_pid = self.get_option('pidbase');
        global_summary = {'timestamp': str(datetime.utcnow()),
                          'title': self.title,
                          'home_note': home_note_text,
                          'home_image': self.home_image_path,
                          'home_image_desc': self.home_image_desc,
                          'base_person': base_pid,
                          'cloud': surnames}

        global_filename = os.path.join(self.target, GLOBALS_FILENAME)
        with open(global_filename, 'w') as gfile:
            gfile.write(json.dumps(global_summary))


    def process_images(self, options):
        """
        Process the images:
        1) Determine new file name for the images
        2) Copy image to destination
        3) Create thumbnails for all images
        """
        include_images = options['incl_images']
        if not include_images:
            return

        # Process images
        all_images = True    # TODO: options['all_content']
        if not all_images:
            last_update = WP_config['WP']['last_update']
            last_update = datetime.strptime(last_update,
                                            '%Y-%m-%d %H:%M:%S.%f')
            last_update = last_update.timestamp()
        else:
            last_update = 0

        # Handle home page image
        home_image_id = self.get_option('homeimg')
        if home_image_id:
            home_image = self.db.get_media_from_gramps_id(home_image_id)
            home_media = TWPerson.add_image(home_image)
            self.home_image_desc = home_media['dsc']

        src_base = media_path(self.db)
        dest_base = self.menu.get_option_by_name('target').get_value()
        dest_base = os.path.join(dest_base, 'media')

        # Create full directory hierarchy
        images_count = 0
        media_dirs = dict()
        for (media_id, med_detail) in TWPerson.get_images():
            media = self.db.get_media_from_gramps_id(media_id)
            simage = media.get_path()
            if simage[0] == os.sep:
                srcfile = simage
            else:
                srcfile = os.path.join(src_base, simage)
            last_mod = os.stat(srcfile).st_mtime if not all_images else 1

            if last_mod > last_update:
                images_count += 1
                dirt = self._get_dir_for_object(media.gramps_id)
                if dirt not in media_dirs:
                    media_dirs[dirt] = True
                    self._create_subdirs(self.images_path, *dirt)
                    self._create_subdirs(self.thumbs_path, *dirt)

                timage = media.gramps_id + med_detail['ext']
                destfile = os.path.join(self.images_path, *dirt, timage)
                copyfile(srcfile, destfile)

                # Create thumbnail
                thm_name = media.gramps_id + '.jpg'
                pixbuf = get_thumbnail_image(srcfile, size=SIZE_LARGE)
                destfile = os.path.join(self.thumbs_path, *dirt, thm_name)
                pixbuf.savev(destfile, 'jpeg', ['quality'], ['85'])

                # Is this the home image?
                if media.gramps_id == home_image_id:
                    fname = media.gramps_id + home_media['ext']
                    self.home_image_path = os.path.join(*dirt, fname)

        return images_count


    def _generate_redirects(self, narrated_dir):
        """
        """
        with open(os.path.join(self.target, REDIR_INDEX_FILENAME), 'w') as outfile:
            for person_handle in self.all_people:
                person = self.db.get_person_from_handle(person_handle)
                outfile.write("%s,%s\n" %(person_handle, person.gramps_id))



#------------------------#
#                        #
# ReportOptions class    #
#                        #
#------------------------#

class TangledWebOptions(MenuReportOptions):
    """Report options for Media Report."""

    def __init__(self, name, database):
        self._db = database

        MenuReportOptions.__init__(self, name, database)


    def add_menu_options(self, menu):
        """Add the options to the report option menu."""

        self._add_report_options(menu)
        # self._add_update_options(menu)
        self._add_page_generation_options(menu)
        self._add_include_options(menu)
        self._add_redirect_options(menu)


    def _add_report_options(self, menu):
        """
        Options on the Report Options menu
        """
        category_name = MSG_REPORT_OPTIONS
        addopt = partial(menu.add_option, category_name)

        dbname = self._db.get_dbname()
        default_dir = dbname + ' WPWEB'
        dest_path = os.path.join(config.get('paths.website-directory'),
                                 default_dir)
        self._target = DestinationOption(MSG_DESTINATION, dest_path)
        self._target.set_help(MSG_DESTINATION_HELP)
        addopt('target', self._target)

        self._title = StringOption(MSG_WEBSITE_TITLE, MSG_DEFAULT_TITLE)
        self._title.set_help(MSG_WEBSITE_TITLE_HELP)
        addopt('title', self._title)

        self._filter = FilterOption(MSG_FILTER, 0)
        self._filter.set_help(MSG_FILTER_HELP)
        addopt('filter', self._filter)
        self._filter.connect('value-changed', self._filter_changed)

        self._pid = PersonOption(MSG_FILTER_PERSON)
        self._pid.set_help(MSG_FILTER_PERSON_HELP)
        addopt('pid', self._pid)
        self._pid.connect('value-changed', self._update_filters)

        stdoptions.add_living_people_option(menu, category_name)
        stdoptions.add_private_data_option(menu, category_name, default=False)

        self._pid_base = PersonOption(MSG_BASE_PERSON)
        self._pid_base.set_help(MSG_BASE_PERSON_HELP)
        addopt('pidbase', self._pid_base)

        self._update_filters()


    def _add_update_options(self, menu):
        """
        Options on the "Update Options" tab.
        """

        category_name = MSG_UPDATE_OPTIONS
        addopt = partial(menu.add_option, category_name)

        self.last_upd = WP_config['WP']['last_update']
        self.have_last_upd = bool(self.last_upd)
        init_limit = 'last' if self.have_last_upd else 'all'

        self._limit_content = EnumeratedListOption(MSG_LIMIT_CONTENT, init_limit)
        self._limit_content.add_item('all', MSG_LIMIT_ALL_CONTENT)
        self._limit_content.add_item('last', MSG_LIMIT_LAST_UPDATE)
        self._limit_content.set_help(MSG_LIMIT_CONTENT_HELP)
        self._limit_content.connect('value-changed', self._update_update_options)
        addopt('all_content', self._limit_content)
        self._limit_content.set_available(self.have_last_upd)

        self._content_since = StringOption(MSG_CONTENT_SINCE, self.last_upd)
        self._content_since.set_help(MSG_CONTENT_SINCE_HELP)
        addopt('content_since_date', self._content_since)
        self._content_since.set_available(self.have_last_upd)

        self._target = EnumeratedListOption(MSG_TARGET, 'dir')
        self._target.add_item('dir', MSG_TARGET_DIRECTORY)
        self._target.add_item('wp', MSG_TARGET_WORDPRESS)
        self._target.connect('value-changed', self._update_target_options)
        addopt('target', self._target)
        self._target.set_help(MSG_TARGET_HELP)

        self._target_id = StringOption(MSG_TARGET_ID, '')
        self._target_id.set_help(MSG_TARGET_ID_HELP)
        addopt('target_id', self._target_id)
        self._target_id.set_available(False)


    def _update_update_options(self):
        """
        Handle change to all images setting
        """
        limit_content = (self._limit_content.get_value() == 'last')
        self._content_since.set_available(limit_content)


    def _update_target_options(self):
        """
        Handle change to all images setting
        """
        wp_selected = (self._target.get_value() == 'wp')
        self._target_id.set_available(wp_selected)


    def _add_page_generation_options(self, menu):
        """
        Options on the "Page Generation" tab.
        """
        category_name = _("Page Generation")
        addopt = partial(menu.add_option, category_name)

        homenote = NoteOption(_('Home page note'))
        homenote.set_help(_("A note to be used on the home page"))
        addopt("homenote", homenote)

        homeimg = MediaOption(_('Home page image'))
        homeimg.set_help(_("An image to be used on the home page"))
        addopt("homeimg", homeimg)


    def _add_include_options(self, menu):
        """
        Optons on the "Include" tab.
        """
        category_name = MSG_INCLUDE
        addopt = partial(menu.add_option, category_name)

        self._gallery = BooleanOption(MSG_INCLUDE_IMAGES, True)
        self._gallery.set_help(MSG_INCLUDE_IMAGES_HELP)
        addopt('incl_images', self._gallery)

        self._incl_witnesses = BooleanOption(MSG_INCLUDE_WITNESSES, True)
        self._incl_witnesses.set_help(MSG_INCLUDE_WITNESSES_HELP)
        addopt('incl_witnesses', self._incl_witnesses)

        self._incl_witness_events = BooleanOption(MSG_INCLUDE_WITNESS_EVENTS,
                                                  True)
        self._incl_witness_events.set_help(MSG_INCLUDE_WITNESS_EVENTS_HELP)
        addopt('incl_witness_events', self._incl_witness_events)

        self._incl_notes = BooleanOption(MSG_INCLUDE_NOTES, True)
        self._incl_notes.set_help(MSG_INCLUDE_NOTES_HELP)
        addopt('incl_notes', self._incl_notes)

        self._incl_links = BooleanOption(MSG_INCLUDE_LINKS, True)
        self._incl_links.set_help(MSG_INCLUDE_LINKS_HELP)
        addopt('incl_links', self._incl_links)

        self._incl_pedigrees = BooleanOption(MSG_INCLUDE_PEDIGREES, True)
        self._incl_pedigrees.set_help(MSG_INCLUDE_PEDIGREES_HELP)
        addopt('incl_pedigrees', self._incl_pedigrees)

        self._incl_rels = BooleanOption(MSG_INCLUDE_RELS, True)
        self._incl_rels.set_help(MSG_INCLUDE_RELS_HELP)
        addopt('incl_rels', self._incl_rels)

        self._incl_altnames = BooleanOption(MSG_INCLUDE_ALTERNATE_NAMES, True)
        self._incl_altnames.set_help(MSG_INCLUDE_ALTERNATE_NAMES_HELP)
        addopt('incl_altnames', self._incl_altnames)


    def _add_redirect_options(self, menu):
        """
        Options on the "Update Options" tab.
        """

        category_name = MSG_REDIRECT_OPTIONS
        addopt = partial(menu.add_option, category_name)

        self._redirect_narrated = BooleanOption(MSG_FROM_NARRATED, False)
        self._redirect_narrated.set_help(MSG_FROM_NARRATED_HELP)
        self._redirect_narrated.connect('value-changed', self._update_redirect)
        addopt('redirect_narrated', self._redirect_narrated)

        self._narrated_dir = DestinationOption(MSG_NARRATED_DIR, '')
        self._narrated_dir.set_help(MSG_NARRATED_DIR_HELP)
        addopt('redirect_narr_dir', self._narrated_dir)

        self._cms_page = StringOption(MSG_CMS_PAGE, '')
        self._cms_page.set_help(MSG_CMS_PAGE_HELP)
        addopt('redirect_cms_page', self._cms_page)

        self._update_redirect()


    def _update_redirect(self):
        """
        """
        red_selected = self._redirect_narrated.get_value()
        self._narrated_dir.set_available(red_selected)
        self._cms_page.set_available(red_selected)



    def _update_filters(self):
        """
        Update the filter list based on the selected person
        """
        gid = self._pid.get_value()
        person = self._db.get_person_from_gramps_id(gid)
        filter_list = utils.get_person_filters(person, include_single=False)
        self._filter.set_filters(filter_list)


    def _filter_changed(self):
        """
        Handle filter change. If the filter is not specific to a person,
        disable the person option
        """
        filter_value = self._filter.get_value()
        if filter_value == 0:
            self._pid.set_available(False)
        else:
            self._pid.set_available(True)


class CompletionWindow(Gtk.Window):
    """
    Completion window displayed at end of processing
    """

    def __init__(self, total_inds, total_imgs):
        """
        """
        Gtk.Window.__init__(self, title=MSG_RESULT)
        self.set_default_size(400, 200)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.homogenous = False
        box.set_border_width(0)

        text = MSG_EXPORT_COMPLETE + "\n" \
               + MSG_INDIVIDUALS_PROCESSED + ' ' + str(total_inds) + "\n" \
               + MSG_IMAGES_PROCESSED + ' ' + str(total_imgs)

        # Results label
        results_label = Gtk.Label(label=text)
        box.pack_start(results_label, expand=True, fill=False, padding=5)

        # Button bar
        button_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        close_button = Gtk.Button.new_with_label(MSG_CLOSE)
        close_button.connect('clicked', lambda x: self.close())
        button_bar.pack_start(close_button, False, False, 5)

        box.pack_start(button_bar, expand=False, fill=False, padding=5)

        self.add(box)
        self.show_all()
