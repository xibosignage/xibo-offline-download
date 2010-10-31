#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Xibo - Digitial Signage - http://www.xibo.org.uk
# Copyright (C) 2010 Alex Harrington
#
# This file is part of Xibo.
#
# Xibo is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version. 
#
# Xibo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Xibo.  If not, see <http://www.gnu.org/licenses/>.

# Static Variables
VERSION = '1.2.1a1'
APP_NAME = 'Xibo Offline Download Client'

# Imports
from XiboOfflineDownloadUI import XiboOfflineDownloadUI
from XiboOfflineDownloadUI import AddDisplayUI
import wx
import os
import ConfigParser
import uuid

class XiboOfflineDownload(XiboOfflineDownloadUI):

    # Called after the GUI is initialised but before it's shown
    def setup_tasks(self):
        self.SetTitle(APP_NAME)
        self.txtOutput.AppendText('%s v%s' % (APP_NAME,VERSION));

        # Define Variables
        self.AddDisplayDialog = None

        # Figure out where our config is saved
        self.__config_path = os.path.expanduser('~')
        self.__config_file = os.path.join(self.__config_path,'xibo-offline.cfg')

        # Read config (if exists)
        global config
        config = ConfigParser.ConfigParser()
        config.readfp(open('defaults.cfg'))

        print _("Reading user configuration")
        config.read([self.__config_file])

        global verbose
        verbose = False
        # Setup the GUI with options from the config file
        if config.get('Main','verbose') == 'true':
            verbose = True
            self.chkVerbose.SetValue(True)

        if config.get('Main','xmdsUrl') != '':
            self.txtServerURL.WriteText(config.get('Main','xmdsUrl'))

        if config.get('Main','xmdsKey') != '':
            self.txtServerKey.WriteText(config.get('Main','xmdsKey'))

        # Add displays defined in the config file
        self.updateDisplays()


    def updateDisplays(self):
        config.readfp(open('defaults.cfg'))

        print _("Reading user configuration")
        config.read([self.__config_file])

        # Add displays defined in the config file
        displayNames = []

        for section in config.sections():
            if section != 'Main':
                displayNames.append(section)
        # End For Loop

        # Sort the names alphabetically
        displayNames.sort()

        # Clear the list
        self.selectedDisplays.Set(displayNames)


    # Event Handlers
    def onSelectAll(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # Select all items in the display list
        numItems = self.selectedDisplays.GetCount()
        for i in range(0,numItems):
            self.selectedDisplays.SetSelection(i)

        self.btnRemove.Enable()
        event.Skip()

    def onSelectNone(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # Clear all selections in the display list
        numItems = self.selectedDisplays.GetCount()

        for i in range(0,numItems):
            self.selectedDisplays.Deselect(i)

        self.btnRemove.Disable()
        event.Skip()

    def onSelectInvert(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # Invert the selections in the display list.
        selected = self.selectedDisplays.GetSelections()
        numItems = self.selectedDisplays.GetCount()

        for i in range(0,numItems):
            if i in selected:
                self.selectedDisplays.Deselect(i)
            else:
                self.selectedDisplays.SetSelection(i)
        
        if len(self.selectedDisplays.GetSelections()) > 0:
            self.btnRemove.Enable()
        else:
            self.btnRemove.Disable()

        event.Skip()

    def onAddDisplay(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        if self.AddDisplayDialog == None:        
            self.AddDisplayDialog = AddDisplay(self,-1)
        self.AddDisplayDialog.Show()
        event.Skip()

    def onDeleteDisplay(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        print "Event handler `onDeleteDisplay' not implemented!"
        event.Skip()

    def onDownload(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        print "Event handler `onDownload' not implemented!"
        event.Skip()

    def onCancel(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        print "Event handler `onCancel' not implemented!"
        event.Skip()

    def onConfigSave(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        print "Event handler `onConfigSave' not implemented!"
        event.Skip()

    def onDisplayListDClick(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # print "Event handler `onDisplayListDClick' not implemented"
        event.Skip()

    def onDisplayListClick(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        if len(self.selectedDisplays.GetSelections()) > 0:
            self.btnRemove.Enable()
        else:
            self.btnRemove.Disable()
        event.Skip()

    def onServerUrlChange(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        self.btnSave.Enable()
        event.Skip()

    def onServerKeyChange(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        self.btnSave.Enable()
        event.Skip()

    def onVerboseChange(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        self.btnSave.Enable()
        event.Skip()

class AddDisplay(AddDisplayUI):
    def onCreateDisplay(self, event): # wxGlade: AddDisplayUI.<event_handler>
        print "Event handler `onCreateDisplay' not implemented!"
        event.Skip()

    def onGenerateKey(self, event): # wxGlade: AddDisplayUI.<event_handler>
        self.txtClientKey.Clear()
        self.txtClientKey.WriteText(uuid.uuid4().hex)
        event.Skip()

    def onCancel(self, event): # wxGlade: AddDisplayUI.<event_handler>
        self.Close()
        event.Skip()

if __name__ == "__main__":
    import gettext
    gettext.install("app")

    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    frmMain = XiboOfflineDownload(None, -1, "")
    app.SetTopWindow(frmMain)
    frmMain.Show()
    frmMain.setup_tasks()
    app.MainLoop()
