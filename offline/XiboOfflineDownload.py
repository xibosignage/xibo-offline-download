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
from threading import Thread, Semaphore
import urlparse
import xml.parsers.expat
from SOAPpy import WSDL
import SOAPpy.Types
import SOAPpy.Errors
import socket
import hashlib
import shutil
import Queue

class XiboOfflineDownload(XiboOfflineDownloadUI):

    # Called after the GUI is initialised but before it's shown
    def setup_tasks(self):
        self.SetTitle(APP_NAME)
        self.txtOutput.AppendText('%s v%s\n' % (APP_NAME,VERSION));

        # Define Variables
        self.AddDisplayDialog = None
        self.downloadThread = None

        # Queue for download requests
        self.downloadQueue = Queue.Queue()

        # Figure out where our config is saved
        self.__config_path = os.path.expanduser('~')
        self.__config_file = os.path.join(self.__config_path,'xibo-offline.cfg')

        global log
        log = self.writeLog

        # Read config (if exists)
        global config
        config = ConfigParser.ConfigParser()
        config.readfp(open('defaults.cfg'))

        print _("Reading user configuration")
        config.read([self.__config_file])

        global verbose
        try:
            verbose = config.getboolean('Main','verbose')
        except ValueError:
            config.set('Main','verbose','false')
            self.saveConfig()
            verbose = False

        # Setup the GUI with options from the config file
        if verbose:
            self.chkVerbose.SetValue(True)

        if config.get('Main','xmdsUrl') != '':
            self.txtServerURL.WriteText(config.get('Main','xmdsUrl'))

        if config.get('Main','xmdsKey') != '':
            self.txtServerKey.WriteText(config.get('Main','xmdsKey'))

        # Add displays defined in the config file
        self.updateDisplays()


    def updateDisplays(self):
        # Add displays defined in the config file
        displayNames = []

        for section in config.sections():
            if section != 'Main':
                displayNames.append(section)
        # End For Loop

        # Sort the names alphabetically ignoring case
        displayNames.sort(key=lambda x: x.lower())

        # Clear the list
        self.selectedDisplays.Set(displayNames)

    def writeLog(self,message,appendLineBreak=True,important=False):
        if verbose or important:
            wx.CallAfter(self.txtOutput.AppendText, message)
            if appendLineBreak:
                wx.CallAfter(self.txtOutput.AppendText, '\n')

    def getConfigFile(self):
        return self.__config_file

    def saveConfig(self):
        try:
            fh = open(self.getConfigFile(), 'w+')
            config.write(fh)
            fh.close()
        except IOError:
            log('Unable to write configuration file at %s. Check your filesystem permissions.' % self.__parent.getConfigFile(),True,True)
            return False

        return True

    def finishedDownload(self):
        log('Finished Download',True,True)
        self.btnDownload.Enable()

    # Event Handlers
    def onSelectAll(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # Select all items in the display list
        numItems = self.selectedDisplays.GetCount()
        for i in range(0,numItems):
            self.selectedDisplays.SetSelection(i)
        
        if numItems > 0:
            self.btnRemove.Enable()
            self.btnDownload.Enable()

        event.Skip()

    def onSelectNone(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # Clear all selections in the display list
        numItems = self.selectedDisplays.GetCount()

        for i in range(0,numItems):
            self.selectedDisplays.Deselect(i)

        self.btnRemove.Disable()
        self.btnDownload.Disable()
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
            self.btnDownload.Enable()
        else:
            self.btnRemove.Disable()
            self.btnDownload.Disable()

        event.Skip()

    def onAddDisplay(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        if self.AddDisplayDialog == None:        
            self.AddDisplayDialog = AddDisplay(self,-1)
        self.AddDisplayDialog.Show()
        self.AddDisplayDialog.setParent(self)
        event.Skip()

    def onDeleteDisplay(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # Are you sure
        dlg = wx.MessageDialog(self, _("Are you sure you want to delete the selected displays?"),_("Delete Displays?"),style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION|wx.STAY_ON_TOP)
        if dlg.ShowModal() == wx.ID_YES:
            # Get a list of selected Displays
            selections = self.selectedDisplays.GetSelections()

            for i in selections:
                display = self.selectedDisplays.GetString(i)
                config.remove_section(display)
                log(_('Removed display %s') % display,True,True)

            self.saveConfig()
            self.updateDisplays()
        
        dlg.Destroy()        
        event.Skip()

    def onDownload(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # Disable Download Button
        self.btnDownload.Disable()

        try:
            outdir = config.get('Main','outDir')
        except ConfigParser.NoOptionError:
            outdir=''

        log('Saved Output Directory: %s' % outdir)

        # Display a dialog asking for a folder to write to
        dlg = wx.DirDialog(self,_("Select output USB drive root folder"),outdir)

        if dlg.ShowModal() == wx.ID_OK:
            outdir = dlg.GetPath()
            config.set('Main','outDir',outdir)
            self.saveConfig()
            log('Selected Output Directory: %s' % outdir)

        dlg.Destroy()

        # Get the displays selected:
        displays = []
        selections = self.selectedDisplays.GetSelections()

        for i in selections:
            displays.append(self.selectedDisplays.GetString(i))

        # Displays now contains a list of display names to download content for
        # Create output folders for each display key:

        for display in displays:
            try:
                key = config.get(display,'license')
            except ConfigParser.NoOptionError:
                log(_('No license key for display %s. Please check configuration.') % display,True,True)
                # Remove the display from the list
                del displays[displays.index(display)]
                continue

            try:
                shutil.rmtree(os.path.join(outdir,key))
            except OSError:
                if os.path.isdir(os.path.join(outdir,key)):
                    log(_('Unable to remove old output directory. Check filesystem permissions.'),True,True)
                    continue
                else:
                    # Do nothing - we're golden.
                    pass

            try:
                os.mkdir(os.path.join(outdir,key))
            except IOError:
                log(_('Unable to create output directory. Check filesystem permissions.'),True,True)
                continue

            displayDict = {'name': display, 'key': key, 'outdir': os.path.join(outdir,key)}
            self.downloadQueue.put(displayDict)
            # Finish while loop for displays

        # Push the queue in to a download thread and start it running
        self.downloadThread = XMDSDownloadThread(self,self.downloadQueue)
        self.downloadThread.start()

        event.Skip()

    def onCancel(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        if self.downloadThread != None:
            # TODO: Terminate running thread
            pass
        event.Skip()

    def onConfigSave(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        config.set('Main','xmdsUrl',self.txtServerURL.GetValue())
        config.set('Main','xmdsKey',self.txtServerKey.GetValue())

        if self.chkVerbose.IsChecked():
            config.set('Main','verbose','true')
        else:
            config.set('Main','verbose','false')

        if not self.saveConfig():
            event.Skip()
            return

        log('Configuration saved',True,True)
        self.btnSave.Disable()
        event.Skip()

    def onDisplayListDClick(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        # print "Event handler `onDisplayListDClick' not implemented"
        event.Skip()

    def onDisplayListClick(self, event): # wxGlade: XiboOfflineDownloadUI.<event_handler>
        if len(self.selectedDisplays.GetSelections()) > 0:
            self.btnRemove.Enable()
            self.btnDownload.Enable()
        else:
            self.btnRemove.Disable()
            self.btnDownload.Disable()
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
        # Save the new display to config
        try:
            config.add_section(self.txtClientName.GetValue())
        except ConfigParser.DuplicateSectionError:
            log('A display with that name already exists.',True,True)
            event.Skip()
            return
        except ValueError:
            log('You may not name a display "DEFAULT". Please choose another name.',True,True)
            event.Skip()
            return

        try:
            config.set(self.txtClientName.GetValue(),'license',self.txtClientKey.GetValue())
        except ConfigParser.NoSectionError:
            log('Something went wrong adding the display to your configuration file.',True,True)
            event.Skip()
            return

        if not self.__parent.saveConfig():
            event.Skip()
            return

        # Actually Add the Display
        xmds = XMDS(self.txtClientKey.GetValue(),self.txtClientName.GetValue(),config.get('Main','xmdsKey'))
        try:
            xmds.RegisterDisplay()
        except XMDSException:
            log('Webservice Exception',True,True)
            event.Skip()
            return

        # If all went well, reninitialize the form and close it
        self.txtClientKey.Clear()
        self.txtClientName.Clear()
        self.btnCreateDisplay.Disable()
        self.txtClientKey.WriteText(hashlib.sha1(uuid.uuid4().hex).hexdigest())
        self.__parent.updateDisplays()
        self.Close()
        event.Skip()

    def onGenerateKey(self, event): # wxGlade: AddDisplayUI.<event_handler>
        self.txtClientKey.Clear()
        self.txtClientKey.WriteText(hashlib.sha1(uuid.uuid4().hex).hexdigest())
        event.Skip()

    def onCancel(self, event): # wxGlade: AddDisplayUI.<event_handler>
        self.txtClientKey.Clear()
        self.txtClientName.Clear()
        self.btnCreateDisplay.Disable()
        self.Close()
        event.Skip()

    def onClientNameChange(self, event): # wxGlade: AddDisplayUI.<event_handler>
        if self.validateFields():
            self.btnCreateDisplay.Enable()
        else:
            self.btnCreateDisplay.Disable()
        event.Skip()

    def onClientKeyChange(self, event): # wxGlade: AddDisplayUI.<event_handler>
        if self.validateFields():
            self.btnCreateDisplay.Enable()
        else:
            self.btnCreateDisplay.Disable()
        event.Skip()

    def validateFields(self):
        ret = True

        if len(self.txtClientKey.GetValue()) < 1:
            ret = False

        if len(self.txtClientName.GetValue()) < 1:
            ret = False

        return ret


    def setParent(self,parent):
        self.__parent = parent

class XMDSDownloadThread(Thread):
    def __init__(self,parent,downloadQueue):
        Thread.__init__(self)
        self.__parent = parent
        self.__q = downloadQueue

    def run(self):
        log('Starting Download Thread')
        try:
            while True:
                # While loop will be broken by Queue empty exception
                display = self.__q.get(False)
                key = display['key']
                name = display['name']
                outdir = display['outdir']

                log('Processing display %s' % name)
                print 'Processing display %s' % name
    
                self.downloadSchedule(key,outdir)
                rf = self.downloadRequiredFiles(key,outdir)

                for tmpFile in rf:
                    fileid = tmpFile['fileid']
                    size = tmpFile['size']
                    checksum = tmpFile['checksum']
                    filetype = tmpFile['filetype']

                    log('Processing file %s for display %s' % (fileid,name))
                    print 'Processing file %s for display %s' % (fileid,name)

                    if filetype == 'media':
                        self.downloadMedia()
                    else:
                        self.downloadLayout()

        except Queue.Empty:
            # Queue is empty.
            log('Download Queue is empty')
            print 'Download Queue is empty'

        self.__parent.finishedDownload()

    def downloadSchedule(self,key,outdir):
        # TODO: Implement
        print 'Download Schedule [IN]'
        return

    def downloadRequiredFiles(self,key,outdir):
        # Download RF, save to disk and return a list of dicts of files
        # rf = [{'fileid':1, 'size':49320, 'checksum':'<checksum!>', 'filetype':'media'}]
        # TODO: Implement
        print 'Download Required Files [IN]'
        return []

    def downloadMedia(self):
        return

    def downloadLayout(self):
        return

#### Webservice
class XMDSException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class XMDS:
    def __init__(self,licenseKey,clientName,serverKey):
        self.__schemaVersion__ = "2";

        # Semaphore to allow only one XMDS call to run check simultaneously
        self.checkLock = Semaphore()

        self.hasInitialised = False

        self.uuid = licenseKey
        self.name = clientName
        self.key = serverKey

        self.socketTimeout = None
        try:
            self.socketTimeout = int(config.get('Main','socketTimeout'))
        except:
            self.socketTimeout = 30
        
        try:
            socket.setdefaulttimeout(self.socketTimeout)
            log(_("Set socket timeout to: ") + str(self.socketTimeout))
        except:
            log(_("Unable to set socket timeout. Using system default"))
            pass
            
        # Setup a Proxy for XMDS
        self.xmdsUrl = None
        try:
            self.xmdsUrl = config.get('Main','xmdsUrl')
            if self.xmdsUrl[-1] != "/":
                self.xmdsUrl = self.xmdsUrl + "/"
            self.xmdsUrl = self.xmdsUrl + "xmds.php"
        except ConfigParser.NoOptionError:
            log(_("No XMDS URL specified in your configuration"),True,True)
            log(_("Please check your xmdsUrl configuration option"),True,True)
        except IndexError:
            log(_("Invalid XMDS URL. Check configuration."),True,True)

        # Work out the URL for XMDS and add HTTP URL quoting (ie %xx)
        self.wsdlFile = self.xmdsUrl + '?wsdl'
        
        # Work out the host that XMDS is on so we can get an IP address for ourselves
        tmpParse = urlparse.urlparse(self.xmdsUrl)
        self.xmdsHost = tmpParse.hostname
        del tmpParse
        
    def getUUID(self):
        return str(self.uuid)

    def getName(self):
        return str(self.name)

    def getKey(self):
        return str(self.key)

    def check(self):
        if self.hasInitialised:
            return True
        else:
            self.checkLock.acquire()
            # Check again as we may have been called and blocked by another thread
            # doing this work for us.
            if self.hasInitialised:
                self.checkLock.release()
                return True
            
            self.server = None
            tries = 0
            while self.server == None and tries < 3:
                tries = tries + 1
#                log.log(2,"info",_("Connecting to XMDS at ") + self.xmdsUrl + " " + _("Attempt") + " " + str(tries))
                try:
                    self.server = WSDL.Proxy(self.wsdlFile)
                    self.hasInitialised = True
#                    log.log(2,"info",_("Connected to XMDS via WSDL at %s") % self.wsdlFile)
                except xml.parsers.expat.ExpatError:
#                    log.log(0,"error",_("Could not connect to XMDS."))
                    pass
            # End While
            if self.server == None:
                self.checkLock.release()
                return False

        self.checkLock.release()
        return True

    def RequiredFiles(self):
        """Connect to XMDS and get a list of required files"""
#        log.lights('RF','amber')
        req = None
        if self.check():
#            try:
                # Update the IP Address shown on the infoScreen
#                log.updateIP(self.getIP())
#            except:
#                pass
#            log.updateFreeSpace(self.getDisk())
            try:
                req = self.server.RequiredFiles(self.getKey(),self.getUUID(),self.__schemaVersion__)
            except SOAPpy.Types.faultType, err:
#                log.lights('RF','red')
                raise XMDSException("RequiredFiles: Incorrect arguments passed to XMDS.")
            except SOAPpy.Errors.HTTPError, err:
#                log.lights('RF','red')
#                log.log(0,"error",str(err))
                raise XMDSException("RequiredFiles: HTTP error connecting to XMDS.")
            except socket.error, err:
#                log.lights('RF','red')
#                log.log(0,"error",str(err))
                raise XMDSException("RequiredFiles: socket error connecting to XMDS.")
            except AttributeError, err:
#                log.lights('RF','red')
#                log.log(0,"error",str(err))
                self.hasInitialised = False
                raise XMDSException("RequiredFiles: webservice not initialised")
            except KeyError, err:
#                log.lights('RF', 'red')
#                log.log(0,"error",str(err))
                self.hasInitialised = False
                raise XMDSException("RequiredFiles: Webservice returned non XML content")
        else:
#            log.log(0,"error","XMDS could not be initialised")
#            log.lights('RF','grey')
            raise XMDSException("XMDS could not be initialised")

#        log.lights('RF','green')
        return req
    
    def Schedule(self):
        """Connect to XMDS and get the current schedule"""
#        log.lights('S','amber')
        req = None
        if self.check():
            try:
                try:
                    req = self.server.Schedule(self.getKey(),self.getUUID(),self.__schemaVersion__)
                except SOAPpy.Types.faultType, err:
#                    log.log(0,"error",str(err))
#                    log.lights('S','red')
                    raise XMDSException("Schedule: Incorrect arguments passed to XMDS.")
                except SOAPpy.Errors.HTTPError, err:
#                    log.log(0,"error",str(err))
#                    log.lights('S','red')
                    raise XMDSException("Schedule: HTTP error connecting to XMDS.")
                except socket.error, err:
#                    log.log(0,"error",str(err))
#                    log.lights('S','red')
                    raise XMDSException("Schedule: socket error connecting to XMDS.")
                except AttributeError, err:
#                    log.lights('S','red')
#                    log.log(0,"error",str(err))
                    self.hasInitialised = False
                    raise XMDSException("Schedule: webservice not initialised")
                except KeyError, err:
#                    log.lights('S', 'red')
#                    log.log(0,"error",str(err))
                    self.hasInitialised = False
                    raise XMDSException("Schedule: Webservice returned non XML content")
            except AttributeError, err:
                # For some reason the except SOAPpy.Types line above occasionally throws an
                # exception when the client first starts saying SOAPpy doesn't have a Types attribute
                # Catch that here I guess!
#                log.lights('S','red')
#                log.log(0,"error",str(err))
                self.hasInitiated = False
                raise XMDSException("RequiredFiles: webservice not initalised")
        else:
#            log.log(0,"error","XMDS could not be initialised")
#            log.lights('S','grey')
            raise XMDSException("XMDS could not be initialised")

#        log.lights('S','green')
        return req

    def GetFile(self,tmpPath,tmpType,tmpOffset,tmpChunk):
        """Connect to XMDS and download a file"""
        response = None
#        log.lights('GF','amber')
        if self.check():
            try:
                response = self.server.GetFile(self.getKey(),self.getUUID(),tmpPath,tmpType,tmpOffset,tmpChunk,self.__schemaVersion__)
            except SOAPpy.Types.faultType, err:
#                log.log(0,"error",str(err))
#                log.lights('GF','red')
                raise XMDSException("GetFile: Incorrect arguments passed to XMDS.")
            except SOAPpy.Errors.HTTPError, err:
#                log.log(0,"error",str(err))
#                log.lights('GF','red')
                raise XMDSException("GetFile: HTTP error connecting to XMDS.")
            except socket.error, err:
#                log.log(0,"error",str(err))
#                log.lights('GF','red')
                raise XMDSException("GetFile: socket error connecting to XMDS.")
            except AttributeError, err:
#                log.lights('GF','red')
#                log.log(0,"error",str(err))
                self.hasInitialised = False
                raise XMDSException("GetFile: webservice not initialised")
            except KeyError, err:
#                log.lights('GF', 'red')
#                log.log(0,"error",str(err))
                self.hasInitialised = False
                raise XMDSException("GetFile: Webservice returned non XML content")
        else:
#            log.log(0,"error","XMDS could not be initialised")
#            log.lights('GF','grey')
            raise XMDSException("XMDS could not be initialised")

#        log.lights('GF','green')
        return response

    def RegisterDisplay(self):
        """Connect to XMDS and attempt to register the client"""
        requireXMDS = False
        try:
            if config.get('Main','requireXMDS') == "true":
                requireXMDS = True
        except:
            pass

        if self.check():
            try:
                log(self.server.RegisterDisplay(self.getKey(),self.getUUID(),self.getName(),self.__schemaVersion__),True,True)
#                log.lights('RD','green')
            except SOAPpy.Types.faultType, err:
#                log.lights('RD','red')
#                log.log(0,"error",str(err))
                pass
            except SOAPpy.Errors.HTTPError, err:
#                log.lights('RD','red')
#                log.log(0,"error",str(err))
                pass
            except socket.error, err:
#                log.lights('RD','red')
#                log.log(0,"error",str(err))
                pass
            except AttributeError, err:
#                log.lights('RD','red')
#                log.log(0,"error",str(err))
                self.hasInitialised = False
            except KeyError, err:
#                log.lights('RD', 'red')
#                log.log(0,"error",str(err))
                self.hasInitialised = False

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
