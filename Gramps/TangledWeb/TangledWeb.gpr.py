#
# TangledWeb - Export files to be used in WordPress
#
# Copyright (C) 2021  Hans Boldt
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
"""Export data in JSON format to be used by a content management system."""

register(REPORT,
         id = 'tangled_web',
         name = _('Export to Tangled Web'),
         description = _('Export data to be used by a content management system.'),
         version = '0.0.1',
         gramps_target_version = "5.1",
         status = STABLE,
         fname = "TangledWeb.py",
         authors = ["Hans Boldt"],
         authors_email = ["hans@boldts.net"],
         category = CATEGORY_WEB,
         reportclass = 'TangledWeb',
         optionclass = 'TangledWebOptions',
         report_modes = [REPORT_MODE_GUI],
         )
