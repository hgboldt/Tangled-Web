#
# TWHelper - Additional helper classes for TangledWeb export
#
# Copyright (C)    2020 Hans Boldt
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

"""Additional helper classes for TangledWeb export"""

#------------------#
# Python modules   #
#------------------#
import os
import itertools
from functools import partial
from datetime import datetime
import json
import imghdr
from html import escape
from math import log2

import pdb

#----------------------------------------------------------------------------
# Gramps modules
#----------------------------------------------------------------------------
from gramps.gen.lib import (Person, ChildRefType, EventType,
                            EventRoleType, UrlType)
from gramps.gen.plug.report import Report, MenuReportOptions
from gramps.gen.plug.menu import (BooleanOption, StringOption,
                                  DestinationOption, PersonOption,
                                  FilterOption)
from gramps.gen.utils.db import (get_birth_or_fallback,
                                 get_death_or_fallback)
from gramps.gen.relationship import get_relationship_calculator
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.utils.file import media_path
from gramps.gen.config import config
from gramps.gen.plug.report import utils
from gramps.gen.datehandler import get_date

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

#---------------------#
# Other modules       #
#---------------------#
from TWPedigree import Pedigree


primary_event_types = (EventType.BIRTH, EventType.DEATH, EventType.MARRIAGE)
WIKITREE_BASE = 'https://www.wikitree.com/wiki/'
ABS_FILE_LIMIT = 150
RELATIONSHIP_LIMIT = 8


