#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BiblelatorHelpers.py
#
# Various non-GUI helper functions for Biblelator Bible display/editing
#
# Copyright (C) 2014-2016 Robert Hunt
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
    createEmptyUSFMBookText( BBB, getNumChapters, getNumVerses )
    createEmptyUSFMBooks( folderPath, BBB, availableVersifications, availableVersions, requestDict )
    calculateTotalVersesForBook( BBB, getNumChapters, getNumVerses )
    mapReferenceVerseKey( mainVerseKey )
    mapParallelVerseKey( forGroupCode, mainVerseKey )
"""

from gettext import gettext as _

LastModifiedDate = '2016-01-29' # by RJH
ShortProgName = "Biblelator"
ProgName = "Biblelator helpers"
ProgVersion = '0.29'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


import sys, os.path

# Biblelator imports
from BiblelatorGlobals import APP_NAME_VERSION, BIBLE_GROUP_CODES

# BibleOrgSys imports
sys.path.append( '../BibleOrgSys/' )
import BibleOrgSysGlobals
from VerseReferences import SimpleVerseKey, FlexibleVersesKey
from BibleReferencesLinks import BibleReferencesLinks



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', _(errorBit) )
# end of exp



def createEmptyUSFMBookText( BBB, getNumChapters, getNumVerses ):
    """
    Give it the functions for getting the number of chapters and the number of verses
    Returns a string that is the text of a blank USFM book.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("createEmptyUSFMBookText( {} )").format( BBB ) )
    USFMAbbreviation = BibleOrgSysGlobals.BibleBooksCodes.getUSFMAbbreviation( BBB )
    USFMNumber = BibleOrgSysGlobals.BibleBooksCodes.getUSFMNumber( BBB )
    bookText = '\\id {} Empty book created by {}\n'.format( USFMAbbreviation.upper(), APP_NAME_VERSION )
    bookText += '\\ide UTF-8\n'
    bookText += '\\h Bookname\n'
    bookText += '\\mt Book Title\n'
    for C in range( 1, getNumChapters(BBB)+1 ):
        bookText += '\\c {}\n'.format( C )
        for V in range( 1, getNumVerses(BBB,C)+1 ):
            bookText += '\\v {} \n'.format( V )
    return bookText
# end of BiblelatorHelpers.createEmptyUSFMBookText



