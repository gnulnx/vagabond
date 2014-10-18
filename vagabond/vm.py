#!/usr/bin/env python
import os
import sys
import argparse
import subprocess
import errno
import logging
#from django.template import Context, Template
#from django.conf import settings
#settings.configure()

# Set up Module Logging
# TODO:  Read this https://docs.python.org/2/howto/logging-cookbook.html
L = logging.getLogger(__name__)
L.setLevel(logging.DEBUG)

FORMAT='%(asctime)s - %(levelname)s - %(message)s'
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# add formatter to ch

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)

L.addHandler(ch)

class VBoxManageError(ValueError):
    """
        A generic error for VBoxManager errors
    """

class VM(object):
    def __init__(self, options, *args, **kwargs):
        self.config = options.config

    def up(self):
        # Check for Vagabond.py file
        _file = os.path.join(os.getcwd(), "Vagabond.py")
        if not os.path.isfile(_file):
            L.error("No Vagabond.py file found.  Is this is this a vagabond project?")
            sys.exit(0)
       
        hostname = self.config.get('hostname', 'vagabond')
  
        count = 0
        for media, value in self.config['media'].items():    
            if value:
                media_type = media
                media_val = value
                count = count + 1
            
        if count > 1:
            L.info("You may only define one media type in %s" % self.config['media'].keys())
            sys.exit(0)

        if media_type == 'iso':
            self.iso_up()
    
      
    def vbox(self, *args):
        err_log=".vagabond.error.log"
        try:
            L.info(" ".join(args))
            with open(err_log, 'w') as f:
                out = subprocess.check_output(args, stderr=f)
        except subprocess.CalledProcessError as e:
            """
                The VBoxManage error was written to .error.log
                We read it in and give the user feedback
            """
            # Log an error containing the failed command.
            L.error(" ".join(args))

            with open(err_log, 'r') as f:
                lines = f.readlines()

            for l in lines:
                if "Machine settings file" in l  \
                and "already exists" in l:
                    L.error(str(lines))
                    L.error(l)
                    L.error("Please try removing the box")

            # If you made it here raise a VBoxManageError
            raise VBoxManageError(unicode(e))

        # remove the temp logfile
        os.unlink(err_log)
 
    def iso_up(self):
        """
            Creating the VM from an ISO image
            http://www.perkin.org.uk/posts/create-virtualbox-vm-from-the-command-line.html
        """
        VM="ubuntu-64bit"
        # Create the Harddrive
        self.vbox('VBoxManage', 'createhd','--filename', '%s.vdi'%VM,'--size', '32768',)

        # Create the Virtual Machines
        self.vbox('VBoxManage', 'createvm','--name', VM, '--ostype', 'Ubuntu_64','--register')
        print "after vbox call"
        raw_input()

        raise Exception("Lets' build a machine from scratch")

