#!/usr/bin/python
"""
Synchronize Unbound forward zones without reloading Unbound

This script synchronizes Unbound file and live forward zone config without
reloading the Unbound service. This script assumes that all zone forwards look
like the statement below and only have one IPv4 forward address.

    forward-zone:
       name: "domain.com"
       forward-addr: 128.66.0.1
"""

import logging
import logging.handlers
import os
import re
import subprocess
import sys

__author__ = "Mikal Sande"
__email__ = "mikal.sande@gmail.com"


#
# Variables
#
INPUT_FILES = [
    '/etc/unbound/conf.d/malwarezones.conf',
]
UNBOUND_CONTROL = '/usr/sbin/unbound-control'
INPUT_SELECTOR = r'(^name:|^forward-addr:)'
INPUT_VALIDATOR = r'.*\..*\. IN forward '
ZONES_ADDED = []
ZONES_REMOVED = []


#
# Functions
#
def loadfileconfig():
    """
    Load list of configured forward zones from file into an array.
    """
    zones = []
    for infile in INPUT_FILES:
        # read file into array
        rawinput = []
        with open(infile) as inputfile:
            rawinput = inputfile.readlines()
        inputfile.close()

        selectedinput = []
        for line in rawinput:
            # remove leading and trailing whitespace
            line = line.strip()

            # remove double quotes, "
            line = line.replace('"', '')

            # select the lines we need and extract
            # the second field
            if re.search(INPUT_SELECTOR, line):
                line = line.split(' ')
                line = line[1]
                selectedinput.append(line)


        # Merge two and two items into a list of tuples
        # put into zones
        iterator = iter(selectedinput)
        zones.extend(zip(iterator, iterator))

    return zones


def loadliveconfig():
    """
    Load list of configured forward zones from unbound-control into an array.
    """
    zones = []

    # load live config from unbound-control
    (out, err) = subprocess.Popen([UNBOUND_CONTROL, 'list_forwards'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).communicate()

    # exit if unbound-control returns an error
    if len(err) > 0:
        for split in err.splitlines():
            print split
        sys.exit(1)


    # do input validation
    for line in out.splitlines():
        if line is None:
            continue
        if re.search(INPUT_VALIDATOR, line):
            # split line into array
            line = line.split()

            # extract and clean fields
            domain = line[0].strip()
            domain = domain.strip('.')
            ipaddress = line[3].strip()

            # append tuple to array
            zones.append((domain, ipaddress))

    return zones


def compareconfigs(fileconfig, liveconfig):
    """
    Compare two lists of forwarded zones.
    """
    # Make sets from the input arrays
    file_set = set(fileconfig)
    unbound_set = set(liveconfig)

    # Set of forward zones to be added to live config
    zoneadd = file_set.difference(unbound_set)

    # Set of forward zones to be removed from live config
    zoneremove = unbound_set.difference(file_set)

    return (zoneadd, zoneremove)


def addforwards(zoneadd):
    """
    Call unbound-control to add a forward zone to live config
    """
    for zone in zoneadd:
        os.system('{0} forward_add {1} {2} > /dev/null 2>&1'.format(
            UNBOUND_CONTROL, zone[0], zone[1]))
        ZONES_ADDED.append(zone)


def removeforwards(zoneremove):
    """
    Call unbound-control to remove a forwarded zone from live config
    """
    for zone in zoneremove:
        os.system('{0} forward_remove {1} > /dev/null 2>&1'.format(
            UNBOUND_CONTROL, zone[0]))
        ZONES_REMOVED.append(zone)

#
# Main
#
if __name__ == "__main__":
    # Load live config and file config
    FILE_ZONES = loadfileconfig()
    UNBOUND_ZONES = loadliveconfig()

    # Compare file config with live config and get two sets of zones back
    (ZONE_ADD, ZONE_REMOVE) = compareconfigs(FILE_ZONES, UNBOUND_ZONES)

    # Add forward zones to live config
    addforwards(ZONE_ADD)

    # Remove forward zones from live config
    removeforwards(ZONE_REMOVE)

    # Reload live config
    UNBOUND_ZONES = loadliveconfig()

    # Compare file config with live config on more time
    (ZONE_ADD, ZONE_REMOVE) = compareconfigs(FILE_ZONES, UNBOUND_ZONES)

    # Print to stdout and syslog if there is a difference between them
    if len(ZONE_ADD) > 0 or len(ZONE_REMOVE) > 0:
        MESSAGE = """unbound_reload_forwards.py: There is difference between file and
                     live config! This should not happen!"""
        print MESSAGE

        HANLDER = logging.handlers.SysLogHandler(address='/dev/log')
        LOGGER = logging.getLogger('unbound-fix-forwards.py')
        LOGGER.addHandler(HANLDER)

        LOGGER.critical(MESSAGE)

    # Print status if run interactively
    if os.isatty(sys.stdout.fileno()):
        if len(ZONES_ADDED) > 0:
            print "Added:"
            for x in ZONES_ADDED:
                print "  {0}".format(x)

        if len(ZONES_REMOVED) > 0:
            print
            print "Removed:"
            for x in ZONES_REMOVED:
                print "  {0}".format(x)
