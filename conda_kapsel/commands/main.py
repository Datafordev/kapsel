# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2016, Continuum Analytics, Inc. All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# ----------------------------------------------------------------------------
"""The ``main`` function chooses and runs a subcommand."""
from __future__ import absolute_import, print_function

import os
import sys
from argparse import ArgumentParser, REMAINDER

from conda_kapsel.commands.prepare_with_mode import (UI_MODE_TEXT_ASK_QUESTIONS,
                                                     UI_MODE_TEXT_DEVELOPMENT_DEFAULTS_OR_ASK, _all_ui_modes)
from conda_kapsel.version import version
from conda_kapsel.project import ALL_COMMAND_TYPES
from conda_kapsel.plugins.registry import PluginRegistry
from conda_kapsel.plugins.requirements.download import _hash_algorithms
import conda_kapsel
import conda_kapsel.commands.init as init
import conda_kapsel.commands.run as run
import conda_kapsel.commands.prepare as prepare
import conda_kapsel.commands.clean as clean
import conda_kapsel.commands.archive as archive
import conda_kapsel.commands.upload as upload
import conda_kapsel.commands.activate as activate
import conda_kapsel.commands.variable_commands as variable_commands
import conda_kapsel.commands.download_commands as download_commands
import conda_kapsel.commands.service_commands as service_commands
import conda_kapsel.commands.environment_commands as environment_commands
import conda_kapsel.commands.command_commands as command_commands


