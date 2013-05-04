# -*- coding: utf-8 -*-
'''
    saltcloud.utils.nb_popen
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Non blocking subprocess Popen.

    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2013 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.
'''

# Import python libs
import os
import sys
import fcntl
import logging
import subprocess


class NonBlockingPopen(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        self.fake_tty = kwargs.pop('fake_tty', False)
        self.stream_stds = kwargs.pop('stream_stds', False)
        self.olog = logging.getLogger('{0}.stdout'.format(__name__))
        self.elog = logging.getLogger('{0}.stderr'.format(__name__))
        if self.fake_tty is True:
            if kwargs.get('stdin', None) is not None:
                raise RuntimeError(
                    'Can\'t use a fake tty if you\'re also passing a stdin'
                )

            # Let's create a fake, pseudo, tty
            import pty
            self.fake_tty_master, self.fake_tty_slave = pty.openpty()
            kwargs['stdin'] = self.fake_tty_slave

        super(NonBlockingPopen, self).__init__(*args, **kwargs)

        if self.fake_tty:
            os.fdopen(self.fake_tty_master, 'w', 0)

        if self.stdout is not None and self.stream_stds:
            fod = self.stdout.fileno()
            fol = fcntl.fcntl(fod, fcntl.F_GETFL)
            fcntl.fcntl(fod, fcntl.F_SETFL, fol | os.O_NONBLOCK)
            self.obuff = ''

        if self.stderr is not None and self.stream_stds:
            fed = self.stderr.fileno()
            fel = fcntl.fcntl(fed, fcntl.F_GETFL)
            fcntl.fcntl(fed, fcntl.F_SETFL, fel | os.O_NONBLOCK)
            self.ebuff = ''

    def poll(self):
        poll = super(NonBlockingPopen, self).poll()

        if self.stdout is not None and self.stream_stds:
            try:
                obuff = self.stdout.read()
                self.obuff += obuff
                if obuff:
                    self.olog.warn(obuff)
                #sys.stdout.write(obuff)
            except IOError, err:
                if err.errno not in (11, 35):
                    # We only handle Resource not ready properly, any other
                    # raise the exception
                    raise
        if self.stderr is not None and self.stream_stds:
            try:
                ebuff = self.stderr.read()
                self.ebuff += ebuff
                if ebuff:
                    self.elog.warn(ebuff)
                #sys.stderr.write(ebuff)
            except IOError, err:
                if err.errno not in (11, 35):
                    # We only handle Resource not ready properly, any other
                    # raise the exception
                    raise

        if poll is None:
            # Not done yet
            return poll

        if not self.stream_stds:
            # Allow the same attribute access even though not streaming to stds
            try:
                self.obuff = self.stdout.read()
            except IOError, err:
                if err.errno not in (11, 35):
                    # We only handle Resource not ready properly, any other
                    # raise the exception
                    raise
            try:
                self.ebuff = self.stderr.read()
            except IOError, err:
                if err.errno not in (11, 35):
                    # We only handle Resource not ready properly, any other
                    # raise the exception
                    raise
        return poll

    def __del__(self):
        if self.fake_tty:
            self.fake_tty_master.close()

        if self.stdout is not None and self.stream_stds:
            fod = self.stdout.fileno()
            fol = fcntl.fcntl(fod, fcntl.F_GETFL)
            fcntl.fcntl(fod, fcntl.F_SETFL, fol & ~os.O_NONBLOCK)

        if self.stderr is not None and self.stream_stds:
            fed = self.stderr.fileno()
            fel = fcntl.fcntl(fed, fcntl.F_GETFL)
            fcntl.fcntl(fed, fcntl.F_SETFL, fel & ~os.O_NONBLOCK)

        super(NonBlockingPopen, self).__del__()
