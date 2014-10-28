#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# EditWindows.py
#   Last modified: 2014-10-23 (also update ProgVersion below)
#
# xxx program for Biblelator Bible display/editing
#
# Copyright (C) 2013-2014 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
xxx to allow editing of USFM Bibles using Python3 and Tkinter.
"""

ShortProgName = "EditWindows"
ProgName = "Biblelator Edit Windows"
ProgVersion = "0.19"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = True


import sys, os.path, configparser, logging
from gettext import gettext as _
import multiprocessing

import tkinter as tk
from tkinter.messagebox import showerror, showinfo
from tkinter.simpledialog import askstring, askinteger
from tkinter.filedialog import asksaveasfilename
from tkinter.colorchooser import askcolor
from tkinter.ttk import Style, Frame

# Biblelator imports
from BiblelatorGlobals import APP_NAME, START, EDIT_MODE_NORMAL, EDIT_MODE_USFM
from ResourceWindows import ResourceWindow
from BibleResourceWindows import BibleResourceWindow

# BibleOrgSys imports
sourceFolder = "../BibleOrgSys/"
sys.path.append( sourceFolder )
import BibleOrgSysGlobals
from VerseReferences import SimpleVerseKey



def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )



class CustomText( tk.Text ):
    """
    A custom Text widget which calls a user function whenever the text changes.

    Adapted from http://stackoverflow.com/questions/13835207/binding-to-cursor-movement-doesnt-change-insert-mark
    """
    def __init__( self, *args, **kwargs ):
        if BibleOrgSysGlobals.debugFlag: print( t("CustomText.__init__( ... )") )
        tk.Text.__init__( self, *args, **kwargs ) # initialise the base class

        # All widget changes happen via an internal Tcl command with the same name as the widget:
        #       all inserts, deletes, cursor changes, etc
        #
        # The beauty of Tcl is that we can replace that command with our own command.
        # The following code does just that: replace the code with a proxy that calls the
        # original command and then calls a callback. We can then do whatever we want in the callback.
        private_callback = self.register( self._callback )
        self.tk.eval( """
            proc widget_proxy {actual_widget callback args} {

                # this prevents recursion if the widget is called
                # during the callback
                set flag ::dont_recurse(actual_widget)

                # call the real tk widget with the real args
                set result [uplevel [linsert $args 0 $actual_widget]]

                # call the callback and ignore errors, but only
                # do so on inserts, deletes, and changes in the
                # mark. Otherwise we'll call the callback way too often.
                if {! [info exists $flag]} {
                    if {([lindex $args 0] in {insert replace delete}) ||
                        ([lrange $args 0 2] == {mark set insert})} {
                        # the flag makes sure that whatever happens in the
                        # callback doesn't cause the callbacks to be called again.
                        set $flag 1
                        catch {$callback $result {*}$args } callback_result
                        unset -nocomplain $flag
                    }
                }

                # return the result from the real widget command
                return $result
            }
            """ )
        self.tk.eval( """
                rename {widget} _{widget}
                interp alias {{}} ::{widget} {{}} widget_proxy _{widget} {callback}
            """.format( widget=str(self), callback=private_callback ) )
    # end of CustomText.__init__


    def _callback( self, result, *args ):
        """
        This little function does the actual call of the user routine
            to handle when the CustomText changes.
        """
        self.callback( result, *args )
    # end of CustomText._callback


    def setTextChangeCallback( self, callable ):
        """
        Just a little function to remember the routine to call
            when the CustomText changes.
        """
        self.callback = callable
    # end of CustomText.setTextChangeCallback
# end of CustomText class



class TextEditWindow( ResourceWindow ):
    def __init__( self, parentApp, folderPath=None, filename=None ):
        if BibleOrgSysGlobals.debugFlag: print( t("TextEditWindow.__init__( {}, {}, {} )").format( parentApp, folderPath, filename ) )
        self.parentApp, self.folderPath, self.filename = parentApp, folderPath, filename

        # Set some dummy values required soon (esp. by refreshTitle)
        self.editMode = 'Default'
        ResourceWindow.__init__( self, self.parentApp, 'TextEditor' )
        self.moduleID = None
        self.winType = 'PlainTextEditWindow'
        self.protocol( "WM_DELETE_WINDOW", self.onCloseEditor ) # Catch when window is closed

        self.textBox['background'] = "white"
        self.textBox['selectbackground'] = "red"
        self.textBox['highlightbackground'] = "orange"
        self.textBox['inactiveselectbackground'] = "green"

        self.textBox['wrap'] = 'word'
        self.textBox.config( undo=True, autoseparators=True )
        self.textBox.pack( expand=tk.YES, fill=tk.BOTH )
        self.createEditorKeyboardBindings()

        self.clearText()
        self.after( 500, self.refreshTitle )
    # end of TextEditWindow.__init__


    def createEditorKeyboardBindings( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.createEditorKeyboardBindings()") )
        for name,command in ( ('Paste',self.doPaste), ('Cut',self.doCut),
                             ('Undo',self.doUndo), ('Redo',self.doRedo),
                             ('Save',self.doSave), ):
            if name in self.parentApp.keyBindingDict:
                for keycode in self.parentApp.keyBindingDict[name][1:]:
                    #print( "Bind {} for {}".format( repr(keycode), repr(name) ) )
                    self.textBox.bind( keycode, command )
                self.myKeyboardBindings.append( (name,self.parentApp.keyBindingDict[name][0],) )
            else: logging.critical( 'No key binding available for {}'.format( repr(name) ) )
        #self.textBox.bind('<Control-v>', self.doPaste ); self.textBox.bind('<Control-V>', self.doPaste )
        #self.textBox.bind('<Control-s>', self.doSave ); self.textBox.bind('<Control-S>', self.doSave )
        #self.textBox.bind('<Control-x>', self.doCut ); self.textBox.bind('<Control-X>', self.doCut )
        #self.textBox.bind('<Control-g>', self.doRefind ); self.textBox.bind('<Control-G>', self.doRefind )
    # end of ResourceWindow.createEditorKeyboardBindings()


    def createMenuBar( self ):
        self.menubar = tk.Menu( self )
        #self['menu'] = self.menubar
        self.config( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label='File', underline=0 )
        fileMenu.add_command( label='Save', underline=0, command=self.doSave, accelerator=self.parentApp.keyBindingDict['Save'][0] )
        fileMenu.add_command( label='Save as...', underline=5, command=self.doSaveAs )
        #fileMenu.add_separator()
        #subfileMenuImport = tk.Menu( fileMenu )
        #subfileMenuImport.add_command( label='USX', underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label='Import', underline=0, menu=subfileMenuImport )
        #subfileMenuExport = tk.Menu( fileMenu )
        #subfileMenuExport.add_command( label='USX', underline=0, command=self.notWrittenYet )
        #subfileMenuExport.add_command( label='HTML', underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label='Export', underline=0, menu=subfileMenuExport )
        fileMenu.add_separator()
        fileMenu.add_command( label='Info...', underline=0, command=self.doShowInfo, accelerator=self.parentApp.keyBindingDict['Info'][0] )
        fileMenu.add_separator()
        fileMenu.add_command( label='Close', underline=0, command=self.doCloseEditor, accelerator=self.parentApp.keyBindingDict['Close'][0] )

        editMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=editMenu, label='Edit', underline=0 )
        editMenu.add_command( label='Undo', underline=0, command=self.doUndo, accelerator=self.parentApp.keyBindingDict['Undo'][0] )
        editMenu.add_command( label='Redo', underline=0, command=self.doRedo, accelerator=self.parentApp.keyBindingDict['Redo'][0] )
        editMenu.add_separator()
        editMenu.add_command( label='Cut', underline=2, command=self.doCut, accelerator=self.parentApp.keyBindingDict['Cut'][0] )
        editMenu.add_command( label='Copy', underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict['Copy'][0] )
        editMenu.add_command( label='Paste', underline=0, command=self.doPaste, accelerator=self.parentApp.keyBindingDict['Paste'][0] )
        editMenu.add_separator()
        editMenu.add_command( label='Delete', underline=0, command=self.doDelete )
        editMenu.add_command( label='Select all', underline=0, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict['SelectAll'][0] )

        searchMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=searchMenu, label='Search', underline=0 )
        searchMenu.add_command( label='Goto line...', underline=0, command=self.doGotoLine, accelerator=self.parentApp.keyBindingDict['Line'][0] )
        searchMenu.add_separator()
        searchMenu.add_command( label='Find...', underline=0, command=self.doFind, accelerator=self.parentApp.keyBindingDict['Find'][0] )
        searchMenu.add_command( label='Find again', underline=5, command=self.doRefind, accelerator=self.parentApp.keyBindingDict['Refind'][0] )
        searchMenu.add_command( label='Replace...', underline=0, command=self.doFindReplace )
        #searchMenu.add_separator()
        #searchMenu.add_command( label='Grep...', underline=0, command=self.onGrep )

##        gotoMenu = tk.Menu( self.menubar )
##        self.menubar.add_cascade( menu=gotoMenu, label='Goto', underline=0 )
##        gotoMenu.add_command( label='Previous book', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label='Next book', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label='Previous chapter', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label='Next chapter', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label='Previous verse', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label='Next verse', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_separator()
##        gotoMenu.add_command( label='Forward', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label='Backward', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_separator()
##        gotoMenu.add_command( label='Previous list item', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_command( label='Next list item', underline=0, command=self.notWrittenYet )
##        gotoMenu.add_separator()
##        gotoMenu.add_command( label='Book', underline=0, command=self.notWrittenYet )

##        viewMenu = tk.Menu( self.menubar )
##        self.menubar.add_cascade( menu=viewMenu, label='View', underline=0 )
##        viewMenu.add_command( label='Whole chapter', underline=6, command=self.notWrittenYet )
##        viewMenu.add_command( label='Whole book', underline=6, command=self.notWrittenYet )
##        viewMenu.add_command( label='Single verse', underline=7, command=self.notWrittenYet )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label='Tools', underline=0 )
        toolsMenu.add_command( label='Options...', underline=0, command=self.notWrittenYet )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label='Window', underline=0 )
        windowMenu.add_command( label='Bring in', underline=0, command=self.notWrittenYet )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, label='Help', underline=0 )
        helpMenu.add_command( label='Help...', underline=0, command=self.doHelp, accelerator=self.parentApp.keyBindingDict['Help'][0] )
        helpMenu.add_separator()
        helpMenu.add_command( label='About...', underline=0, command=self.doAbout, accelerator=self.parentApp.keyBindingDict['About'][0] )
    # end of TextEditWindow.createMenuBar


    def createContextMenu( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.createContextMenu()") )
        self.contextMenu = tk.Menu( self, tearoff=0 )
        self.contextMenu.add_command( label="Cut", underline=2, command=self.doCut, accelerator=self.parentApp.keyBindingDict['Cut'][0] )
        self.contextMenu.add_command( label="Copy", underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict['Copy'][0] )
        self.contextMenu.add_command( label="Paste", underline=0, command=self.doPaste, accelerator=self.parentApp.keyBindingDict['Paste'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Select all", underline=7, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict['SelectAll'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Close", underline=1, command=self.doCloseEditor, accelerator=self.parentApp.keyBindingDict['Close'][0] )

        self.bind( "<Button-3>", self.showContextMenu ) # right-click
    # end of TextEditWindow.createContextMenu


    #def showContextMenu( self, e):
        #self.contextMenu.post( e.x_root, e.y_root )
    ## end of TextEditWindow.showContextMenu


    #def createToolBar( self ):
        #toolbar = Frame( self, cursor='hand2', relief=tk.SUNKEN ) # bd=2
        #toolbar.pack( side=tk.BOTTOM, fill=tk.X )
        #Button( toolbar, text='Halt',  command=self.quit ).pack( side=tk.RIGHT )
        #Button( toolbar, text='Hide Resources', command=self.hideResources ).pack(side=tk.LEFT )
        #Button( toolbar, text='Hide All', command=self.hideAll ).pack( side=tk.LEFT )
        #Button( toolbar, text='Show All', command=self.showAll ).pack( side=tk.LEFT )
        #Button( toolbar, text='Bring All', command=self.bringAll ).pack( side=tk.LEFT )
    ## end of TextEditWindow.createToolBar


    def refreshTitle( self ):
        self.title( "{}[{}] {} ({}) Editable".format( '*' if self.modified() else '',
                                            _("Text"), self.filename, self.folderPath ) )
        self.after( 200, self.refreshTitle )
    # end if TextEditWindow.refreshTitle


    def doHelp( self, event=None ):
        from Help import HelpBox
        hb = HelpBox( self.parentApp, ProgName, ProgNameVersion )
    # end of TextEditWindow.doHelp


    def doAbout( self, event=None ):
        from About import AboutBox
        ab = AboutBox( self.parentApp, ProgName, ProgNameVersion )
    # end of TextEditWindow.doAbout


    def doUndo( self, event=None ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doUndo()") )
        try: self.textBox.edit_undo()
        except tk.TclError:
            showinfo( APP_NAME, 'Nothing to undo')
    # end of TextEditWindow.doUndo


    def doRedo( self, event=None ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doRedo()") )
        try: self.textBox.edit_redo()
        except tk.TclError:
            showinfo( APP_NAME, 'Nothing to redo')
    # end of TextEditWindow.doRedo


    def xxxdoCopy( self ):                           # get text selected by mouse, etc.
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doCopy()") )
        if not self.textBox.tag_ranges( tk.SEL ):       # save in cross-app clipboard
            showerror( APP_NAME, 'No text selected')
        else:
            text = self.textBox.get( tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(text)
    # end of TextEditWindow.doCopy


    def doDelete( self, event=None ):                         # delete selected text, no save
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doDelete()") )
        if not self.textBox.tag_ranges( tk.SEL ):
            showerror( APP_NAME, 'No text selected')
        else:
            self.textBox.delete( tk.SEL_FIRST, tk.SEL_LAST)
    # end of TextEditWindow.doDelete


    def doCut( self, event=None ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doCut()") )
        if not self.textBox.tag_ranges( tk.SEL ):
            showerror( APP_NAME, 'No text selected')
        else:
            self.doCopy()                       # save and delete selected text
            self.doDelete()
    # end of TextEditWindow.doCut


    def doPaste( self, event=None ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doPaste()") )
        try:
            text = self.selection_get( selection='CLIPBOARD')
        except tk.TclError:
            showerror( APP_NAME, 'Nothing to paste')
            return
        self.textBox.insert( tk.INSERT, text)          # add at current insert cursor
        self.textBox.tag_remove( tk.SEL, START, tk.END)
        self.textBox.tag_add( tk.SEL, tk.INSERT+'-%dc' % len(text), tk.INSERT)
        self.textBox.see( tk.INSERT )                   # select it, so it can be cut
    # end of TextEditWindow.doPaste


    def xxxdoSelectAll( self ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doSelectAll()") )
        self.textBox.tag_add( tk.SEL, START, tk.END+'-1c' )   # select entire text
        self.textBox.mark_set( tk.INSERT, START )          # move insert point to top
        self.textBox.see( tk.INSERT )                      # scroll to top
    # end of TextEditWindow.doSelectAll


    ############################################################################
    # Search menu commands
    ############################################################################

    def xxxdoGotoLine( self, forceline=None):
        line = forceline or askinteger( APP_NAME, 'Enter line number' )
        self.textBox.update()
        self.textBox.focus()
        if line is not None:
            maxindex = self.textBox.index( tk.END+'-1c' )
            maxline  = int( maxindex.split('.')[0] )
            if line > 0 and line <= maxline:
                self.textBox.mark_set( tk.INSERT, '{}.0'.format(line) ) # goto line
                self.textBox.tag_remove( tk.SEL, START, tk.END )          # delete selects
                self.textBox.tag_add( tk.SEL, tk.INSERT, 'insert + 1l' )  # select line
                self.textBox.see( tk.INSERT )                          # scroll to line
            else:
                showerror( APP_NAME, 'No such line number' )
    # end of TextEditWindow.doGotoLine


    def xxxdoFind( self, lastkey=None):
        key = lastkey or askstring( APP_NAME, 'Enter search string' )
        self.textBox.update()
        self.textBox.focus()
        self.lastfind = key
        if key:
            nocase = self.optionsDict['caseinsens']
            where = self.textBox.search( key, tk.INSERT, tk.END, nocase=nocase )
            if not where:                                          # don't wrap
                showerror( APP_NAME, 'String not found' )
            else:
                pastkey = where + '+%dc' % len(key)           # index past key
                self.textBox.tag_remove( tk.SEL, START, tk.END )         # remove any sel
                self.textBox.tag_add( tk.SEL, where, pastkey )        # select key
                self.textBox.mark_set( tk.INSERT, pastkey )           # for next find
                self.textBox.see( where )                          # scroll display
    # end of TextEditWindow.doFind


    def xxxdoRefind( self ):
        self.doFind( self.lastfind)
    # end of TextEditWindow.doRefind


    def doFindReplace( self ):
        """
        non-modal find/change dialog
        2.1: pass per-dialog inputs to callbacks, may be > 1 change dialog open
        """
        new = Toplevel( self )
        new.title( 'PyEdit - change')
        Label(new, text='Find text?', relief=RIDGE, width=15).grid(row=0, column=0)
        Label(new, text='Change to?', relief=RIDGE, width=15).grid(row=1, column=0)
        entry1 = Entry(new)
        entry2 = Entry(new)
        entry1.grid(row=0, column=1, sticky=EW)
        entry2.grid(row=1, column=1, sticky=EW)

        def doFind():                         # use my entry in enclosing scope
            self.doFind( entry1.get() )         # runs normal find dialog callback

        def onApply():
            self.onDoChange( entry1.get(), entry2.get() )

        Button( new, text='Find',  command=doFind ).grid(row=0, column=2, sticky=EW)
        Button( new, text='Apply', command=onApply).grid(row=1, column=2, sticky=EW)
        new.columnconfigure(1, weight=1)      # expandable entries
    # end of TextEditWindow.doFindReplace


    def onDoChange( self, findtext, changeto):
        # on Apply in change dialog: change and refind
        if self.textBox.tag_ranges( tk.SEL ):                      # must find first
            self.textBox.delete( tk.SEL_FIRST, tk.SEL_LAST)
            self.textBox.insert( tk.INSERT, changeto)             # deletes if empty
            self.textBox.see( tk.INSERT )
            self.doFind( findtext )                          # goto next appear
            self.textBox.update()                             # force refresh
    # end of TextEditWindow.onDoChange


    def xxxdoShowInfo( self, event=None ):
        """
        pop-up dialog giving text statistics and cursor location;
        caveat (2.1): Tk insert position column counts a tab as one
        character: translate to next multiple of 8 to match visual?
        """
        text  = self.getAllText()
        bytes = len( text )             # words uses a simple guess:
        lines = len( text.split('\n') ) # any separated by whitespace
        words = len( text.split() )     # 3.x: bytes is really chars
        index = self.textBox.index( tk.INSERT ) # str is unicode code points
        where = tuple( index.split('.') )
        showinfo( APP_NAME+' Information',
                 'Current location:\n\n' +
                 'line:\t%s\ncolumn:\t%s\n\n' % where +
                 'File text statistics:\n\n' +
                 'chars:\t{}\nlines:\t{}\nwords:\t{}\n'.format( bytes, lines, words) )
    # end of TextEditWindow.doShowInfo


    ############################################################################
    # Utilities, useful outside this class
    ############################################################################

    def xxxisEmpty( self ):
        return not self.getAllText()
    # end of TextEditWindow.modified

    def xxxxmodified( self ):
        return self.textBox.edit_modified()
    # end of TextEditWindow.modified

    def xxxgetAllText( self ):
        """ Returns all the text as a string. """
        return self.textBox.get( START, tk.END+'-1c' )
    # end of TextEditWindow.modified

    def xxxsetAllText( self, newText ):
        """
        caller: call self.update() first if just packed, else the
        initial position may be at line 2, not line 1 (2.1; Tk bug?)
        """
        self.textBox.delete( START, tk.END )
        self.textBox.insert( tk.END, newText )
        self.textBox.mark_set( tk.INSERT, START ) # move insert point to top
        self.textBox.see( tk.INSERT ) # scroll to top, insert is set

        self.textBox.edit_reset() # clear undo/redo stks
        self.textBox.edit_modified( tk.FALSE ) # clear modified flag
    # end of TextEditWindow.setAllText


    def setFilepath( self, newFilepath ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.setFilepath( {} )").format( repr(newFilepath) ) )
        self.folderPath, self.filename = os.path.split( newFilepath )
        #self.currfile = name  # for save
        #self.filelabel.config(text=str(name))
        self.refreshTitle()
    # end of TextEditWindow.setFilepath


    def doSaveAs( self, event=None ):
        """
        Called if the user requests a close from the GUI.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doSaveAs()") )
        if self.modified():
            saveAsFilepath = asksaveasfilename()
            #print( "saveAsFilepath", repr(saveAsFilepath) )
            if saveAsFilepath:
                self.setFilepath( saveAsFilepath )
                self.doSave()
    # end of TextEditWindow.doSaveAs

    def doSave( self, event=None ):
        """
        Called if the user requests a close from the GUI.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doSaveAs()") )
        if self.modified():
            if self.folderPath and self.filename:
                filepath = os.path.join( self.folderPath, self.filename )
                allText = self.getAllText()
                with open( filepath, mode='wt' ) as theFile:
                    theFile.write( allText )
                self.textBox.edit_modified( tk.FALSE ) # clear modified flag
                self.refreshTitle()
            else: self.doSaveAs()
    # end of TextEditWindow.doSaveAs


    def doCloseEditor( self, event=None ):
        """
        Called if the user requests a close from the GUI.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.doCloseEditor()") )
        self.onCloseEditor()
    # end of TextEditWindow.closeEditor

    def onCloseEditor( self ):
        """
        Called if the window is about to be destroyed.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("TextEditWindow.onCloseEditor()") )
        if self.modified():
            if self.folderPath and self.filename:
                self.doSave()
                self.closeResourceWindow()
            else: # we need to ask where to save it
                self.doSaveAs()
                if self.folderPath and self.filename: # assume we saved it
                    self.closeResourceWindow()
        else: self.closeResourceWindow()
    # end of TextEditWindow.onCloseEditor
# end of TextEditWindow class



class USFMEditWindow( TextEditWindow, BibleResourceWindow ):
    def __init__( self, parentApp, USFMBible ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "USFMEditWindow.__init__( {}, {} )".format( parentApp, USFMBible ) )
        self.parentApp, self.internalBible = parentApp, USFMBible
        self.USFMFolder = self.internalBible.sourceFolder

        # Set some dummy values required soon (esp. by refreshTitle)
        self.editMode = 'Default'
        BibleResourceWindow.__init__( self, parentApp, 'BibleEditor' )
        TextEditWindow.__init__( self, parentApp )

        # Make our own textBox
        self.textBox.destroy()
        self.textBox = CustomText( self, yscrollcommand=self.vScrollbar.set, wrap='word' )
        self.textBox.setTextChangeCallback( self.onTextChange )
        self.textBox.pack( expand=tk.YES, fill=tk.BOTH )
        self.vScrollbar.config( command=self.textBox.yview ) # link the scrollbar to the text box
        self.doStandardKeyboardBindings()
        self.createEditorKeyboardBindings()

        # Now we need to override a few critical variables
        self.genericWindowType = 'BibleEditor'
        self.winType = 'USFMBibleEditWindow'

        if self.internalBible is not None:
            self.textBox['background'] = 'white'
            self.textBox['selectbackground'] = 'red'
            self.textBox['highlightbackground'] = 'orange'
            self.textBox['inactiveselectbackground'] = 'green'
        else: self.editMode = None

        #self.textBox.bind( '<1>', self.onTextChange )
        self.lastBBB = None
    # end of USFMEditWindow.__init__


    def refreshTitle( self ):
        self.title( "{}[{}] {} {} {}:{} ({}) Editable {}".format( '*' if self.modified() else '',
                                    self.groupCode,
                                    self.internalBible.name if self.internalBible is not None else 'None',
                                    self.verseKey.getBBB(), self.verseKey.getChapterNumber(), self.verseKey.getVerseNumber(),
                                    self.editMode, self.contextViewMode ) )
    # end if USFMEditWindow.refreshTitle


    def xxdoHelp( self ):
        from Help import HelpBox
        hb = HelpBox( self.parentApp, ProgName, ProgNameVersion )
    # end of USFMEditWindow.doHelp


    def xxdoAbout( self ):
        from About import AboutBox
        ab = AboutBox( self.parentApp, ProgName, ProgNameVersion )
    # end of USFMEditWindow.doAbout


    def createMenuBar( self ):
        self.menubar = tk.Menu( self )
        #self['menu'] = self.menubar
        self.config( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label='File', underline=0 )
        fileMenu.add_command( label='Save', underline=0, command=self.notWrittenYet )
        fileMenu.add_command( label='Save as...', underline=5, command=self.notWrittenYet )
        #fileMenu.add_separator()
        #subfileMenuImport = tk.Menu( fileMenu )
        #subfileMenuImport.add_command( label='USX', underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label='Import', underline=0, menu=subfileMenuImport )
        #subfileMenuExport = tk.Menu( fileMenu )
        #subfileMenuExport.add_command( label='USX', underline=0, command=self.notWrittenYet )
        #subfileMenuExport.add_command( label='HTML', underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label='Export', underline=0, menu=subfileMenuExport )
        fileMenu.add_separator()
        fileMenu.add_command( label='Info...', underline=0, command=self.doShowInfo )
        fileMenu.add_separator()
        fileMenu.add_command( label='Close', underline=0, command=self.doCloseEditor )

        editMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=editMenu, label='Edit', underline=0 )
        editMenu.add_command( label='Undo', underline=0, command=self.doUndo )
        editMenu.add_command( label='Redo', underline=0, command=self.doRedo )
        editMenu.add_separator()
        editMenu.add_command( label='Cut', underline=2, command=self.doCut )
        editMenu.add_command( label='Copy', underline=0, command=self.doCopy )
        editMenu.add_command( label='Paste', underline=0, command=self.doPaste )
        editMenu.add_separator()
        editMenu.add_command( label='Delete', underline=0, command=self.doDelete )
        editMenu.add_command( label='Select all', underline=0, command=self.doSelectAll )

        searchMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=searchMenu, label='Search', underline=0 )
        searchMenu.add_command( label='Goto line...', underline=0, command=self.doGotoLine )
        searchMenu.add_separator()
        searchMenu.add_command( label='Find...', underline=0, command=self.doFind )
        searchMenu.add_command( label='Find again', underline=5, command=self.doRefind )
        searchMenu.add_command( label='Replace...', underline=0, command=self.doFindReplace )

        gotoMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=gotoMenu, label='Goto', underline=0 )
        gotoMenu.add_command( label='Previous book', underline=0, command=self.notWrittenYet )
        gotoMenu.add_command( label='Next book', underline=0, command=self.notWrittenYet )
        gotoMenu.add_command( label='Previous chapter', underline=0, command=self.notWrittenYet )
        gotoMenu.add_command( label='Next chapter', underline=0, command=self.notWrittenYet )
        gotoMenu.add_command( label='Previous verse', underline=0, command=self.notWrittenYet )
        gotoMenu.add_command( label='Next verse', underline=0, command=self.notWrittenYet )
        gotoMenu.add_separator()
        gotoMenu.add_command( label='Forward', underline=0, command=self.notWrittenYet )
        gotoMenu.add_command( label='Backward', underline=0, command=self.notWrittenYet )
        gotoMenu.add_separator()
        gotoMenu.add_command( label='Previous list item', underline=0, command=self.notWrittenYet )
        gotoMenu.add_command( label='Next list item', underline=0, command=self.notWrittenYet )
        gotoMenu.add_separator()
        gotoMenu.add_command( label='Book', underline=0, command=self.notWrittenYet )
        gotoMenu.add_separator()
        self._groupRadio.set( self.groupCode )
        gotoMenu.add_radiobutton( label='Group A', underline=6, value='A', variable=self._groupRadio, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label='Group B', underline=6, value='B', variable=self._groupRadio, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label='Group C', underline=6, value='C', variable=self._groupRadio, command=self.changeBibleGroupCode )
        gotoMenu.add_radiobutton( label='Group D', underline=6, value='D', variable=self._groupRadio, command=self.changeBibleGroupCode )

        viewMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=viewMenu, label='View', underline=0 )
        if   self.contextViewMode == 'BeforeAndAfter': self._viewRadio.set( 1 )
        elif self.contextViewMode == 'ByVerse': self._viewRadio.set( 2 )
        elif self.contextViewMode == 'ByBook': self._viewRadio.set( 3 )
        elif self.contextViewMode == 'ByChapter': self._viewRadio.set( 4 )

        viewMenu.add_radiobutton( label='Before and after...', underline=7, value=1, variable=self._viewRadio, command=self.changeBibleContextView )
        viewMenu.add_radiobutton( label='Single verse', underline=7, value=2, variable=self._viewRadio, command=self.changeBibleContextView )
        viewMenu.add_radiobutton( label='Whole book', underline=6, value=3, variable=self._viewRadio, command=self.changeBibleContextView )
        viewMenu.add_radiobutton( label='Whole chapter', underline=6, value=4, variable=self._viewRadio, command=self.changeBibleContextView )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label='Tools', underline=0 )
        toolsMenu.add_command( label='Options...', underline=0, command=self.notWrittenYet )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label='Window', underline=0 )
        windowMenu.add_command( label='Bring in', underline=0, command=self.notWrittenYet )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, label='Help', underline=0 )
        helpMenu.add_command( label='Help...', underline=0, command=self.doHelp )
        helpMenu.add_separator()
        helpMenu.add_command( label='About...', underline=0, command=self.doAbout )
    # end of USFMEditWindow.createMenuBar


    def xxcreateContextMenu( self ):
        """
        """
        self.contextMenu = tk.Menu( self, tearoff=0 )
        self.contextMenu.add_command( label="Cut", underline=2, command=self.doCut )
        self.contextMenu.add_command( label="Copy", underline=0, command=self.doCopy )
        self.contextMenu.add_command( label="Paste", underline=0, command=self.doPaste )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Close", underline=1, command=self.doCloseEditor )

        self.bind( "<Button-3>", self.showContextMenu ) # right-click
        #self.pack()
    # end of USFMEditWindow.createContextMenu


    #def showContextMenu( self, e):
        #self.contextMenu.post( e.x_root, e.y_root )
    ## end of USFMEditWindow.showContextMenu


    #def createToolBar( self ):
        #toolbar = Frame( self, cursor='hand2', relief=tk.SUNKEN ) # bd=2
        #toolbar.pack( side=tk.BOTTOM, fill=tk.X )
        #Button( toolbar, text='Halt',  command=self.quit ).pack( side=tk.RIGHT )
        #Button( toolbar, text='Hide Resources', command=self.hideResources ).pack(side=tk.LEFT )
        #Button( toolbar, text='Hide All', command=self.hideAll ).pack( side=tk.LEFT )
        #Button( toolbar, text='Show All', command=self.showAll ).pack( side=tk.LEFT )
        #Button( toolbar, text='Bring All', command=self.bringAll ).pack( side=tk.LEFT )
    ## end of USFMEditWindow.createToolBar


    def onTextChange( self, result, *args ):
        """
        Called whenever the text box cursor changes either with a mouse click or arrow keys.

        Checks to see if they have moved to a new chapter/verse,
            and if so, informs the parent app.
        """
        if self.loading: return # So we don't get called a million times for nothing
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("USFMEditWindow.onTextChange( {}, {} )").format( repr(result), args ) )

        if 0: # Get line and column info
            lineColumn = self.textBox.index( tk.INSERT )
            print( "lc", repr(lineColumn) )
            line, column = lineColumn.split( '.', 1 )
            print( "l,c", repr(line), repr(column) )

        if 0: # get formatting tag info
            tagNames = self.textBox.tag_names( tk.INSERT )
            tagNames2 = self.textBox.tag_names( lineColumn )
            tagNames3 = self.textBox.tag_names( tk.INSERT + ' linestart' )
            tagNames4 = self.textBox.tag_names( lineColumn + ' linestart' )
            tagNames5 = self.textBox.tag_names( tk.INSERT + ' linestart+1c' )
            tagNames6 = self.textBox.tag_names( lineColumn + ' linestart+1c' )
            print( "tN", tagNames )
            if tagNames2!=tagNames or tagNames3!=tagNames or tagNames4!=tagNames or tagNames5!=tagNames or tagNames6!=tagNames:
                print( "tN2", tagNames2 )
                print( "tN3", tagNames3 )
                print( "tN4", tagNames4 )
                print( "tN5", tagNames5 )
                print( "tN6", tagNames6 )
                halt

        if 0: # show various mark strategies
            mark1 = self.textBox.mark_previous( tk.INSERT )
            mark2 = self.textBox.mark_previous( lineColumn )
            mark3 = self.textBox.mark_previous( tk.INSERT + ' linestart' )
            mark4 = self.textBox.mark_previous( lineColumn + ' linestart' )
            mark5 = self.textBox.mark_previous( tk.INSERT + ' linestart+1c' )
            mark6 = self.textBox.mark_previous( lineColumn + ' linestart+1c' )
            print( "mark1", mark1 )
            if mark2!=mark1:
                print( "mark2", mark1 )
            if mark3!=mark1 or mark4!=mark1 or mark5!=mark1 or mark6!=mark1:
                print( "mark3", mark3 )
                if mark4!=mark3:
                    print( "mark4", mark4 )
                print( "mark5", mark5 )
                if mark6!=mark5:
                    print( "mark6", mark6 )

        # Try to determine the CV mark
        # It seems that we have to try various strategies because
        #       sometimes we get a 'current' mark and sometimes an 'anchor1'
        gotCV = False
        # Try to put the most useful methods first (for efficiency)
        for j, mark in enumerate( (self.textBox.mark_previous(tk.INSERT), self.textBox.mark_previous(tk.INSERT+'-1c'),
                                   self.textBox.mark_previous(tk.INSERT+' linestart+1c'), self.textBox.mark_previous(tk.INSERT+' linestart'),) ):
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  mark", j, mark )
            if mark[0]=='C' and mark[1].isdigit() and 'V' in mark:
                gotCV = True; break
        if gotCV and mark != self.lastCV:
            C, V = mark[1:].split( 'V', 1 )
            #print( "bits", bits )
            #C, V = bits
            #self.parentApp.gotoGroupBCV( self.groupCode, self.verseKey.getBBB(), C, V )
            self.after_idle( lambda: self.parentApp.gotoGroupBCV( self.groupCode, self.verseKey.getBBB(), C, V ) )
            self.lastCV = mark
    # end of USFMEditWindow.onTextChange


    def getBookData( self, verseKey ):
        """
        Fetches and returns the internal Bible data for the given book
            by reading the USFM source file completely and returning the text.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("USFMEditWindow.getBookData( {} )").format( verseKey ) )
        BBB = verseKey.getBBB()
        if BBB != self.lastBBB: self.bookText = None
        if self.internalBible is not None:
            if self.bookText is None:
                self.lastBBB = BBB
                self.bookFilename = self.internalBible.possibleFilenameDict[BBB]
                self.bookFilepath = os.path.join( self.internalBible.sourceFolder, self.bookFilename )
                self.setFilepath( self.bookFilepath ) # For title displays, etc.
                #print( t('gVD'), BBB, repr(self.bookFilepath), repr(self.internalBible.encoding) )
                self.bookText = open( self.bookFilepath, 'rt', encoding=self.internalBible.encoding ).read()
                if self.bookText == None:
                    showerror( APP_NAME, 'Could not decode and open file ' + self.bookFilepath + ' with encoding ' + self.internalBible.encoding )
            return self.bookText
    # end of USFMEditWindow.getBookData


    def xxxdisplayAppendVerse( self, firstFlag, verseKey, verseDataList, currentVerse=False ):
        """
        Add the requested verse to the end of self.textBox.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            try: print( t("USFMEditWindow.displayAppendVerse"), firstFlag, verseKey, verseDataList, currentVerse )
            except UnicodeEncodeError: print( t("USFMEditWindow.displayAppendVerse"), firstFlag, verseKey, currentVerse )
        lastCharWasSpace = haveTextFlag = not firstFlag
        if verseDataList is None:
            print( "  ", verseKey, "has no data for", self.moduleID )
            #self.textBox.insert( tk.END, '--' )
        else:
            for entry in verseDataList:
                if isinstance( entry, tuple ):
                    marker, cleanText = entry[0], entry[3]
                else: marker, cleanText = entry.getMarker(), entry.getCleanText()
                #print( "  ", haveTextFlag, marker, repr(cleanText) )
                if marker and marker[0]=='¬': pass # Ignore end markers for now
                elif marker in ('chapters',): pass # Ignore added markers for now
                elif marker == 'id':
                    self.textBox.insert( tk.END, ('\n\n' if haveTextFlag else '')+cleanText, marker )
                    haveTextFlag = True
                elif marker in ('ide','rem',):
                    self.textBox.insert( tk.END, ('\n' if haveTextFlag else '')+cleanText, marker )
                    haveTextFlag = True
                elif marker == 'c': # Don't want to display this (original) c marker
                    #if not firstFlag: haveC = cleanText
                    #else: print( "   Ignore C={}".format( cleanText ) )
                    pass
                elif marker == 'c#': # Might want to display this (added) c marker
                    if cleanText != verseKey.getBBB():
                        if not lastCharWasSpace: self.textBox.insert( tk.END, ' ', 'v-' )
                        self.textBox.insert( tk.END, cleanText, 'c#' )
                        lastCharWasSpace = False
                elif marker in ('mt1','mt2','mt3','mt4', 'iot','io1','io2','io3','io4',):
                    self.textBox.insert( tk.END, ('\n' if haveTextFlag else '')+cleanText, marker )
                    haveTextFlag = True
                elif marker in ('s1','s2','s3','s4',):
                    self.textBox.insert( tk.END, ('\n' if haveTextFlag else '')+cleanText, marker )
                    haveTextFlag = True
                elif marker == 'r':
                    self.textBox.insert( tk.END, ('\n' if haveTextFlag else '')+cleanText, marker )
                    haveTextFlag = True
                elif marker in ('p','ip',):
                    self.textBox.insert ( tk.END, '\n  ' if haveTextFlag else '  ' )
                    lastCharWasSpace = True
                    if cleanText:
                        self.textBox.insert( tk.END, cleanText, '*v~' if currentVerse else 'v~' )
                        lastCharWasSpace = False
                    haveTextFlag = True
                elif marker == 'p#' and self.winType=='DBPBibleResourceWindow':
                    pass # Just ignore these for now
                elif marker in ('q1','q2','q3','q4',):
                    self.textBox.insert ( tk.END, '\n  ' if haveTextFlag else '  ' )
                    lastCharWasSpace = True
                    if cleanText:
                        self.textBox.insert( tk.END, cleanText, '*'+marker if currentVerse else marker )
                        lastCharWasSpace = False
                    haveTextFlag = True
                elif marker == 'm': pass
                elif marker == 'v':
                    if haveTextFlag:
                        self.textBox.insert( tk.END, ' ', 'v-' )
                    self.textBox.insert( tk.END, cleanText, marker )
                    self.textBox.insert( tk.END, ' ', 'v+' )
                    lastCharWasSpace = haveTextFlag = True
                elif marker in ('v~','p~'):
                    self.textBox.insert( tk.END, cleanText, '*v~' if currentVerse else marker )
                    haveTextFlag = True
                else:
                    logging.critical( t("USFMEditWindow.displayAppendVerse: Unknown marker {} {} from {}").format( marker, cleanText, verseDataList ) )
    # end of USFMEditWindow.displayAppendVerse


    def xxxgetBeforeAndAfterBibleData( self, newVerseKey ):
        """
        Returns the requested verse, the previous verse, and the next n verses.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( t("USFMEditWindow.getBeforeAndAfterBibleData( {} )").format( newVerseKey ) )
            assert( isinstance( newVerseKey, SimpleVerseKey ) )

        BBB, C, V = newVerseKey.getBCV()
        intC, intV = newVerseKey.getChapterNumberInt(), newVerseKey.getVerseNumberInt()

        prevBBB, prevIntC, prevIntV = BBB, intC, intV
        previousVersesData = []
        for n in range( -self.parentApp.viewVersesBefore, 0 ):
            failed = False
            #print( "  getBeforeAndAfterBibleData here with", n, prevIntC, prevIntV )
            if prevIntV > 0: prevIntV -= 1
            elif prevIntC > 0:
                prevIntC -= 1
                try: prevIntV = self.getNumVerses( prevBBB, prevIntC )
                except KeyError:
                    if prevIntC != 0: # we can expect an error for chapter zero
                        logging.critical( t("getBeforeAndAfterBibleData failed at"), prevBBB, prevIntC )
                    failed = True
                if not failed:
                    if BibleOrgSysGlobals.debugFlag: print( " Went back to previous chapter", prevIntC, prevIntV, "from", BBB, C, V )
            else:
                prevBBB = self.parentApp.genericBibleOrganisationalSystem.getPreviousBookCode( BBB )
                prevIntC = self.getNumChapters( prevBBB )
                prevIntV = self.getNumVerses( prevBBB, prevIntC )
                if BibleOrgSysGlobals.debugFlag: print( " Went back to previous book", prevBBB, prevIntC, prevIntV, "from", BBB, C, V )
            if not failed:
                previousVerseKey = SimpleVerseKey( prevBBB, prevIntC, prevIntV )
                previousVerseData = self.getVerseData( previousVerseKey )
                if previousVerseData: previousVersesData.insert( 0, (previousVerseKey,previousVerseData,) ) # Put verses in backwards

        # Determine the next valid verse numbers
        nextBBB, nextIntC, nextIntV = BBB, intC, intV
        nextVersesData = []
        for n in range( 0, self.parentApp.viewVersesAfter ):
            try: numVerses = self.getNumVerses( nextBBB, nextIntC )
            except KeyError: numVerses = 0
            nextIntV += 1
            if nextIntV > numVerses:
                nextIntV = 1
                nextIntC += 1 # Need to check................................
            nextVerseKey = SimpleVerseKey( nextBBB, nextIntC, nextIntV )
            nextVerseData = self.getVerseData( nextVerseKey )
            if nextVerseData: nextVersesData.append( (nextVerseKey,nextVerseData,) )

        verseData = self.getVerseData( newVerseKey )

        return verseData, previousVersesData, nextVersesData
    # end of USFMEditWindow.getBeforeAndAfterBibleData


    def updateShownBCV( self, newVerseKey ):
        """
        Updates self.textBox in various ways depending on the contextViewMode held by the enclosing window.

        Leaves the textbox in the disabled state.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "USFMEditWindow.updateShownBCV( {}) for".format( newVerseKey ), self.moduleID )
            #print( "contextViewMode", self.contextViewMode )
            assert( isinstance( newVerseKey, SimpleVerseKey ) )

        if newVerseKey.getBBB() != self.verseKey.getBBB(): # we've switched books
            if self.modified():
                self.showerror( APP_NAME, "Should save text here!" )
            self.loading = True
            self.clearText() # Leaves the text box enabled
            self.setAllText( self.getBookData( newVerseKey ) )
            self.loading = False
            self.lastCV = None

        if newVerseKey != self.verseKey: # we have a change of reference
            desiredMark = 'C{}V{}'.format( newVerseKey.getChapterNumber(), newVerseKey.getVerseNumber() )
            try: self.textBox.see( desiredMark )
            except tk.TclError: print( t("USFMEditWindow.updateShownBCV couldn't find {}").format( repr( desiredMark ) ) )
            self.verseKey = newVerseKey

        self.refreshTitle()
    # end of USFMEditWindow.updateShownBCV


    def xxcloseEditor( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("USFMEditWindow.closeEditor()") )
        if self.textBox.edit_modified():
            pass
        else: self.closeResourceWindow()
    # end of USFMEditWindow.closeEditor
# end of USFMEditWindow class



class ESFMEditWindow( USFMEditWindow ):
    pass
# end of ESFMEditWindow class



def demo():
    """
    Demo program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    if BibleOrgSysGlobals.debugFlag: print( t("Running demo...") )
    #Globals.debugFlag = True

    tkRootWindow = tk.Tk()
    tkRootWindow.title( ProgNameVersion )
    tkRootWindow.textBox = tk.Text( tkRootWindow )

    tEW = TextEditWindow( tkRootWindow )
    try: uEW = USFMEditWindow( tkRootWindow, None )
    except: pass

    # Start the program running
    tkRootWindow.mainloop()
# end of EditWindows.demo


if __name__ == '__main__':
    import multiprocessing

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables


    if 1 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        #from tkinter import TclVersion, TkVersion
        from tkinter import tix
        print( "TclVersion is", tk.TclVersion )
        print( "TkVersion is", tk.TkVersion )
        print( "tix TclVersion is", tix.TclVersion )
        print( "tix TkVersion is", tix.TkVersion )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of EditWindows.py