def _parse_args_and_run_subcommand(argv):
    parser = ArgumentParser(prog="conda-kapsel", description="Actions on kapsels (runnable projects).")

    # future: make setup.py store our version in a version.py then use that here
    # parser.add_argument('-v', '--version', action='version', version='0.1')

    subparsers = parser.add_subparsers(help="Sub-commands")

    parser.add_argument('-v', '--version', action='version', version=version)

    def add_directory_arg(preset):
        preset.add_argument('--directory',
                            metavar='PROJECT_DIR',
                            default='.',
                            help="Project directory containing kapsel.yml (defaults to current directory)")

    def add_env_spec_arg(preset):
        preset.add_argument('--env-spec',
                            metavar='ENVIRONMENT_SPEC_NAME',
                            default=None,
                            action='store',
                            help="An environment spec name from kapsel.yml")

    def add_prepare_args(preset):
        add_directory_arg(preset)
        add_env_spec_arg(preset)
        all_supported_modes = list(_all_ui_modes)
        # we don't support "ask about every single thing" mode yet.
        all_supported_modes.remove(UI_MODE_TEXT_ASK_QUESTIONS)
        preset.add_argument('--mode',
                            metavar='MODE',
                            default=UI_MODE_TEXT_DEVELOPMENT_DEFAULTS_OR_ASK,
                            choices=_all_ui_modes,
                            action='store',
                            help="One of " + ", ".join(_all_ui_modes))

    def add_env_spec_name_arg(preset):
        preset.add_argument('-n',
                            '--name',
                            metavar='ENVIRONMENT_SPEC_NAME',
                            action='store',
                            help="Name of the environment spec from kapsel.yml")

    preset = subparsers.add_parser('init', help="Initialize a directory with default project configuration")
    add_directory_arg(preset)
    preset.set_defaults(main=init.main)

    preset = subparsers.add_parser('run', help="Run the project, setting up requirements first")
    add_prepare_args(preset)
    preset.add_argument('command',
                        metavar='COMMAND_NAME',
                        default=None,
                        nargs='?',
                        help="A command name from kapsel.yml")
    preset.add_argument('extra_args_for_command', metavar='EXTRA_ARGS_FOR_COMMAND', default=None, nargs=REMAINDER)
    preset.set_defaults(main=run.main)

    preset = subparsers.add_parser('prepare', help="Set up the project requirements, but does not run the project")
    add_prepare_args(preset)
    preset.set_defaults(main=prepare.main)

    preset = subparsers.add_parser('clean',
                                   help="Removes generated state (stops services, deletes environment files, etc)")
    add_directory_arg(preset)
    preset.set_defaults(main=clean.main)

    if not conda_kapsel._beta_test_mode:
        preset = subparsers.add_parser('activate',
                                       help="Set up the project and output shell export commands reflecting the setup")
        add_prepare_args(preset)
        preset.set_defaults(main=activate.main)

    preset = subparsers.add_parser('archive',
                                   help="Create a .zip, .tar.gz, or .tar.bz2 archive with project files in it")
    add_directory_arg(preset)
    preset.add_argument('filename', metavar='ARCHIVE_FILENAME')
    preset.set_defaults(main=archive.main)

    preset = subparsers.add_parser('upload', help="Upload the project to Anaconda Cloud")
    add_directory_arg(preset)
    preset.add_argument('-s', '--site', metavar='SITE', help='Select site to use')
    preset.add_argument('-t', '--token', metavar='TOKEN', help='Auth token or a path to a file containing a token')
    preset.add_argument('-u', '--user', metavar='USERNAME', help='User account, defaults to the current user')
    preset.set_defaults(main=upload.main)

    preset = subparsers.add_parser('add-variable', help="Add a required environment variable to the project")
    preset.add_argument('vars_to_add', metavar='VARS_TO_ADD', default=None, nargs=REMAINDER)
    preset.add_argument('--default',
                        metavar='DEFAULT_VALUE',
                        default=None,
                        help='Default value if environment variable is unset')
    add_directory_arg(preset)
    preset.set_defaults(main=variable_commands.main_add)

    preset = subparsers.add_parser('remove-variable', help="Remove an environment variable from the project")
    add_directory_arg(preset)
    preset.add_argument('vars_to_remove', metavar='VARS_TO_REMOVE', default=None, nargs=REMAINDER)
    preset.set_defaults(main=variable_commands.main_remove)

    preset = subparsers.add_parser('list-variables', help="List all variables on the project")
    add_directory_arg(preset)
    preset.set_defaults(main=variable_commands.main_list)

    preset = subparsers.add_parser('set-variable', help="Set an environment variable value in kapsel-local.yml")
    preset.add_argument('vars_and_values', metavar='VARS_AND_VALUES', default=None, nargs=REMAINDER)
    add_directory_arg(preset)
    preset.set_defaults(main=variable_commands.main_set)

    preset = subparsers.add_parser('unset-variable', help="Unset an environment variable value from kapsel-local.yml")
    add_directory_arg(preset)
    preset.add_argument('vars_to_unset', metavar='VARS_TO_UNSET', default=None, nargs=REMAINDER)
    preset.set_defaults(main=variable_commands.main_unset)

    preset = subparsers.add_parser('add-download', help="Add a URL to be downloaded before running commands")
    add_directory_arg(preset)
    preset.add_argument('filename_variable', metavar='ENV_VAR_FOR_FILENAME', default=None)
    preset.add_argument('download_url', metavar='DOWNLOAD_URL', default=None)
    preset.add_argument('--filename', help="The name to give the file/folder after downloading it", default=None)
    preset.add_argument('--hash-algorithm',
                        help="Defines which hash algorithm to use",
                        default=None,
                        choices=_hash_algorithms)
    preset.add_argument('--hash-value', help="The expected checksum hash of the downloaded file", default=None)
    preset.set_defaults(main=download_commands.main_add)

    preset = subparsers.add_parser('remove-download', help="Remove a download from the project and from the filesystem")
    add_directory_arg(preset)
    preset.add_argument('filename_variable', metavar='ENV_VAR_FOR_FILENAME', default=None)
    preset.set_defaults(main=download_commands.main_remove)

    preset = subparsers.add_parser('list-downloads', help="List all downloads on the project")
    add_directory_arg(preset)
    preset.set_defaults(main=download_commands.main_list)

    service_types = PluginRegistry().list_service_types()
    service_choices = list(map(lambda s: s.name, service_types))

    def add_service_variable_name(preset):
        preset.add_argument('--variable', metavar='ENV_VAR_FOR_SERVICE_ADDRESS', default=None)

    preset = subparsers.add_parser('add-service', help="Add a service to be available before running commands")
    add_directory_arg(preset)
    add_service_variable_name(preset)
    preset.add_argument('service_type', metavar='SERVICE_TYPE', default=None, choices=service_choices)
    preset.set_defaults(main=service_commands.main_add)

    preset = subparsers.add_parser('remove-service', help="Remove a service from the project")
    add_directory_arg(preset)
    preset.add_argument('variable', metavar='SERVICE_REFERENCE', default=None)
    preset.set_defaults(main=service_commands.main_remove)

    preset = subparsers.add_parser('list-services', help="List services present in the project")
    add_directory_arg(preset)
    preset.set_defaults(main=service_commands.main_list)

    def add_package_args(preset):
        preset.add_argument('-c',
                            '--channel',
                            metavar='CHANNEL',
                            action='append',
                            help='Channel to search for packages')
        preset.add_argument('packages', metavar='PACKAGES', default=None, nargs=REMAINDER)

    preset = subparsers.add_parser('add-env-spec', help="Add a new environment spec to the project")
    add_directory_arg(preset)
    add_package_args(preset)
    add_env_spec_name_arg(preset)
    preset.set_defaults(main=environment_commands.main_add)

    preset = subparsers.add_parser('remove-env-spec', help="Remove an environment spec from the project")
    add_directory_arg(preset)
    add_env_spec_name_arg(preset)
    preset.set_defaults(main=environment_commands.main_remove)

    preset = subparsers.add_parser('list-env-specs', help="List all environment specs for the project")
    add_directory_arg(preset)
    preset.set_defaults(main=environment_commands.main_list_env_specs)

    preset = subparsers.add_parser('add-packages', help="Add packages to one or all project environments")
    add_directory_arg(preset)
    add_env_spec_arg(preset)
    add_package_args(preset)
    preset.set_defaults(main=environment_commands.main_add_packages)

    preset = subparsers.add_parser('remove-packages', help="Remove packages from one or all project environments")
    add_directory_arg(preset)
    add_env_spec_arg(preset)
    preset.add_argument('packages', metavar='PACKAGE_NAME', default=None, nargs='+')
    preset.set_defaults(main=environment_commands.main_remove_packages)

    preset = subparsers.add_parser('list-packages', help="List packages for an environment on the project")
    add_directory_arg(preset)
    add_env_spec_arg(preset)
    preset.set_defaults(main=environment_commands.main_list_packages)

    def add_command_name_arg(preset):
        preset.add_argument('name', metavar="NAME", help="Command name used to invoke it")

    preset = subparsers.add_parser('add-command', help="Add a new command to the project")
    add_directory_arg(preset)
    command_choices = list(ALL_COMMAND_TYPES) + ['ask']
    command_choices.remove("conda_app_entry")  # conda_app_entry is sort of silly and may go away
    preset.add_argument('--type', action="store", choices=command_choices, help="Command type to add")
    add_command_name_arg(preset)
    add_env_spec_arg(preset)
    preset.add_argument('command', metavar="COMMAND", help="Command line or app filename to add")
    preset.set_defaults(main=command_commands.main)

    preset = subparsers.add_parser('remove-command', help="Remove a command from the project")
    add_directory_arg(preset)
    add_command_name_arg(preset)
    preset.set_defaults(main=command_commands.main_remove)

    preset = subparsers.add_parser('list-commands', help="List the commands on the project")
    add_directory_arg(preset)
    preset.set_defaults(main=command_commands.main_list)

    # argparse doesn't do this for us for whatever reason
    if len(argv) < 2:
        print("Must specify a subcommand.", file=sys.stderr)
        parser.print_usage(file=sys.stderr)
        return 2  # argparse exits with 2 on bad args, copy that

    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as e:
        return e.code

    # '--directory' is used for all subcommands now, but may not be always
    if 'directory' in args:
        args.directory = os.path.abspath(args.directory)
    return args.main(args)


def main():
    """conda-kapsel command line tool Conda-style entry point.

    Conda expects us to take no args and return an exit code.
    """
    conda_kapsel._enter_beta_test_mode()
    return _parse_args_and_run_subcommand(sys.argv)
