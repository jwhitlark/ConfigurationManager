"""Configuration handler to go from default -> config files -> environmental variables -> command line options.

Adds an option to dump the current loaded config as a config file, and
the ability to expand environmental variables in help msgs.  Options
that come from a config file MUST be in a config group.

Extends/depends on os, ConfigParser, and optparse.

Advanced functionality of ConfigParser and optparse HAS NOT BEEN TESTED.

Usage example:

    from ConfigManager import ConfigManager, ConfigGroup

    appname = 'cfgmgr'   # could use basename, I suppose

    cfgmgr = ConfigManager()
    cfgmgr.set_config_files(['/etc/%s/%s.conf' % (appname, appname),
                             os.path.expanduser('~/.%s.cfg' % appname)]

    daemonGroup = ConfigGroup(cfgmgr, "Daemon", "Settings for running as a daemon.")
    daemonGroup.add_option('-p', '--pidfile', envvar="CFGMGR_PIDFILE",
                           help="The location to use for the pid file.",
                           default="/var/run/%s.pid" % (appname,))

    cfgmgr.add_option_group(daemonGroup)
    print cfgmgr.parse_args()
"""

__version__ = '0.9.0'

__all__ = ['ConfigManager', 'ConfigGroup', 'ConfigOption']

__copyright__ = """
Copyright (c) 2010 Jason A. Whitlark.  All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

  * Neither the name of the author nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from optparse import OptionParser, OptionGroup, Option, IndentedHelpFormatter
from ConfigParser import SafeConfigParser
import os

class ExpandedIndentedHelpFormatter(IndentedHelpFormatter):
    "Add expansion of Environmental variables in help string."

    def __init__(self, *args, **kwargs):
        IndentedHelpFormatter.__init__(self, *args, **kwargs)
        self.envvar_tag = "%envvar"

    def expand_default(self, option):
        if hasattr(option, 'envvar') and hasattr(option, 'help'):
            option.help = option.help.replace(str(self.envvar_tag), "$" + str(option.envvar))

        return IndentedHelpFormatter.expand_default(self, option)


class ConfigOption(Option):
    ATTRS = Option.ATTRS
    ATTRS.append('envvar')
    ATTRS.append('group_name')
    ATTRS.append('parent_parser')

    ACTIONS = Option.ACTIONS + ('generate_config',)

    def __init__(self, *opts, **attrs):
        Option.__init__(self, *opts, **attrs)
        self._look_for_config_value()
        self._look_for_env_var()


    def _look_for_env_var(self):
        "Replace default with the environmental variable, if it exists."
        if hasattr(self, 'envvar'):
            val = os.getenv(self.envvar)
            if val:
                self.default = val
                delattr(self, 'envvar')


    def _look_for_config_value(self):
        if hasattr(self, 'group_name') and hasattr(self, 'parent_parser'):
            if self.parent_parser:
                config_val = self.parent_parser._get_config_value(self.group_name,
                                                                  self.dest)
                if config_val:
                    self.default = config_val


    def _lookup_default_from_config_file(self, parser, grp, opt):
        return parser.find_config_value_from_file(grp.title, opt.dest)


    def take_action(self, action, dest, opt, value, values, parser):
        "Extended to handle generation a config file"
        if action == "generate_config":
            parser.generate_and_print_config_file()
            parser.exit()

        Option.take_action(self, action, dest, opt, value, values, parser)



class ConfigGroup(OptionGroup):
    # Add information the option needs to look up its config.
    def add_option(self, *args, **kwargs):
        kwargs['group_name'] = self.title
        kwargs['parent_parser'] = self.parser
        option = OptionGroup.add_option(self, *args, **kwargs)
        return option



class ConfigManager(OptionParser):

    def __init__(self,
                 usage=None,
                 option_list=None,
                 option_class=ConfigOption,
                 version=None,
                 conflict_handler="error",
                 description=None,
                 formatter=None,
                 add_help_option=True,
                 prog=None,
                 epilog=None):
        if formatter is None:
            formatter = ExpandedIndentedHelpFormatter()
        OptionParser.__init__(self,
                              usage,
                              option_list,
                              option_class,
                              version,
                              conflict_handler,
                              description,
                              formatter,
                              add_help_option,
                              prog,
                              epilog)

    def _add_generate_config_file_option(self):
         self.add_option("--generate-config-file",
                         action='generate_config',
                         help=("Generate a config file on standard out."))

    def generate_and_print_config_file(self):
        """Generate a config file.
        """
        for grp in self.option_groups:
            print "[%s]" % grp.title
            for opt in grp.option_list:
                print "%s = %s" % (opt.dest, opt.default)
            print

    def _populate_option_list(self, option_list, add_help=True):
        OptionParser._populate_option_list(self, option_list, add_help)
        self._add_generate_config_file_option()

    def read_config_files(self, file_or_files):

        self.config_file_vars = SafeConfigParser()
        self.config_file_vars.read(file_or_files)

    def _get_config_value(self, section, option):
        if self.config_file_vars.has_section(section) and \
                self.config_file_vars.has_option(section, option):
            return self.config_file_vars.get(section, option)
        else:
            return None



if __name__ == '__main__':
    appname = 'agent-example'

    cfgmgr = ConfigManager()
    cfgmgr.read_config_files(['/etc/%s/agent.conf' % (appname,),
                             os.path.expanduser('~/.%s.cfg' % appname)])

    daemonGroup = ConfigGroup(cfgmgr, "Daemon", "Settings for running as a daemon.")
    daemonGroup.add_option('-p', '--pidfile', envvar="CFGMGR_PIDFILE",
                           help="The location to use for the pid file. [environment: %envvar, default: %default]",
                           default="/var/run/%s.pid" % (appname,))
    daemonGroup.add_option( '--stdin',
                           help="Stdin file descriptor for the daemon. [default: %default]",
                           default="/dev/null")
    daemonGroup.add_option( '--stdout',
                           help="Stdout file descriptor for the daemon. [default: %default]",
                           default="/dev/null")
    daemonGroup.add_option( '--stderr',
                           help="Stderr file descriptor for the daemon. [default: %default]",
                           default="/dev/null")


    logGroup = ConfigGroup(cfgmgr, "Log", "Log settings.")
    logGroup.add_option('-l', '--logfile', envvar="CFGMGR_LOGFILE",
                           help="The location to use for the log file. [environment: %envvar, default: %default]",
                           default="/var/log/%s.log" % (appname,))
    logGroup.add_option( '--loglevel',
                           help="Log level for the daemon. [default: %default]",
                           default="warn")


    stompGroup = ConfigGroup(cfgmgr, "Stomp", "Stomp connection settings.")
    stompGroup.add_option( '--server',
                           help="Address to use to connect to the Stomp server.[default: %default]",
                           default="localhost")
    stompGroup.add_option( '--port',
                           help="Port to use to connect to the Stomp server.[default: %default]",
                           default="61613")
    stompGroup.add_option( '--user',
                           help="Username to use to connect to the Stomp server.Log level for the daemon. [default: %default]",
                           default="")
    stompGroup.add_option( '--password',
                           help="Password to use to connect to the Stomp server. [default: %default]",
                           default="")


    cfgmgr.add_option_group(daemonGroup)
    cfgmgr.add_option_group(logGroup)
    cfgmgr.add_option_group(stompGroup)

    print cfgmgr.parse_args()
    print "Done."