def createEmptyUSFMBooks( folderPath, currentBBB, requestDict ):
    """
    Create empty USFM books or CV shells in the given folderPath
        as requested by the dictionary parameters:
            Books: 'OT'
            Fill: 'Versification'
            Versification: 'KJV'
            Version: 'KJV1611'
    """
    from BibleVersificationSystems import BibleVersificationSystem
    from InternalBible import OT39_BOOKLIST, NT27_BOOKLIST
    from InternalBibleInternals import BOS_ALL_ADDED_MARKERS
    from USFMBible import USFMBible

    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("createEmptyUSFMBooks( {}, {}, {} )").format( folderPath, currentBBB, requestDict ) )


    versificationObject = BibleVersificationSystem( requestDict['Versification'] ) \
                            if requestDict['Fill']=='Versification' else None
    print( 'versificationObject', versificationObject )
    if versificationObject is not None:
        getNumChapters, getNumVerses = versificationObject.getNumChapters, versificationObject.getNumVerses

    if requestDict['Fill'] == 'Version':
        #ALL_CHAR_MARKERS = BibleOrgSysGlobals.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )
        uB = USFMBible( requestDict['Version'] ) # Get the Bible object
        print( "Fill Bible1", uB )
        uB.preload()
        print( "Fill Bible2", uB )
        #uB.loadBooks()
        #print( "Fill Bible3", uB )

    if requestDict['Books'] == 'None': booklist = []
    elif requestDict['Books'] == 'Current': booklist = [ currentBBB ]
    elif requestDict['Books'] == 'All': booklist = OT39_BOOKLIST + NT27_BOOKLIST
    elif requestDict['Books'] == 'OT': booklist = OT39_BOOKLIST
    elif requestDict['Books'] == 'NT': booklist = NT27_BOOKLIST
    else: halt # programming error

    count = 0
    skippedBooklist = []
    for BBB in booklist:
        if requestDict['Fill'] == 'Versification' \
        and versificationObject is not None \
        and BBB not in versificationObject:
            skippedBooklist.append( BBB )
            continue
        #if requestDict['Fill'] == 'Version' \
        #and uB is not None \
        #and BBB not in uB:
            #skippedBooklist.append( BBB )
            #continue

        USFMAbbreviation = BibleOrgSysGlobals.BibleBooksCodes.getUSFMAbbreviation( BBB )
        USFMNumber = BibleOrgSysGlobals.BibleBooksCodes.getUSFMNumber( BBB )

        if requestDict['Fill'] == 'None': bookText = ''
        elif requestDict['Fill'] == 'Basic':
            bookText = '\\id {} Empty book created by {}\n'.format( USFMAbbreviation.upper(), APP_NAME_VERSION )
            bookText += '\\ide UTF-8\n'
            bookText += '\\h Bookname\n'
            bookText += '\\mt Book Title\n'
            bookText += '\\c 1\n'
        elif requestDict['Fill'] == 'Versification':
            bookText = createEmptyUSFMBookText( BBB, getNumChapters, getNumVerses )
        elif requestDict['Fill'] == 'Version':
            try: uB.loadBook( BBB )
            except FileNotFoundError:
                skippedBooklist.append( BBB )
                continue
            uBB = uB[BBB] # Get the Bible book object
            bookText = ''
            for verseDataEntry in uBB._processedLines:
                pseudoMarker, cleanText = verseDataEntry.getMarker(), verseDataEntry.getCleanText()
                #print( BBB, pseudoMarker, repr(cleanText) )
                if '¬' in pseudoMarker or pseudoMarker in BOS_ALL_ADDED_MARKERS or pseudoMarker in ('c#','vp#',):
                    continue # Just ignore added markers -- not needed here
                #if pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                    #pseudoMarker += ' ' # Append a space since it didn't have one
                #if pseudoMarker in ALL_CHAR_MARKERS: # Character markers to be closed
                    #print( "CHAR MARKER" )
                    #pass
                    ##if (USFM[-2]=='\\' or USFM[-3]=='\\') and USFM[-1]!=' ':
                    #if bookText[-1] != ' ':
                        #bookText += ' ' # Separate markers by a space e.g., \p\bk Revelation
                        #if BibleOrgSysGlobals.debugFlag: print( "toUSFM: Added space to {!r} before {!r}".format( bookText[-2], pseudoMarker ) )
                    #adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                #elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                #elif pseudoMarker in ('fr','fq','ft','xo',): USFM += ' ' # These go on the same line just separated by spaces and don't get closed
                if bookText: bookText += '\n' # paragraph markers go on a new line
                if not cleanText: bookText += '\\{}'.format( pseudoMarker )
                elif pseudoMarker == 'c': bookText += '\\c {}'.format( cleanText )
                elif pseudoMarker == 'v': bookText += '\\v {} '.format( cleanText )
                else: bookText += '\\{} '.format( pseudoMarker )
                #print( pseudoMarker, USFM[-200:] )
        else: halt # programming error

        # Write the actual file
        filename = '{}-{}.USFM'.format( USFMNumber, USFMAbbreviation )
        with open( os.path.join( folderPath, filename ), mode='wt' ) as theFile:
            theFile.write( bookText )
        count += 1
    print( len(skippedBooklist), "books skipped:", skippedBooklist ) # Should warn the user here
    print( count, "books created" )
# end of BiblelatorHelpers.createEmptyUSFMBooks



def calculateTotalVersesForBook( BBB, getNumChapters, getNumVerses ):
    """
    Give it the functions for getting the number of chapters and number of verses
    Returns the total number of verses in the book
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("calculateTotalVersesForBook( {} )").format( BBB ) )
    totalVerses = 0
    for C in range( 1, getNumChapters(BBB)+1 ):
        totalVerses += getNumVerses( BBB, C )
    return totalVerses
# end of BiblelatorHelpers.calculateTotalVersesForBook



def mapReferenceVerseKey( mainVerseKey ):
    """
    Returns the verse key for OT references in the NT (and vv), etc.

    Returns None if we don't have a mapping.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("mapReferenceVerseKey( {} )").format( mainVerseKey.getShortText() ) )
    referenceVerseKeyDict = {
        SimpleVerseKey('MAT','2','18'): SimpleVerseKey('JER','31','15'),
        SimpleVerseKey('MAT','3','3'): SimpleVerseKey('ISA','40','3'),
        }
    if mainVerseKey in referenceVerseKeyDict:
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( '  returning {}'.format( referenceVerseKeyDict[mainVerseKey].getShortText() ) )
        return referenceVerseKeyDict[mainVerseKey]
