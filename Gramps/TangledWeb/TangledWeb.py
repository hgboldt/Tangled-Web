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
from functools import partial
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
from TWWordPress import WordPress
from TWFileSystem import FileSystem

Pedigree.set_max_generations(False)

MSG_REPORT_OPTIONS = _('Filter')
MSG_DESTINATION = _('Destination directory')
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

MSG_UPDATE_OPTIONS = _('Destination')
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

MAX_CLOUD_NAMES = 40

CONFIG_FILENAME = 'TangledWeb.ini'
INIFILE = os.path.join(VERSION_DIR, CONFIG_FILENAME)
WP_config = ConfigParser()
if not WP_config.read(INIFILE):
    WP_config['WP'] = {'last_update': '' }

REDIR_INDEX_FILENAME = 'redir-index'
GLOBALS_FILENAME = 'globs'
DATA_DIR_LIMIT = 150


#------------------------#
#                        #
# TangledWeb class       #
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

        self.all_people = None
        self.surnames = dict()
        self.home_image_path = ''
        self.home_image_desc = ''
        self.indi_count = 0
        self.imgs_count = 0

        # Get the data writer
        try:
            export_target = self.get_option('update_target')

            if export_target == 'dir':
                # Export to local file system
                if not self.target:
                    self.user.notify_error(MSG_ERROR_NO_TARGET)
                    return
                self.data_writer = FileSystem(self.target)

            elif export_target == 'wp':
                # Export directly to WordPress
                tgt_url = self.get_option('target_url')
                tgt_id = self.get_option('target_id')
                if not tgt_url or not tgt_id:
                    self.user.notify_error(MSG_ERROR_NO_TARGET)
                    return
                self.data_writer = WordPress(tgt_url, tgt_id)

        except IOError as exc:
            msg = exc.strerror + ': ' + exc.filename
            self.user.notify_error(msg)
            return

        except Exception as exc:
            self.user.notify_error(exc.strerror)
            return

        # Do processing
        msg = self.data_writer.start()
        if msg:
            self.user.notify_error(msg)
            return

        self.determine_individuals_to_process()
        progress = ProgressWindow()
        self.do_processing(opts, progress)
        self.process_summary()

        # Handle redirects (if requested)
        if export_target == 'dir':
            if get_option('redirect_narrated').get_value():
                narrdir = get_option('redirect_narr_dir').get_value()
                self._generate_redirects(narrdir)

        self.data_writer.finish()

        # Update .ini file
        WP_config['WP']['last_update'] = str(datetime.now())
        with open(INIFILE, 'w') as ini_file:
            WP_config.write(ini_file)

        text = MSG_EXPORT_COMPLETE + "\n" \
               + MSG_INDIVIDUALS_PROCESSED + ' ' + str(self.indi_count) + "\n" \
               + MSG_IMAGES_PROCESSED + ' ' + str(self.imgs_count)
        progress.set_step_name('Done!')
        progress.update(1.0, text)


    def do_processing(self, opts, progress):
        """
        Do the work
        """
        c = 0
        progress.set_step_name('Processing individuals')
        for (item, fract) in self.process_individuals(opts):
            c += 1
            if c == 10:
                c = 0
                progress.update(fract/2)
            while Gtk.events_pending():
                Gtk.main_iteration()
            if progress.cancel_requested():
                return

        progress.set_step_name('Processing images')
        for (item, fract) in self.process_images(opts):
            c += 1
            if c == 10:
                c = 0
                progress.update(0.5 + fract/2)
            while Gtk.events_pending():
                Gtk.main_iteration()
            if progress.cancel_requested():
                return


    def get_option(self, opt):
        """
        Get option
        """
        return self.menu.get_option_by_name(opt).get_value()


    def determine_individuals_to_process(self):
        """
        Figure out list of individuals to process
        """
        filters_option = self.menu.get_option_by_name('filter')
        filter = filters_option.get_filter()
        ind_list = self.db.iter_person_handles()
        ind_list = filter.apply(self.db, ind_list, user=self.user)
        self.all_people = list(ind_list)
        TWPerson.set_person_filter(self.all_people)

        # Figure out which people have icons
        self.people_with_icons = dict()
        for person_handle in self.all_people:
            person = self.db.get_person_from_handle(person_handle)
            pid = person.gramps_id
            media_list = person.get_media_list()
            if media_list:
                self.people_with_icons[pid] = True

        TWPerson.set_people_with_icons(self.people_with_icons)


    def process_individuals(self, options):
        """
        Process all selected individuals.
        """
        total_indis = len(self.all_people)
        count = 0
        src_base = media_path(self.db)

        for person_handle in self.all_people:
            person = TWPerson(self.db, person_handle, options, self.menu)
            pid = person.person.gramps_id

            # Get summary and info data
            index_summary = person.get_index_summary()
            info = person.get_info()

            # Write out info files
            self.data_writer.export_individual(index_summary, info)

            # Remember surnames
            for rec in index_summary:
                surname = rec['surname']
                if surname not in self.surnames:
                    self.surnames[surname] = 1
                else:
                    self.surnames[surname] += 1

            # Create person icons
            media_list = person.person.get_media_list()
            if media_list:
                media = self.db.get_media_from_handle(media_list[0].ref)
                med_path = media.get_path()
                if med_path[0] == os.sep:
                    srcfile = med_path
                else:
                    srcfile = os.path.join(src_base, med_path)
                rect = media_list[0].get_rectangle()

                # Normal icon
                pixbuf = get_thumbnail_image(srcfile, rectangle=rect,
                                             size=SIZE_NORMAL)
                self.data_writer.export_image('fam', pid, '.jpg', pixbuf)

                # Large icon
                pixbuf = get_thumbnail_image(srcfile, rectangle=rect,
                                             size=SIZE_LARGE)
                self.data_writer.export_image('fam', pid, '.big.jpg', pixbuf)

            count += 1;
            yield (pid, count/total_indis)

        self.indi_count = count


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
        self.data_writer.export_json(None, GLOBALS_FILENAME, global_summary)


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
        image_list = TWPerson.get_images()
        total_images = len(image_list)
        count = 0
        for (media_id, med_detail) in image_list:
            media = self.db.get_media_from_gramps_id(media_id)
            mid = media.gramps_id
            simage = media.get_path()
            if simage[0] == os.sep:
                srcfile = simage
            else:
                srcfile = os.path.join(src_base, simage)
            last_mod = os.stat(srcfile).st_mtime if not all_images else 1

            if last_mod > last_update:
                images_count += 1

                timage = mid + med_detail['ext']
                self.data_writer.export_file('img', timage, srcfile)

                # Create thumbnail
                pixbuf = get_thumbnail_image(srcfile, size=SIZE_LARGE)
                self.data_writer.export_image('thm', mid, '.jpg', pixbuf)

                # Is this the home image?
                if mid == home_image_id:
                    self.home_image_path = mid + home_media['ext']

            count += 1
            yield (media_id, count/total_images)

        self.imgs_count = images_count


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
        self._add_update_options(menu)
        self._add_page_generation_options(menu)
        self._add_include_options(menu)
        self._add_redirect_options(menu)


    def _add_report_options(self, menu):
        """
        Options on the Report Options menu
        """
        category_name = MSG_REPORT_OPTIONS
        addopt = partial(menu.add_option, category_name)

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

        self._update_target = EnumeratedListOption(MSG_TARGET, 'dir')
        self._update_target.add_item('dir', MSG_TARGET_DIRECTORY)
        self._update_target.add_item('wp', MSG_TARGET_WORDPRESS)
        self._update_target.connect('value-changed', self._update_update_options)
        addopt('update_target', self._update_target)
        self._update_target.set_help(MSG_TARGET_HELP)

        dbname = self._db.get_dbname()
        default_dir = dbname + ' WPWEB'
        dest_path = os.path.join(config.get('paths.website-directory'),
                                 default_dir)
        self._target = DestinationOption(MSG_DESTINATION, dest_path)
        self._target.set_help(MSG_DESTINATION_HELP)
        addopt('target', self._target)

        self._target_url = StringOption(_('Website to update'), '')
        self._target_url.set_help(_('URL of website to update'))
        addopt('target_url', self._target_url)

        self._target_id = StringOption(MSG_TARGET_ID, '')
        self._target_id.set_help(MSG_TARGET_ID_HELP)
        addopt('target_id', self._target_id)

        self._update_update_options()


    def _update_update_options(self):
        """
        Handle change to all images setting
        """
        tgt = self._update_target.get_value()
        if tgt == 'dir':
            self._target.set_available(True)
            self._target_url.set_available(False)
            self._target_id.set_available(False)

        elif tgt == 'wp':
            self._target.set_available(False)
            self._target_url.set_available(True)
            self._target_id.set_available(True)


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

        self._title = StringOption(MSG_WEBSITE_TITLE, MSG_DEFAULT_TITLE)
        self._title.set_help(MSG_WEBSITE_TITLE_HELP)
        addopt('title', self._title)

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


