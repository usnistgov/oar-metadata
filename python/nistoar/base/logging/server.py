"""
A Server that can accept and record logging messages from multiple processes.

This implementation is based on the server referenced in the 
`Python Logging Cookbook <https://docs.python.org/3/howto/logging-cookbook.html#network-logging>` 
with an implementation 
`kindly provided by Vinay Sajip <https://gist.github.com/vsajip/4b227eeec43817465ca835ca66f75e2b>` 
(c. 2020, Red Dove Consultants) via the 
`BSD-3 License <https://opensource.org/license/bsd-3-clause>`.
"""
# See source implementation license at end of this file
import sys, os, json, logging.handlers, socketserver, struct, pickle
from argparse import ArgumentParser
import traceback as tb
from datetime import datetime

import psutil

from .. import config
from ..config import ConfigurationException

APP_NAME = "LogServer"

class LogRecordStreamHandler(socketserver.BaseRequestHandler):
    """
    Handler for a streaming logging request.
    This basically logs the record using whatever logging policy is
    configured locally.
    """

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.request.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.request.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.request.recv(slen - len(chunk))
            obj = self.unPickle(chunk)
            logging.info("sending message")
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)

class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.
    """

    allow_reuse_address = True

    def __init__(self,
                 host='localhost',
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.logname = None

    def serve_forever(self, poll_interval=0.5):
        now = datetime.now().isoformat()
        logging.getLogger(APP_NAME).info("Starting Log Server at %s", now)
        super().serve_forever(poll_interval)

def define_options(progname):
    """
    return an ArgumentParser configured with server command line options
    """
    description = \
"""Collect log messages from multiple processes for recording to a
combined log file."""
    epilog = None

    parser = ArgumentParser(progname, None, description, epilog)

    parser.add_argument('-c', '--config-file', type=str, metavar='FILE',
                        dest='cfgfile',
                        help='load the configuration from FILE')
    parser.add_argument('-C', '--no-config', action='store_true', 
                        dest='noconfig', default=False,
                        help='Do not attempt to load configuration; '
                             '(requires -p and -l)')
    parser.add_argument('-N', '--config-name', type=str, metavar='NAME',
                        dest='cfgname', default='logserver',
                        help='the name to use to retrieve configuration ' +
                             'from a configuration server. (Ignored when ' +
                             '-c is used')
    parser.add_argument('-p', '--port', type=int, metavar='N', default=None,
                        dest='port',
                        help='list for log messages on port N (overriding '
                             'configuration)')
    parser.add_argument('-l', '--log-file', type=str, metavar='FILE',
                        dest='logfile', default=None,
                        help='use FILE as the output log file (overriding '
                             'configuration)')
    parser.add_argument('-P', '--pid-file', type=str, metavar='FILE',
                        dest='pidfile', default=None,
                        help='location of pid file that can be used to kill '
                             'the server; if not specified, a file matching '
                             'the name of the log but with the .pid extension '
                             'will be written')
    parser.add_argument('-k', '--kill-server', action='store_true',
                        dest='stop',
                        help='stop a running server using it PID file')
    parser.add_argument('-T', '--tag', type=str, metavar='ID',
                        dest='tag', default=None,
                        help='a label to use to help identify the server '
                             'process when it comes time to kill it')

    return parser

def main(prog, args, cfg=None):
    parser = define_options(prog)
    opts = parser.parse_args(args)

    if not cfg and not opts.noconfig:
      if opts.cfgfile:
          try:
              cfg = config.load_from_file(opts.cfgfile)
          except Exception as ex:
              raise ConfigurationException("Failed to read config file, %s: %s" %
                                           (opts.cfgfile, str(ex))) from ex

      else:
          # requires env vars OAR_CONFIG_SERVICE, OAR_CONFIG_ENV to be set
          cfg = config.service.get(opts.cfgname)

      if not cfg and not opts.port:
          raise ConfigurationException("No configuration available for " +
                                       opts.cfgname)

    if opts.port:
        if not cfg:
            cfg = {}
        cfg['port'] = opts.port
    cfg.setdefault('logfile', 'logserver.log')
    if opts.logfile:
        cfg['logfile'] = opts.logfile
    cfg.setdefault('logformat', config.SERVER_LOG_FORMAT)

    config.configure_logging(cfg)
    pidfile = determine_pidfile(opts.pidfile)
    if opts.stop:
        return stop_server(pidfile)
    record_pid(pidfile, opts)
        
    server = make_server(cfg)
    server.serve_forever()
    return 0

def stop_server(pidfile):
    log = logging.getLogger(APP_NAME)
    if not os.path.isfile(pidfile):
        print(f"{APP_NAME}: No server found to be running ({pidfile} not found)",
              file=sys.stderr)
        return 0

    try:
        with open(pidfile) as fd:
            pidnm = fd.readline().split()
    except Exception as ex:
        print(f"{APP_NAME}: {pidfile}: Failed to read pid file: {str(ex)}")
        return 3

    if not pidnm[0]:
        print(f"{APP_NAME}: No server found ({pidfile}: empty)", file=sys.stderr)

    pnm = pidnm[1] if len(pidnm) > 1 else None
    tag = pidnm[2] if len(pidnm) > 2 else None
    try:
        p = psutil.Process(int(pidnm[0]))
        if (pnm and p.cmdline()[0] != pnm) or \
           (tag and not any(tag in a for a in p.cmdline())):
            print(f"{APP_NAME}: No server found running (stale pid file?)",
                  file=sys.stderr)
            print(f"  {' '.join(pidnm)}", file=sys.stderr)
            return 0
        p.kill()
        p.wait(5)
    except (ValueError, TypeError) as ex:
        print(f"{APP_NAME}: Bad PID contents: not a number: {pidnm[0]}",
              file=sys.stderr)
        return 3
    except psutil.NoSuchProcess as ex:
        print(f"{APP_NAME}: Server not running with pid={pidnm[0]}",
              file=sys.stderr)
        return 0
    except psutil.TimeoutExpired as ex:
        print(f"{APP_NAME}: Server (pid={pidnm[0]}) not responding",
              file=sys.stderr)
        return 1
    except Exception as ex:
        print(f"{APP_NAME}: Failed to find/kill server: {str(ex)}",
              file=sys.stderr)
        return 4
    else:
        try:
            os.remove(pidfile)
        except IOError as ex:
            print(f"{APP_NAME}: Trouble removing pid file: {pidfile}: {str(ex)}")

    return 0

def determine_pidfile(pidfile=None):
    if not pidfile:
        pidfile = os.path.splitext(config.global_logfile)[0] + ".pid"
    elif not os.path.isabs(pidfile):
        pidfile = os.path.join(config.global_logdir, pidfile)
    return pidfile

def record_pid(pidfile=None, opts=None):
    if not pidfile:
        pidfile = determine_pidfile()
    pid = os.getpid()
    try:
        p = psutil.Process(pid)
        
        with open(pidfile, 'w') as fd:
            fd.write(str(pid))
            fd.write(' ')
            fd.write(p.cmdline()[0])
            if opts.tag:
                fd.write(' ')
                fd.write(opts.tag)
            fd.write('\n')
    except Exception as ex:
        log = logging.getLogger(APP_NAME)
        log.error("Failed to write PID file (%s): %s", pidfile, str(ex))
        print(f"{APP_NAME}: Failed to write PID file {pidfile}: {str(ex)}")

    return pidfile

def make_server(cfg):
    """
    create and return an instance of the loggging server, ready to handle
    logging messages.
    """
    port = cfg.get('port', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
    return LogRecordSocketReceiver(port=port)

if __name__ == '__main__':
    prog = APP_NAME
    args = sys.argv[1:]
    try:
        rc = main(prog, args)
    except KeyboardInterrupt:
        rc = 2
        print("Keyboard interrupt", file=sys.stderr)
    except ConfigurationException as ex:
        rc = 1
        print(f"{prog}: {str(ex)}", file=sys.stderr) 
    except Exception as ex:
        rc = 4
        tb.print_exception(ex);
        print(f"{prog}: {str(ex)}")
    sys.exit(rc)


# The above code was adapted from the logging server provided by Vinay
# Sajip at https://gist.github.com/vsajip/4b227eeec43817465ca835ca66f75e2b,
# licensed as follows:
#
# Copyright 2002 Red Dove Consultants
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met: 
# 
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer. 
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution. 
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE. 