# end of BiblelatorHelpers.mapReferenceVerseKey


def mapParallelVerseKey( forGroupCode, mainVerseKey ):
    """
    Returns the verse key for synoptic references in the NT, etc.

    Returns None if we don't have a mapping.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("mapParallelVerseKey( {}, {} )").format( forGroupCode, mainVerseKey.getShortText() ) )
    groupIndex = BIBLE_GROUP_CODES.index( forGroupCode ) - 1
    parallelVerseKeyDict = {
        SimpleVerseKey('MAT','3','13'): (SimpleVerseKey('MRK','1','9'), SimpleVerseKey('LUK','3','21'), SimpleVerseKey('JHN','1','31') )
        }
    if mainVerseKey in parallelVerseKeyDict:
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( '  returning {}'.format( parallelVerseKeyDict[mainVerseKey][groupIndex].getShortText() ) )
        return parallelVerseKeyDict[mainVerseKey][groupIndex]
# end of BiblelatorHelpers.mapParallelVerseKey



loadedReferences = None
def mapReferencesVerseKey( mainVerseKey ):
    """
    Returns the list of FlexibleVerseKeys for references related to the given verse key.

    Returns None if we don't have a mapping.
    """
    global loadedReferences
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("mapReferencesVerseKey( {} )").format( mainVerseKey.getShortText() ) )
    if loadedReferences is None:
        loadedReferences = BibleReferencesLinks()
        loadedReferences.loadData()
    result = loadedReferences.getRelatedPassagesList( mainVerseKey )
    # Returns a list containing 2-tuples:
    #    0: Link type ('QuotedOTReference','AlludedOTReference','PossibleOTReference')
    #    1: Link FlexibleVersesKey object
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( "  mapReferencesVerseKey got result:", result )
    resultList = []
    for linkType, link in result:
        resultList.append( link )
    return resultList
    # old sample code
        #referenceVerseKeyDict = {
            #SimpleVerseKey('MAT','2','18'): SimpleVerseKey('JER','31','15'),
            #SimpleVerseKey('MAT','3','3'): FlexibleVersesKey( 'ISA_40:3,7,14-15' ),
            #}
        #if mainVerseKey in referenceVerseKeyDict:
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( '  returning {}'.format( referenceVerseKeyDict[mainVerseKey].getShortText() ) )
            #return referenceVerseKeyDict[mainVerseKey]
# end of BiblelatorHelpers.mapReferencesVerseKey



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    from tkinter import Tk
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    if BibleOrgSysGlobals.debugFlag: print( exp("Running demo...") )

    tkRootWindow = Tk()
    tkRootWindow.title( ProgNameVersion )

    #swnd = SaveWindowNameDialog( tkRootWindow, ["aaa","BBB","CcC"], "Test SWND" )
    #print( "swndResult", swnd.result )
    #dwnd = DeleteWindowNameDialog( tkRootWindow, ["aaa","BBB","CcC"], "Test DWND" )
    #print( "dwndResult", dwnd.result )
    #srb = SelectResourceBox( tkRootWindow, [(x,y) for x,y, in {"ESV":"ENGESV","WEB":"ENGWEB","MS":"MBTWBT"}.items()], "Test SRB" )
    #print( "srbResult", srb.result )

    #tkRootWindow.quit()

    # Start the program running
    #tkRootWindow.mainloop()
# end of BiblelatorHelpers.demo


if __name__ == '__main__':
    from BibleOrgSysGlobals import setup, addStandardOptionsAndProcess, closedown
    import multiprocessing

    # Configure basic set-up
    parser = setup( ProgName, ProgVersion )
    addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables


    if 1 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        from tkinter import TclVersion, TkVersion
        from tkinter import tix
        print( "TclVersion is", TclVersion )
        print( "TkVersion is", TkVersion )
        print( "tix TclVersion is", tix.TclVersion )
        print( "tix TkVersion is", tix.TkVersion )

    demo()

    closedown( ProgName, ProgVersion )
# end of BiblelatorHelpers.py