class TWPerson():
    """
    Generate information about a person
    """

    all_people = None
    images_list = dict()
    abs_path_count = 0
    abs_file_count = 0
    relationships = list()
    people_with_icons = dict()
    db = None

    websites_checked = dict()


    @classmethod
    def set_database(cls, db):
        cls.db = db


    @classmethod
    def set_person_filter(cls, people_list):
        """
        Set list of all people to be included in the export
        """
        cls.all_people = dict()
        for p in people_list:
            cls.all_people[p] = 1


    @classmethod
    def set_people_with_icons(cls, people_list):
        """
        Set list of all people to be included in the export
        """
        cls.people_with_icons = people_list


    @classmethod
    def include_person(cls, person_handle):
        """
        Is this person eligible to be included in the export?
        """
        return person_handle in cls.all_people


    @classmethod
    def add_image(cls, image):
        """
        Add image to list
        """
        mid = image.gramps_id

        if mid not in cls.images_list:
            image_path = image.get_path()
            (fname, fext) = os.path.splitext(image_path)

            med = {'mid': image.gramps_id,
                   'ext': fext,
                   'dsc': escape(image.get_description())}

            cls.images_list[mid] = med

        return cls.images_list[mid]


    @classmethod
    def get_images(cls):
        """
        Return list of images used by person.
        """
        return cls.images_list.items()


    def __init__(self, database, person_handle, config,
                 menu):
        """
        init()
        """

        self.db = database
        self.menu = menu
        self.person_handle = person_handle
        self.options = config

        self.person = self.db.get_person_from_handle(person_handle)
        self.gender = self.person.get_gender()
        self.relcalc = get_relationship_calculator()
        self.citation_list = list()
        self.sources = {}

        self.parents = self._get_parents(self.db, self.person)
        self.fathers = None
        dadid = None
        self.mothers = None
        momid = None
        if self.parents[1]:
            self.fathers = self.parents[1]
            dad = self.db.get_person_from_handle(self.fathers[0][0])
            dadid = dad.gramps_id
        if self.parents[0]:
            self.mothers = self.parents[0]
            mom = self.db.get_person_from_handle(self.mothers[0][0])
            momid = mom.gramps_id
        self.spouses = self._get_spouses(person_handle)

        self.relationships.append([self.person.gramps_id, dadid, momid])


    def get_index_summary(self):
        """
        Get summary and names information.
        """
        dates = self._get_summary_dates()
        names = self._get_summary_names(True)
        reslist = list()
        pid = self.person.gramps_id
        for name in names:
            reslist.append({'pid': pid, **name, **dates})
        return reslist


    def _get_summary_dates(self):
        """
        Return summary dates for person:
        """

        # Birth and death dates:
        summary = dict()
        bevent = get_birth_or_fallback(self.db, self.person)
        if bevent:
            place_handle = bevent.get_place_handle()
            place_name = self.get_full_place_name(place_handle) \
                              if place_handle else ''
            summary['bplace'] = place_name
            summary['btype'] = 'B' if bevent.get_type() == 'Birth' else 'P'
            summary['bdate'] = self._get_date(bevent)
            summary['byear'] = bevent.get_date_object().get_year()

        devent = get_death_or_fallback(self.db, self.person)
        if not devent and not bevent:
            stillbirth = self._look_for_stillbirth_event(self.person)
            if stillbirth:
                devent = stillbirth

        if devent:
            place_handle = devent.get_place_handle()
            place_name = self.get_full_place_name(place_handle) \
                              if place_handle else ''
            ev_type = devent.get_type()
            if ev_type == 'Stillbirth':
                ev_code = 'S'
            elif ev_type == 'Burial':
                ev_code = 'B'
            else:
                ev_code = 'D'
            summary['dplace'] = place_name
            summary['dtype'] = ev_code
            summary['ddate'] = self._get_date(devent)
            summary['dyear'] = devent.get_date_object().get_year()

        return summary


    def _get_summary_names(self, forindex=False):
        """
        Return list of alternate names for person.
        """
        retlist = list()
        primary_name = self.person.get_primary_name()
        retlist.append(self._handle_one_name(primary_name, True, forindex))
        for name in self.person.get_alternate_names():
            retlist.append(self._handle_one_name(name, False, forindex))
        return retlist


    def _handle_one_name(self, name, primary, forindex):
        """
        Handle one name
        """
        surname_list = name.get_surname_list()
        surname_type = surname_list[0].origintype.string

        namerec = {'surname': name.get_surname(),
                   'given': name.get_first_name(),
                   'prim': ('1' if primary else '0')}
        nick = name.get_nick_name()
        if nick:
            namerec['nick'] = nick
        if forindex:
            namerec['gdr'] = ('M' if self.gender == Person.MALE else 'F');
        else:
            namerec['nametype'] = str(name.get_type())
            namerec['surnametype'] = surname_type;
            citations = name.get_citation_list()
            if citations:
                namerec['cits'] = self._add_citations(citations)
        return namerec


    def get_info(self):
        """
        Return detailed information about person format.
        1) Gramps id
        2) Detailed information
           a) Spouses and children
           b) Events
           c) Source/citations
           d) Image gallery (if requested)
        """
        pid = self.person.gramps_id
        info = {'pid': pid }

        info['gdr'] = 'M' if self.gender == Person.MALE else 'F'
        info['names'] = self._get_summary_names()
        info['summary'] = self._get_summary_dates()
        citations = self.person.get_citation_list()
        if citations:
            info['cits'] = self._add_citations(citations)
        info['events'] = self._handle_event_info()
        if self.options['incl_pedigrees']:
            info['pedigree'] = self._handle_pedigree()
        if self.options['incl_images']:
            gallery = self._handle_gallery()
            if gallery:
                info['gallery'] = gallery
        if self.options['incl_notes']:
            notes = self._handle_notes(self.person)
            if notes:
                info['notes'] = notes
        info['sources'] = self._handle_sources_info()
        if self.options['incl_links']:
            links = self._handle_links()
            if links:
                info['links'] = links

        date = self.person.get_change_time()
        info['lastupdate'] = datetime.fromtimestamp(date).strftime(
                                    '%Y-%m-%d %H:%M:%S')

        (pars, fams) = self._handle_family_info()

        faminfo = {'pid': pid,
                   'famc': pars,
                   'fams': fams}

        return {'pid': pid,
                'info': info,
                'fam': faminfo}


    def _handle_family_info(self):
        """
        Get detailed info about the family
        """

        # Parents
        pars = {}
        # ### hndls = self._get_parents(self.db, self.person)

        if self.fathers:
            father = self.fathers[0]
            if self.include_person(father[0]):
                dad = self.db.get_person_from_handle(father[0])
                dadlink = self._get_person_link(dad, dates=True)
                if father[1] != ChildRefType.BIRTH:
                    dadlink['ado'] = father[1].string
                pars['dad'] = dadlink

        if self.mothers:
            mother = self.mothers[0]
            if self.include_person(mother[0]):
                mom = self.db.get_person_from_handle(mother[0])
                momlink = self._get_person_link(mom, dates=True)
                if mother[1] != ChildRefType.BIRTH:
                    momlink['ado'] = mother[1].string
                pars['mom'] = momlink

        fams = list()

        for fam_handle in self.person.get_family_handle_list():
            family = self.db.get_family_from_handle(fam_handle)
            if not family:
                continue

            # Get spouse
            if self.gender == Person.MALE:
                spouse_handle = family.get_mother_handle()
            else:
                spouse_handle = family.get_father_handle()
            if spouse_handle:
                spouse = self.db.get_person_from_handle(spouse_handle)
                link = self._get_person_link(spouse, dates=True,
                                             rel=True, skip_spouse=True)
                if link:
                    spouse_id = link
                else:
                    spouse_id = family.gramps_id
            else:
                spouse_id = family.gramps_id

            # Get children
            children = list()
            child_ref_list = family.get_child_ref_list()
            if child_ref_list:
                for child_ref in child_ref_list:
                    child = self.db.get_person_from_handle(child_ref.ref)
                    link = self._get_person_link(child, dates=True)
                    if link:
                        children.append(link)

            fams.append([spouse_id, children])

        return pars, fams


    def _get_person_link(self, person, dates=False, rel=False,
                         skip_spouse=False, except_spouse=None):
        """
        Get link information to specified person.
        Returns dict:
            pid: gramps id
            sur: surname
            giv: given names
            gdr: gender
            dat: (opt) vital dates
            rel: (opt) relationship to primary person
            ico: (opt) '1': person has an icon
            ado: (opt) adoption
        """
        if not self.include_person(person.get_handle()):
            return None

        pid = person.gramps_id
        name = person.get_primary_name()

        plink = {'pid': pid,
                 'sur': name.get_surname(),
                 'giv': name.get_first_name(),
                 'gdr': ('M' if person.get_gender() == Person.MALE else 'F')}

        if dates and not person.get_privacy():
            plink['dat'] = self.get_vital_dates(person)

        if rel:
            plink['rel'] = self._get_relationship(person, skip_spouse,
                                                  except_spouse)

        if person.gramps_id in self.people_with_icons:
            plink['ico'] = '1'

        return plink

    @classmethod
    def get_vital_dates(cls, person):
        """
        """
        vitals = ''
        bstr = ''
        birth_event = get_birth_or_fallback(cls.db, person)
        if birth_event:
            event_date = cls._get_date(birth_event)
            if event_date:
                if birth_event.get_type() == 'Birth':
                    bstr = '*' + event_date
                else:
                    bstr = '~<i>' + event_date + '</i>'

        dstr = ''
        death_event = get_death_or_fallback(cls.db, person)
        if death_event:
            event_date = cls._get_date(death_event)
            if event_date:
                if death_event.get_type() == 'Death':
                    dstr = '+' + event_date
                else:
                    dstr = '[]<i>' + event_date + '</i>'

        if bstr and dstr:
            vitals = bstr + ', ' + dstr
        elif bstr:
            vitals = bstr
        elif dstr:
            vitals = dstr
        else:
            stillbirth = cls._look_for_stillbirth_event(person)
            if stillbirth:
                event_date = cls._get_date(stillbirth)
                if event_date:
                    vitals = '+*%s' % event_date
        return vitals


    @classmethod
    def _look_for_stillbirth_event(cls, person):
        """
        Look for a stillbirth event.
        """
        # Get events for person
        event_ref_list = person.get_event_ref_list()
        for event_ref in event_ref_list:
            if event_ref.get_role() == EventRoleType.PRIMARY:
                event = cls.db.get_event_from_handle(event_ref.ref)
                if event.get_type() == 'Stillbirth':
                    return event

        return None


    def _handle_event_info(self):
        """
        Determine the list of event
        """
        event_list = list()
        events = self._get_events(children=True)

        # Locate last event, either Death or Burial
        last_event = None
        for ev in events:
            if ev['events'][0]['role'] == 'Primary':
                event_type = ev['events'][0]['event'].get_type()
                if event_type in [EventType.DEATH, EventType.BURIAL]:
                    last_event = ev

        # Go through list of dates
        self.show_parents_on_birth_event = True
        for one_date in events:
            this_date = {'date': one_date['datestr'],
                         'events': list()}

            # Go through individual events on this date
            for ev in one_date['events']:
                event_info = self._handle_one_event(ev['event'], ev['role'])
                if event_info:
                    this_date['events'].append(event_info)

            # Save information in result list
            if this_date['events']:
                event_list.append(this_date)

            # End at last event
            if one_date == last_event:
                break

        return event_list


    def get_full_place_name(self, place_handle):
        """
        Return string of full place name
        """
        place_list = list()
        while place_handle:
            place = self.db.get_place_from_handle(place_handle)
            place_list.append(place.name.get_value())

            placeref_list = place.get_placeref_list()
            if not placeref_list:
                break

            place_handle = placeref_list[0].ref

        return ', '.join(place_list)


    def _handle_one_event(self, event, role):
        """
        Handle one event.
        """
        primary_roles = ['Primary', 'Family']
        event_type = event.get_type()
        event_str = str(event_type)

        event_data = {'event': str(event_type),
                      'role': role}
        citations = event.get_citation_list()
        if citations:
            event_data['cits'] = self._add_citations(citations)

        if role in primary_roles:
            attrs = self._get_attributes(event)
            if attrs:
                event_data['attrs'] = attrs

        place_handle = event.get_place_handle()
        if place_handle:
            event_data['place'] = self.get_full_place_name(place_handle)
        descr = event.get_description()
        if descr:
            event_data['desc'] = escape(str(descr))

        participants_list = list()
        participants = self._get_event_participants(event)

        if role == 'Primary':
            if event_type in [EventType.BIRTH, EventType.BAPTISM]:
                if self.show_parents_on_birth_event:
                    self.show_parents_on_birth_event = False
                    hndls = self.relcalc.get_birth_parents(self.db, self.person)
                    if hndls[1] and self.include_person(hndls[1]):
                        dad = self.db.get_person_from_handle(hndls[1])
                        link = self._get_person_link(dad)
                        if link:
                            event_data['father'] = link
                    if hndls[0] and self.include_person(hndls[0]):
                        mom = self.db.get_person_from_handle(hndls[0])
                        link = self._get_person_link(mom)
                        if link:
                            event_data['mother'] = link
            self._handle_others(event_data, participants)

        elif role == 'Family':
            if event_type in [EventType.MARRIAGE, EventType.MARR_BANNS,
                              EventType.DIVORCE]:
                family = None
                for p in participants:
                    if p[0] == 'Family':
                        family = self.db.get_family_from_handle(p[1])
                        break
                if family:
                    father_handle = family.get_father_handle()
                    if father_handle == self.person.get_handle():
                        spouse_handle = family.get_mother_handle()
                    else:
                        spouse_handle = father_handle

                    if spouse_handle:
                        spouse = self.db.get_person_from_handle(spouse_handle)
                        link = self._get_person_link(spouse)
                        if link:
                            event_data['spouse'] = link
                self._handle_others(event_data, participants)

        elif role == 'Parent':
            if event_type in [EventType.MARRIAGE, EventType.MARR_BANNS,
                              EventType.DIVORCE]:
                family = None
                for p in participants:
                    if p[0] == 'Family':
                        family = self.db.get_family_from_handle(p[1])
                        break
                (husb, wife) = self._get_bride_groom_from_family(family)
                if husb:
                    event_data['husband'] = husb
                if wife:
                    event_data['wife'] = wife

            else:
                try:
                    child_handle = self._filter_participants \
                          (participants, EventRoleType.PRIMARY)[0][1]
                except:
                    pdb.set_trace()

                child = self.db.get_person_from_handle(child_handle)
                link = self._get_person_link(child)
                if link:
                    event_data['child'] = link

        elif role == 'Spouse':
            spouse_handle = self._filter_participants \
                      (participants, EventRoleType.PRIMARY)[0][1]
            spouse = self.db.get_person_from_handle(spouse_handle)
            link = self._get_person_link(spouse)
            if link:
                event_data['spouse'] = link

        else: # All other roles
            family = None
            prim_info = None
            for p in participants:
                if p[0] == 'Family':
                    family = self.db.get_family_from_handle(p[1])
                    break
                if p[0] == 'Person' and p[2] == EventRoleType.PRIMARY:
                    prim_info = p
                    break

            if family:
                (husb, wife) = self._get_bride_groom_from_family(family)
                if husb:
                    event_data['husband'] = husb
                if wife:
                    event_data['wife'] = wife

            elif prim_info:
                prim = self.db.get_person_from_handle(prim_info[1])
                link = self._get_person_link(prim, rel=True)
                if link:
                    event_data['primary'] = link

        return event_data


    def _get_bride_groom_from_family(self, family):
        """
        Get the bride and groom from the family
        """
        husb = None
        wife = None
        if not family:
            return (None, None)
        husb_handle = family.get_father_handle()
        wife_handle = family.get_mother_handle()
        if husb_handle:
            husb = self.db.get_person_from_handle(husb_handle)
            husb = self._get_person_link(husb, rel=True,
                                         except_spouse=wife_handle)
        if wife_handle:
            wife = self.db.get_person_from_handle(wife_handle)
            wife = self._get_person_link(wife, rel=True,
                                         except_spouse=husb_handle)
        return (husb, wife)


    def _handle_others(self, event_data, participants):
        """
        Add other participants to event data
        """
        if not self.options['incl_witnesses']:
            return
        others_list = list()
        for part in participants:
            if part[0] == 'Person' and part[2] != EventRoleType.PRIMARY:
                other = self.db.get_person_from_handle(part[1])
                other_link = self._get_person_link(other, rel=True)
                if other_link:
                    others_list.append((part[2].string, other_link))
        if others_list:
            event_data['others'] = others_list

    def _get_relationship(self, other, skip_spouse=False, except_spouse=None):
        """
        Get relationship between self and an other person.

        There are 3 possible types of related witness:
        1) relative of primary person
           ie: "first cousin"
        2) relative of spouse of primary person (in-law)
           ie: "first cousin of wife {name of wife}"
        3) spouse of relative of primary person
           ie: "husband of first cousin {name of cousin}"
        """

        # Case #1: relative of primary
        relstr = self._get_relstr(self.person, other, skip_spouse).split(' (')[0]
        if relstr:
            return relstr

        # Case #2: relationship with spouse of person
        for spouse_handle in self.spouses:
            spouse = self.db.get_person_from_handle(spouse_handle)
            relstr = self._get_relstr(spouse, other, skip_spouse=True)
            if relstr:
                spouse_type = (' of husband' if spouse.get_gender() == Person.MALE
                                 else ' of wife')
                relstr = [relstr.split(' (')[0] + spouse_type,
                           self._get_person_link(spouse)]
                return relstr

        if skip_spouse:
            return ''

        # Case #3: relationship with spouse of witness
        other_handle = other.get_handle()
        for witspouse_handle in self._get_spouses(other_handle):
            if witspouse_handle != except_spouse:
                spouse = self.db.get_person_from_handle(witspouse_handle)
                relstr = self._get_relstr(self.person, spouse)
                if relstr:
                    wit_type = ('husband of ' if other.get_gender() == Person.MALE
                                     else 'wife of ')
                    relstr = [wit_type + relstr.split(' (')[0],
                               self._get_person_link(spouse)]
                    return relstr

        return ''


    def _get_relstr(self, person, other, skip_spouse=False):
        """
        Get relationship string
        """
        rels = self.relcalc.get_all_relationships(self.db, person, other)[0]
        if skip_spouse:
            while rels and rels[0] in ['wife', 'husband', 'partner',
                                       'ex-wife', 'ex-husband', 'former partner']:
                rels.pop(0)

        if not rels: return ''
        return rels[0].split(' (')[0]


    def _filter_participants(self, participants, role):
        """
        Get participants with specified role.
        """
        return [x for x in participants if x[2] == role]


    def _get_events(self, children=False):
        """
        Get list of events for person
        """
        events = list()

        # Get events for person
        event_ref_list = self.person.get_event_ref_list()
        for event_ref in event_ref_list:
            event = self.db.get_event_from_handle(event_ref.ref)
            ev = self._make_event(event_ref.role.string, event, event_ref)
            events.append(ev)

        # Get family marriage and child birth/death events
        for family_handle in self.person.get_family_handle_list():
            family = self.db.get_family_from_handle(family_handle)

            # Get family events
            for event_ref in family.get_event_ref_list():
                event = self.db.get_event_from_handle(event_ref.ref)
                ev = self._make_event(event_ref.role.string, event, event_ref)
                self._insert_event(events, ev)

                # Get death event for spouse
                if self.gender == Person.MALE:
                    spouse_handle = family.get_mother_handle()
                else:
                    spouse_handle = family.get_father_handle()
                if spouse_handle:
                    spouse = self.db.get_person_from_handle(spouse_handle)
                    death_event = get_death_or_fallback(self.db, spouse)
                    if death_event:
                        ev = self._make_event('Spouse', death_event)
                        self._insert_event(events, ev)

            # Get birth, marriage, and death events for children
            if children:
                for child_ref in family.get_child_ref_list():
                    child = self.db.get_person_from_handle(child_ref.ref)

                    birth_event = get_birth_or_fallback(self.db, child)
                    if birth_event:
                        ev = self._make_event('Parent', birth_event)
                        self._insert_event(events, ev)

                    death_event = get_death_or_fallback(self.db, child)
                    if death_event:
                        ev = self._make_event('Parent', death_event)
                        self._insert_event(events, ev)

                    marr_event = None
                    marr_banns_event = None
                    for family_handle in child.get_family_handle_list():
                        family = self.db.get_family_from_handle(family_handle)
                        for event_ref in family.get_event_ref_list():
                            event = self.db.get_event_from_handle(event_ref.ref)
                            if event:
                                event_type = event.get_type()
                                if event_type == EventType.MARRIAGE:
                                    marr_event = event
                                    break
                                if event_type == EventType.MARR_BANNS:
                                    marr_banns_event = event

                    marr = marr_event or marr_banns_event
                    if marr:
                        ev = self._make_event('Parent', marr)
                        self._insert_event(events, ev)

        # Add in marriage of parents
        marr_event = None
        marr_banns_event = None
        divorce_event = None
        for family_handle in self.person.get_parent_family_handle_list():
            family = self.db.get_family_from_handle(family_handle)
            for event_ref in family.get_event_ref_list():
                event = self.db.get_event_from_handle(event_ref.ref)
                ev = self._make_event('Child', event, event_ref)
                event_type = event.get_type()
                if not marr_event and event_type == EventType.MARRIAGE:
                    marr_event = ev
                if not marr_banns_event and event_type == EventType.MARR_BANNS:
                    marr_banns_event = ev
                if not divorce_event and event_type == EventType.DIVORCE:
                    divorce_event = ev

        if marr_event:
            self._insert_event(events, marr_event)
        elif marr_banns_event:
            self._insert_event(events, marr_banns_event)
        if divorce_event:
            self._insert_event(events, divorce_event)

        # Add in deaths of parents
        parents = self.relcalc.get_birth_parents(self.db, self.person)
        if parents[1] and self.include_person(parents[1]):
            dad = self.db.get_person_from_handle(parents[1])
            death_event = get_death_or_fallback(self.db, dad)
            if death_event:
                event = self._make_event('Child', death_event)
                self._insert_event(events, event)
        if parents[0] and self.include_person(parents[0]):
            mom = self.db.get_person_from_handle(parents[0])
            death_event = get_death_or_fallback(self.db, mom)
            if death_event:
                event = self._make_event('Child', death_event)
                self._insert_event(events, event)

        # Merge events with same date
        res_events = list()
        while events:
            ev = events.pop(0)
            if res_events and res_events[-1]['date'] == ev['date']:
                event_type = ev['events'][0]['event'].get_type()
                if event_type in primary_event_types \
                and ev['events'][0]['role'] == 'Primary':
                    res_events[-1]['events'].insert(0, ev['events'][0])
                else:
                    res_events[-1]['events'].append(ev['events'][0])
            else:
                res_events.append(ev)

        # Final sort of events
        res_events.sort(key=lambda x: x['date'])
        return res_events


    def _make_event(self, role, event, event_ref=None):
        """
        Make event detail structure
        """
        return {'date': event.get_date_object(),
                'datestr': self._get_date(event),
                'events': [ {
                      'role': role,
                      'event': event,
                      'eventref': event_ref } ] }


    def _insert_event(self, event_list, event):
        """
        Merge the event into the list of events.
        Note that events on the same date have not yet been merged.
        """
        i = 0
        while i < len(event_list):
            event_date = event_list[i]['date']
            if event_date:
                if event_date > event['date']:
                    event_list.insert(i, event)
                    return
                if event_date == event['date']:
                    ev = event_list[i]['events'][0]['event']
                    if ev == event['events'][0]['event']:
                        # event is already in list
                        #if event['events'][0]['role'] == 'Parent':
                        #    pdb.set_trace()
                        return
            i += 1
        event_list.append(event)


    def _get_event_participants(self, event):
        """
        Get all participants in specified event

        Return list of lists:
            0: gramps object type
            1: handle
            2: role
        """
        res_participants = list()
        event_handle = event.get_handle()
        participants = list(self.db.find_backlink_handles(event_handle,
                                    include_classes=['Person', 'Family']))

        # Determine roles for each participant
        for p in participants:
            plist = list(p)
            if p[0] == 'Person':
                person = self.db.get_person_from_handle(p[1])
                event_refs = person.get_event_ref_list()
                for evref in event_refs:
                    if evref.ref == event_handle:
                        plist.append(evref.get_role())
                        break

            elif p[0] == 'Family':
                family = self.db.get_family_from_handle(p[1])
                event_refs = family.get_event_ref_list()
                for evref in event_refs:
                    if evref.ref == event_handle:
                        plist.append(evref.get_role())
                        break

            res_participants.append(plist)

        return res_participants


    def _handle_links(self):
        """
        Handle links to external web sites.
        """
        ret_list = list()

        url_list = self.person.get_url_list()
        for url in url_list:
            type = url.get_type()
            if type ==  UrlType.WEB_HOME:
                path = url.get_full_path()
                desc = url.get_description()
                ret_list.append((desc, path))

        attr_list = self.person.get_attribute_list()
        for attr in attr_list:
            if attr.get_type() == 'WikiTree':
                wt_link = json.loads(attr.get_value())
                url = WIKITREE_BASE + wt_link['id']
                ret_list.append(('WikiTree', url))

        return ret_list


    def _add_citations(self, citations):
        """
        Add citations.
        """
        cit_list = list()

        for cit_handle in citations:
            citation = self.db.get_citation_from_handle(cit_handle)
            source_handle = citation.source_handle
            source = self.db.get_source_from_handle(source_handle)

            if source_handle in self.sources:
                src_num = self.sources[source_handle]['num']
                cit_handle_list = self.sources[source_handle]['citation handles']
                handle_list = list(hndl[1] for hndl in cit_handle_list)
                if cit_handle in handle_list:
                    i = handle_list.index(cit_handle)
                    cit_num = self._get_cit_number(i)
                else:
                    cit_num = self._get_cit_number(len(cit_handle_list))
                    cit_handle_list.append((src_num+cit_num, cit_handle))
            else:
                src_num = str(len(self.sources)+1)
                self.sources[source_handle] = {
                        'num': src_num,
                        'src': source,
                        'citation handles': [(src_num+'a', cit_handle)]
                    }
                src_num = self.sources[source_handle]['num']
                cit_num = 'a'

            cit_list.append(src_num + cit_num)

        return cit_list


    def _get_cit_number(self, n):
        """
        Map number n into an alphabetic count: a, b, c, ..., z, aa, ab, ...
        """
        alpha = 'abcdefghijklmnopqrstuvwxyz'
        b = 26
        if n == 0:
            return 'a'
        digits = []
        first = True
        while n:
            dig = n%b
            if not first:
                dig -= 1
            digits.append(dig)
            n //= b
            first = False
        digits.reverse()
        return ''.join([alpha[x] for x in digits])


    def _handle_sources_info(self):
        """
        Handle sources and citations
        """
        sources = list()
        for src_key in self.sources:
            source = dict()
            src = self.sources[src_key]

            source['srcnum'] = src['num']
            source['title'] = escape(src['src'].get_title())
            source['cits'] = list()
            attrs = self._get_attributes(src['src'])
            if attrs:
                source['attrs'] = attrs

            for (cit_num, cit_handle) in src['citation handles']:
                citation = dict()
                cit = self.db.get_citation_from_handle(cit_handle)

                citation['citnum'] = cit_num
                dat = self._get_date(cit)
                if dat:
                    citation['date'] = dat
                pag = cit.get_page()
                if pag:
                    citation['page'] = pag
                attrs = self._get_attributes(cit)
                if attrs:
                    citation['attrs'] = attrs

                if self.options['incl_images']:
                    media_list = cit.get_media_list()
                    if media_list:
                        citation['media'] = list()
                        for mediaref in media_list:
                            media = self.db.get_media_from_handle(mediaref.ref)
                            media_path = media.get_path()
                            if self._image_okay_to_include(media_path):
                                med = self.add_media(mediaref)
                                citation['media'].append(med)

                if self.options['incl_notes']:
                    notes = self._handle_notes(cit)
                    if notes:
                        citation['notes'] = notes

                source['cits'].append(citation)

            sources.append(source)

        return sources


    def _get_attributes(self, gobj):
        """
        Get Attributes
        """
        attr_list = gobj.get_attribute_list()
        attrs = list()
        for attr in attr_list:
            dattr = {'attr': attr.get_type().string,
                     'val': attr.get_value()}
            if hasattr(attr, 'get_citation_list'):
                citations = attr.get_citation_list()
                if citations:
                    dattr['cits'] = self._add_citations(citations)
            attrs.append(dattr)
        return attrs


    def _handle_gallery(self):
        """
        Handle the photo gallery
        """
        photo_list = list()

        media_list = self.person.get_media_list()
        for mediaref in media_list:
            media = self.db.get_media_from_handle(mediaref.ref)
            media_path = media.get_path()
            if self._image_okay_to_include(media_path):
                med = self.add_media(mediaref)
                photo_list.append(med)

        return photo_list


    def _image_okay_to_include(self, image_path):
        """
        Is this an acceptable image type to include?
        """
        filepath = os.path.join(media_path(self.db), image_path)
        filetype = imghdr.what(filepath)
        return filetype in ('gif', 'jpeg', 'png')


    def _handle_pedigree(self):
        """
        Process the pedigree for the person
        """
        result = dict()
        ped = dict()

        pedigree = Pedigree.make_pedigree(self.db, self.person_handle)

        ped_collapse = {}
        have_collapse = False
        if pedigree.has_pedigree_collapse():
            have_collapse = True
            result['collapse'] = True
            ped_collapse = pedigree.determine_pedigree_collapse()

        for (primary, anc_num, primary_num) in pedigree.get_pedigree():
            if primary:
                ancestor = pedigree.get_ancestor_by_number(anc_num)
                panc = self.db.get_person_from_handle(ancestor.person_handle)
                plink = self._get_person_link(panc, dates=True)

                collapse = None
                if have_collapse and anc_num%2 == 1:
                    # For female ancestors, determine consanguinity for
                    # the couple
                    childnum = anc_num//2
                    if childnum in ped_collapse:
                        collapse = list()
                        ped_count = 0

                        for coll in ped_collapse[childnum]:
                            c = list()
                            ancs = coll[0] # just consider first ancestor
                            genp = int(log2(anc_num))
                            gena1 = int(log2(ancs[0])) - genp
                            gena2 = int(log2(ancs[1])) - genp
                            relstr = self.relcalc \
                                .get_plural_relationship_string(gena1, gena2)
                            relstr = relstr.split(' (')[0]

                            if len(coll) == 1:
                                relstr = 'half ' + relstr
                            c.append(relstr)

                            for a in coll:
                                anc = pedigree.get_ancestor_by_number(a[0])
                                c.append(anc.get_primary_ancestor_number())
                                # c.append(a[0])
                            collapse.append(c)

                            ped_count += 1
                            if ped_count>RELATIONSHIP_LIMIT:
                                break

                if collapse:
                    ped[anc_num] = [plink, collapse]
                else:
                    ped[anc_num] = [plink]
            else:
                ped[anc_num] = primary_num

        result['pedigree'] = ped
        return result


    def _handle_notes(self, item):
        """
        Process the notes for the person
        """
        res_list = list()
        note_list = item.get_note_list()
        if note_list:
            for note_handle in note_list:
                note = self.db.get_note_from_handle(note_handle)
                if not note.get_privacy():
                    note_data = {'type': escape(note.get_type().string),
                                 'text': self._format_note_text(note)}
                    res_list.append(note_data)
        return res_list


    def _format_note_text(self, note):
        text = escape(str(note.get_styledtext()))
        lines = text.split("\n")
        return "<br/>\n".join(lines)


    def _get_parents(self, db, person):
        """
        Method that returns the birthparents of a person as tuple
        (mother handle, father handle), if no known birthparent, the
        handle is replaced by None
        """
        fathers = list()
        birth_father = None
        mothers = list()
        birth_mother = None

        for fam_handle in person.get_parent_family_handle_list():
            family = db.get_family_from_handle(fam_handle)
            if not family:
                continue

            dadrel = None
            momrel = None
            for ref in family.get_child_ref_list():
                if ref.ref == person.handle:
                    dadrel = ref.get_father_relation()
                    momrel = ref.get_mother_relation()
                    break


            mother_handle = family.get_mother_handle()
            if mother_handle and momrel:
                if momrel == ChildRefType.BIRTH and not birth_mother:
                    birth_mother = [mother_handle, momrel]
                else:
                    mothers.append([mother_handle, momrel])

            father_handle = family.get_father_handle()
            if father_handle and dadrel:
                if dadrel == ChildRefType.BIRTH and not birth_father:
                    birth_father = [father_handle, dadrel]
                else:
                    fathers.append([father_handle, dadrel])

        if birth_mother:
            mothers.insert(0, birth_mother)
        if birth_father:
            fathers.insert(0, birth_father)
        return (mothers, fathers)

    def _get_spouses(self, person_handle):
        """
        Return list of spouses for given person.
        """
        spouses = list()
        person = self.db.get_person_from_handle(person_handle)
        gender = person.get_gender()

        # Loop through all families
        for family_handle in person.get_family_handle_list():
            family = self.db.get_family_from_handle(family_handle)
            if not family:
                continue

            if gender == Person.MALE:
                spouse_handle = family.get_mother_handle()
            else:
                spouse_handle = family.get_father_handle()

            if spouse_handle:
                spouses.append(spouse_handle)

        return spouses

    @classmethod
    def _get_date(cls, event):
        """
        Get date for event, and convert date modifiers to short form
        """
        dat = get_date(event)
        if not dat:
            return ''
        dat = dat.replace('calculated', 'calc').replace('estimated', 'est')
        return dat.replace('after', 'aft').replace('before', 'bef')

    def add_media(self, mediaref):
        """
        Add image to list
        """
        image = self.db.get_media_from_handle(mediaref.ref)
        mid = image.gramps_id

        if mid not in self.images_list:
            image_path = image.get_path()
            (fname, fext) = os.path.splitext(image_path)
            med = {'mid': image.gramps_id,
                   'ext': fext,
                   'dsc': escape(image.get_description()) }
            dat = self._get_date(image)
            if dat:
                med['dat'] = dat
            rect = mediaref.get_rectangle()
            if rect:
                med['rect'] = rect
            self.images_list[mid] = med

        return self.images_list[mid]
