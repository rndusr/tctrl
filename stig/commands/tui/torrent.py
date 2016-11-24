# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details
# http://www.gnu.org/licenses/gpl-3.0.txt

"""Torrent commands for the TUI"""

from ...logging import make_logger
log = make_logger(__name__)


from ..base import torrent as base
from . import mixin
from .. import ExpectedResource


class AddTorrentsCmd(base.AddTorrentsCmdbase,
                     mixin.update_torrentlist, mixin.make_request):
    provides = {'tui'}
    tui = ExpectedResource      # Needed by mixin.update_torrentlist
    aioloop = ExpectedResource  # Needed by mixin.update_torrentlist


class ListTorrentsCmd(base.ListTorrentsCmdbase):
    provides = {'tui'}
    tui = ExpectedResource

    def make_tlist(self, filters, sort, columns):
        import urwid
        from ...tui.torrent.tlist import TorrentListWidget
        tlistw = TorrentListWidget(filters=filters, sort=sort, columns=columns)
        titlew = urwid.AttrMap(urwid.Text(tlistw.title), 'tabs', 'tabs.focused')
        self.tui.tabs.load(titlew, tlistw)
        return True


class ListFilesCmd(base.ListFilesCmdbase,
                   mixin.make_request, mixin.make_selection):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_flist(self, filters):
        import urwid
        from ...tui.torrent.flist import FileListWidget
        flistw = FileListWidget(self.srvapi, filters,
                                columns=('name', 'progress', 'size'))
        title = 'Files:%s' % filters
        titlew = urwid.AttrMap(urwid.Text(title), 'tabs', 'tabs.focused')

        self.tui.tabs.load(titlew, flistw)
        return True


class RemoveTorrentsCmd(base.RemoveTorrentsCmdbase,
                        mixin.update_torrentlist, mixin.make_request, mixin.make_selection):
    provides = {'tui'}
    tui = ExpectedResource      # Needed by mixin.update_torrentlist
    aioloop = ExpectedResource  # Needed by mixin.update_torrentlist


class StartTorrentsCmd(base.StartTorrentsCmdbase,
                       mixin.update_torrentlist, mixin.make_request, mixin.make_selection):
    provides = {'tui'}
    tui = ExpectedResource      # Needed by mixin.update_torrentlist
    aioloop = ExpectedResource  # Needed by mixin.update_torrentlist


class StopTorrentsCmd(base.StopTorrentsCmdbase,
                      mixin.update_torrentlist, mixin.make_request, mixin.make_selection):
    provides = {'tui'}
    tui = ExpectedResource      # Needed by mixin.update_torrentlist
    aioloop = ExpectedResource  # Needed by mixin.update_torrentlist


class VerifyTorrentsCmd(base.VerifyTorrentsCmdbase,
                        mixin.make_request, mixin.make_selection):
    provides = {'tui'}
    tui = ExpectedResource      # Needed by mixin.update_torrentlist
