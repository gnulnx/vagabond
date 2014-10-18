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
    pass
    #def __init__(self, msg):
    #    self.msg = msg
    #def __str__(self):
    #    return repr(self.msg)

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
    
    def _check_vbox_errors(self, err_log, args=None):
        """
            Check for errors and raise VBoxManageError
        """
        errors = []

        if not os.path.isfile(err_log):
            return errors

        with open(err_log, 'r') as f:
            tmp_error = f.readlines()
            
        for line in tmp_error:
            if "VBoxManage: error: " in line:
                errors.append(line)

        if errors:  
            os.unlink(err_log)
            # Log the command that failed
            L.error(" ".join(args))
            raise VBoxManageError(errors)

        return errors
      
    def vbox(self, *args):
        """
            Pass in a list of command/args to call VBoxManage.  We use subprocess to
            write sterr to a file. On subprocess.CalledProcessError we read in the error
            file and raise a VBoxManageError with the contents of the file as the message
        """
        err_log=".vagabond.error.log"
        try:
            L.info(" ".join(args))
            with open(err_log, 'w') as f:
                subprocess.check_output(args, stderr=f)
            
            # sometimes subprocess exits cleanly, but VBoxManage still threw an error...
            errors = self._check_vbox_errors(err_log, args)
        except subprocess.CalledProcessError as e:
            # Log an error containing the failed command.
            errors = self._check_vbox_errors(err_log, args)

    @staticmethod
    def show_valid_os_types():
        cmd = "VBoxManage list -l ostypes".split()
        out = subprocess.check_output(cmd)
        valid_os = []
        for line in out.split("\n"):
            if "ID:" in line and "Family" not in line:
                os = line.split(":")[1].strip()
                valid_os.append(os)
                print os
        return valid_os
 
    def iso_up(self):
        """
            Creating the VM from an ISO image
            http://www.perkin.org.uk/posts/create-virtualbox-vm-from-the-command-line.html
        """
        VM="ubuntu-64bit"   
        try:
            size = self.config['hdd']['size']
        except KeyError:
            size = '32768'

        try:
            ostype = self.config['ostype']
        except KeyError:
            ostype = 'Ubuntu_64'

        # Create the Harddrive
        try:
            self.vbox('VBoxManage', 'createhd','--filename', '%s.vdi'%VM,'--size', size,)
        except VBoxManageError as e:
            if "Failed to create hard disk" in str(e):
                L.error(str(e))
                sys.exit(0)

        # Create the Virtual Machines
        try:
            self.vbox('VBoxManage', 'createvm','--name', VM, '--ostype', ostype ,'--register')
        except VBoxManageError as e:
            L.error(str(e))
            if "Machine settings file" in str(e) and "already exists" in str(e):
                sys.exit(0)
            if "Guest OS type" in str(e) and "is invalid" in str(e):
                L.error("In valid ostype")
                L.error("run: vagabond list ostypes")
                sys.exit(0)
                


