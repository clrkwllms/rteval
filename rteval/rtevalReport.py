#  rtevalReport.py - Takes care of the report generation
#
#   Copyright 2009 - 2012   Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2012   David Sommerseth <davids@redhat.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.

import os, tarfile
from datetime import datetime
import xmlout


class rtevalReport(object):
    def __init__(self, rtev_version, installdir, annotate):
        self.__version = rtev_version
        self.__installdir = installdir
        self.__annotate = annotate
        self.__start = datetime.now()
        self.__xmlreport = None
        self.__reportdir = None


    def _report(self, measure_start, xslt_tpl):
        "Create a screen report, based on a predefined XSLT template"

        if measure_start is None:
            raise Exception("No measurement runs have been attempted")

        duration = datetime.now() - measure_start
        seconds = duration.seconds
        hours = seconds / 3600
        if hours: seconds -= (hours * 3600)
        minutes = seconds / 60
        if minutes: seconds -= (minutes * 60)

        # Start new XML report
        self.__xmlreport = xmlout.XMLOut('rteval', self.__version)
        self.__xmlreport.NewReport()

        self.__xmlreport.openblock('run_info', {'days': duration.days,
                                 'hours': hours,
                                 'minutes': minutes,
                                 'seconds': seconds})
        self.__xmlreport.taggedvalue('date', self.__start.strftime('%Y-%m-%d'))
        self.__xmlreport.taggedvalue('time', self.__start.strftime('%H:%M:%S'))
        if self.annotate:
            self.__xmlreport.taggedvalue('annotate', self.__annotate)
        self.__xmlreport.closeblock()

        # Collect and add info about the system
        self.__xmlreport.AppendXMLnodes(self._sysinfo.MakeReport())

        # Add load info
        self.__xmlreport.AppendXMLnodes(self._loadmods.MakeReport())

        self.cyclictest.genxml(self.__xmlreport)
        if self.cmd_options.hwlatdetect:
            self._hwlat.genxml(self.__xmlreport)

        # Close the report - prepare for return the result
        self.__xmlreport.close()

        # Write the XML to the report directory
        if self.xml != None:
            self.__xmlreport.Write(self.xml, None)

        # Write a text report to stdout as well, using the
        # rteval_text.xsl template
        self.__xmlreport.Write("-", xslt_tpl)


    def _XMLreport(self):
        "Retrieves the complete rteval XML report as a libxml2.xmlDoc object"
        return self.__xmlreport.GetXMLdocument()


    def _show_report(self, xmlfile, xsltfile):
        '''summarize a previously generated xml file'''
        print "Loading %s for summarizing" % xmlfile

        xsltfullpath = os.path.join(self.__installdir, xsltfile)
        if not os.path.exists(xsltfullpath):
            raise RuntimeError, "can't find XSL template (%s)!" % xsltfullpath

        xmlreport = xmlout.XMLOut('rteval', self.version)
        xmlreport.LoadReport(xmlfile)
        xmlreport.Write('-', xsltfullpath)
        del xmlreport


    def _make_report_dir(self, workdir):
        t = self.__start
        i = 1
        self.__reportdir = os.path.join(workdir,
                                      t.strftime("rteval-%Y%m%d-"+str(i)))
        while os.path.exists(self.__reportdir):
            i += 1
            self.__reportdir = os.path.join(workdir,
                                          t.strftime('rteval-%Y%m%d-'+str(i)))
        if not os.path.isdir(self.__reportdir):
            os.mkdir(self.__reportdir)
            os.mkdir(os.path.join(self.__reportdir, "logs"))
        return self.__reportdir


    def _tar_results(self):
        if not os.path.isdir(self.__reportdir):
            raise RuntimeError, "no such directory: %s" % reportdir

        dirname = os.path.dirname(self.__reportdir)
        rptdir = os.path.basename(self.__reportdir)
        cwd = os.getcwd()
        os.chdir(dirname)
        try:
            t = tarfile.open(rptdir + ".tar.bz2", "w:bz2")
            t.add(rptdir)
            t.close()
        except:
            os.chdir(cwd)
