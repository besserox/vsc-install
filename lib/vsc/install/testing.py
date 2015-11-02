#!/usr/bin/env python
# -*- coding: latin-1 -*-
#
# Copyright 2014-2015 Ghent University
#
# This file is part of vsc-install,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/vsc-install
#
# vsc-install is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-install is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-install. If not, see <http://www.gnu.org/licenses/>.
#
"""
Shared module for vsc software testing

TestCase: use instead of unittest TestCase
   from vsc.install.testing import TestCase

VSCImport usage: make a module 00-import.py in the test/ dir that has only the following line
   from vsc.install.testing import VSCImportTest

Running python setup.py test will pick this up and do its magic

@author: Stijn De Weirdt (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""
import os
import re
import sys

from cStringIO import StringIO
from unittest import TestCase as OrigTestCase
from vsc.install.shared_setup import generate_packages, generate_scripts, generate_modules, \
    FILES_IN_PACKAGES, REPO_BASE_DIR
from vsc.install.headers import nicediff, check_header


class TestCase(OrigTestCase):
    """Enhanced test case, provides extra functionality (e.g. an assertErrorRegex method)."""

    LOGCACHE = {}

    ASSERT_MAX_DIFF = 100
    DIFF_OFFSET = 5 # lines of text around changes

    def assertEqual(self, a, b, msg=None):
        """Make assertEqual always print useful messages"""
        try:
            super(TestCase, self).assertEqual(a, b)
        except AssertionError as e:
            if msg is None:
                msg = str(e)
            else:
                msg = "%s: %s" % (msg, e)

            if isinstance(a, basestring):
                txta = a
            else:
                txta = pprint.pformat(a)
            if isinstance(b, basestring):
                txtb = b
            else:
                txtb = pprint.pformat(b)

            diff = nicediff(txta, txtb, offset=self.DIFF_OFFSET)
            if len(diff) > self.ASSERT_MAX_DIFF:
                limit = ' (first %s lines)' % self.ASSERT_MAX_DIFF
            else:
                limit = ''

            raise AssertionError("%s:\nDIFF%s:\n%s" % (msg, limit, ''.join(diff[:self.ASSERT_MAX_DIFF])))

    def setUp(self):
        """Prepare test case."""
        super(TestCase, self).setUp()
        self.orig_sys_stdout = sys.stdout
        self.orig_sys_stderr = sys.stderr

    def convert_exception_to_str(self, err):
        """Convert an Exception instance to a string."""
        msg = err
        if hasattr(err, 'msg'):
            msg = err.msg
        elif hasattr(err, 'message'):
            msg = err.message
            if not msg:
                # rely on str(msg) in case err.message is empty
                msg = err
        elif hasattr(err, 'args'):  # KeyError in Python 2.4 only provides message via 'args' attribute
            msg = err.args[0]
        else:
            msg = err
        try:
            res = str(msg)
        except UnicodeEncodeError:
            res = msg.encode('utf8', 'replace')

        return res

    def assertErrorRegex(self, error, regex, call, *args, **kwargs):
        """
        Convenience method to match regex with the expected error message.
        Example: self.assertErrorRegex(OSError, "No such file or directory", os.remove, '/no/such/file')
        """
        try:
            call(*args, **kwargs)
            str_kwargs = ['='.join([k, str(v)]) for (k, v) in kwargs.items()]
            str_args = ', '.join(map(str, args) + str_kwargs)
            self.assertTrue(False, "Expected errors with %s(%s) call should occur" % (call.__name__, str_args))
        except error, err:
            msg = self.convert_exception_to_str(err)
            if isinstance(regex, basestring):
                regex = re.compile(regex)
            self.assertTrue(regex.search(msg), "Pattern '%s' is found in '%s'" % (regex.pattern, msg))

    def mock_stdout(self, enable):
        """Enable/disable mocking stdout."""
        sys.stdout.flush()
        if enable:
            sys.stdout = StringIO()
        else:
            sys.stdout = self.orig_sys_stdout

    def mock_stderr(self, enable):
        """Enable/disable mocking stdout."""
        sys.stderr.flush()
        if enable:
            sys.stderr = StringIO()
        else:
            sys.stderr = self.orig_sys_stderr

    def get_stdout(self):
        """Return output captured from stdout until now."""
        return sys.stdout.getvalue()

    def get_stderr(self):
        """Return output captured from stderr until now."""
        return sys.stderr.getvalue()

    def mock_logmethod(self, logmethod_func):
        """
        Intercept the logger logmethod. Use as
            mylogger = logging.getLogger
            mylogger.error = self.mock_logmethod(mylogger.error)
        """
        def logmethod(*args, **kwargs):
            if hasattr(logmethod_func, 'func_name'):
                funcname=logmethod_func.func_name
            elif hasattr(logmethod_func, 'im_func'):
                funcname = logmethod_func.im_func.__name__
            else:
                raise Exception("Unknown logmethod %s" % (dir(logmethod_func)))
            logcache = self.LOGCACHE.setdefault(funcname, [])
            logcache.append({'args': args, 'kwargs': kwargs})
            logmethod_func(*args, **kwargs)

        return logmethod

    def reset_logcache(self, funcname=None):
        """
        Reset the LOGCACHE
        @param: funcname: if set, only reset the cache for this log function
                (default is to reset the whole chache)
        """
        if funcname:
            self.LOGCACHE[funcname] = []
        else:
            self.LOGCACHE = {}

    def count_logcache(self, funcname):
        """
        Return the number of log messages for funcname in the logcache
        """
        return len(self.LOGCACHE.get(funcname, []))

    def tearDown(self):
        """Cleanup after running a test."""
        self.mock_stdout(False)
        self.mock_stderr(False)
        self.reset_logcache()
        super(TestCase, self).tearDown()


class VSCImportTest(TestCase):
    """Dummy class to prove importing VSC namespace works"""

    EXTRA_PKGS = None # additional packages to test / try to import
    EXCLUDE_PKGS = None # list of regexp patters to remove from list of package to test

    EXTRA_MODS = None # additional modules to test / try to import
    EXCLUDE_MODS = None # list of regexp patterns to remove from list of modules to test

    EXTRA_SCRIPTS = None # additional scripts to test / try to import
    EXCLUDE_SCRIPTS = None # list of regexp patterns to remove from list of scripts to test

    CHECK_HEADER = True

    def _import(self, pkg):
        try:
            __import__(pkg)
        except ImportError:
            pass

        self.assertTrue(pkg in sys.modules, msg='import %s was success' % pkg)

    def test_import_packages(self):
        """Try to import each namespace"""
        for pkg in generate_packages(extra=self.EXTRA_PKGS, exclude=self.EXCLUDE_PKGS):
            self._import(pkg)

            if self.CHECK_HEADER:
                for fn in FILES_IN_PACKAGES['packages'][pkg]:
                    self.assertFalse(check_header(os.path.join(REPO_BASE_DIR, fn), script=False, write=False),
                                     msg='check_header of %s' % fn)

    def test_import_modules(self):
        """Try to import each module"""
        for modname in generate_modules(extra=self.EXTRA_MODS, exclude=self.EXCLUDE_MODS):
            self._import(modname)

    def test_importscripts(self):
        """Try to import each python script as a module"""
        # sys.path is already setup correctly
        for scr in generate_scripts(extra=self.EXTRA_SCRIPTS, exclude=self.EXCLUDE_SCRIPTS):
            if not scr.endswith('.py'):
                continue
            self._import(os.path.basename(scr)[:-len('.py')])

            if self.CHECK_HEADER:
                self.assertFalse(check_header(os.path.join(REPO_BASE_DIR, scr), script=True, write=False),
                                 msg='check_header of %s' % scr)