#------------------------#
#                        #
# ProgressWindow class   #
#                        #
#------------------------#

class ProgressWindow(Gtk.Window):
    """
    Show progress of export process
    """

    def __init__(self):
        """
        """
        Gtk.Window.__init__(self, title='Tangled Web Progress')
        self.set_border_width(10)
        self.set_default_size(400, 300)
        self.canceled = False

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.homogenous = False
        box.set_border_width(0)

        self.stepname = Gtk.Label()
        box.pack_start(self.stepname, expand=False, fill=False, padding=5)

        self.progressbar = Gtk.ProgressBar()
        box.pack_start(self.progressbar, expand=False, fill=False, padding=5)

        scw = Gtk.ScrolledWindow()
        self.textview = Gtk.TextView()
        scw.add(self.textview)
        box.pack_start(scw, expand=True, fill=True, padding=5)

        button_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.cancel_button = Gtk.Button.new_with_label(_('Cancel'))
        self.cancel_button.connect('clicked', self.cancel_processing)
        button_bar.pack_start(self.cancel_button, False, False, 5)

        close_button = Gtk.Button.new_with_label(MSG_CLOSE)
        close_button.connect('clicked', lambda x: self.close())
        button_bar.pack_start(close_button, False, False, 5)
        box.pack_start(button_bar, expand=False, fill=False, padding=5)

        self.add(box)
        self.show_all()

    def cancel_processing(self, x):
        self.canceled = True
        self.cancel_button.set_sensitive(False)
        self.output("Cancel requested\n")

    def cancel_requested(self):
        return self.canceled

    def set_step_name(self, step_name):
        self.stepname.set_text(step_name)

    def update(self, amount, item=None):
        self.progressbar.set_fraction(amount)
        if item:
            self.output(item + "\n")

    def output(self, text):
        buffer = self.textview.get_buffer()
        iter = buffer.get_end_iter()
        buffer.insert(iter, text)
        self.textview.scroll_to_iter(buffer.get_end_iter(), 0.0, False, 0.0, 1.0)
