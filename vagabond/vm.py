#!/usr/bin/env python
import os
import re
import sys
import subprocess
import logging

# Set up Module Logging
# TODO:  Read this https://docs.python.org/2/howto/logging-cookbook.html
L = logging.getLogger(__name__)
L.setLevel(logging.DEBUG)

FORMAT='%(asctime)s - %(levelname)s - %(message)s'
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)

L.addHandler(ch)

class VBoxManageError(ValueError):
    """
        A generic error for VBoxManager errors
    """
    pass

class VM(object):
    def __init__(self, options, *args, **kwargs):
        self.config = options.config
        self.args = kwargs.get('args')
        self.force = self.args.force
        
        self.vm_name = self.config.get('vmname', "ubuntu-64bit")

    def up(self):
        # Check for Vagabond.py file
        _file = os.path.join(os.getcwd(), "Vagabond.py")
        if not os.path.isfile(_file):
            L.error("No Vagabond.py file found.  Is this is this a vagabond project?")
            sys.exit(0)
      
        media = self.config.get('media')
        if not media:
            raise ValueError("No media specified in Vagabond.py file")
        
        if media.get('iso'):
            self.iso_up()
        elif media.get('vmdx'):
            raise Exception("vmdx media type not supported yet")
        elif media.get('vdi'):
            raise Exception("vdi media type not supported yet")

    
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
                out = subprocess.check_output(args, stderr=f)
                L.info("subprocess:"+str(out))
            
            # sometimes subprocess exits cleanly, but VBoxManage still throws an error...
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

    def createhd(self):
        try:
            size = self.config['hdd']['size']
        except KeyError:
            size = '32768'
        
        # Create the virtual hard drive
        try:   
            self.vbox('VBoxManage', 'createhd','--filename', '%s.vdi'%self.vm_name,'--size', size,)
        except VBoxManageError as e:
            if "Could not create the medium storage unit" in str(e):
                if self.args.force:
                    L.error(str(e))
                    out = re.findall(r'Could not create the medium storage unit([^(]*)\\n', str(e))[0]
                    out = out.strip().replace("'","")
                    while out[-1] == '.':     
                        out = out[:-1]

                    if os.path.isfile(out) and out.endswith('.vdi'):
                        L.info("force=True.  Removing %s"%out)
                        os.unlink(out)
                        try:
                            L.info("Force=True, Rerunning")
                            self.vbox('VBoxManage', 'createhd','--filename', '%s.vdi'%self.vm_name,'--size', size,)
                        except VBoxManageError as e:
                            L.error(str(e))
                            sys.exit(0)
                elif 'VERR_ALREADY_EXISTS' in str(e):
                    
                    raise e
                    L.error(str(e))
                    sys.exit(0)

    def createvm(self):
        # Set the ostype.  Must be from the list shown in: VBoxManage list ostypes
        ostype = 'Ubuntu_64' if not self.config.get('ostype') else self.config['ostype']

        # Create the Virtual Machines
        try:
            self.vbox('VBoxManage', 'createvm','--name', self.vm_name, '--ostype', ostype ,'--register')
        except VBoxManageError as e:
            L.error(str(e))
            if "Machine settings file" in str(e) and "already exists" in str(e):
                if self.args.force:
                    out = re.findall(r'Machine settings file([^(]*)already exists', str(e))[0]
                    out = out.strip().replace("'","")
                    while out[-1] == '.':       
                        out = out[:-1]
                    if os.path.isfile(out) and out.endswith('.vbox'):
                        L.info("force=True.  Removing %s"%out)
                        os.unlink(out)
                        try:
                            L.info("Force=True, Rerunning")
                            self.vbox('VBoxManage', 'createvm','--name', self.vm_name, '--ostype', ostype ,'--register')
                        except VBoxManageError as e:
                            L.error(str(e))
                            sys.exit(0)
                else:
                    L.error(str(e))
                    sys.exit(0)

            if "Guest OS type" in str(e) and "is invalid" in str(e):
                L.error("In valid ostype")
                L.error("run: vagabond list ostypes")
                sys.exit(0)
        
     
    def iso_up(self):
        """
            Creating a VM from an ISO image
            http://www.perkin.org.uk/posts/create-virtualbox-vm-from-the-command-line.html
        """
        try:
            size = self.config['hdd']['size']
        except KeyError:
            size = '32768'


        # This is a --hard-force switch....dirty, but works for cleaning it all up
        if self.args.hard_force:
            self.unregistervm()

        self.createhd()

        self.createvm()

        for _ in [True]:
            try:
                self.vbox('VBoxManage', 'storagectl', self.vm_name, 
                    '--name', "SATA Controller", 
                    '--add', 'sata', 
                    '--controller', 'IntelAHCI'
                )
            except VBoxManageError as e:
                if "Storage controller named" in str(e) and "already exists" in str(e):
                    if self.args.force:
                        L.error(str(e))
                        L.info("--force.  Using currently existing controller")
                        break
                    else:
                        L.error(str(e))
                        sys.exit(0)
                else:
                    L.error(str(e))
                    sys.exit(0)

           
        for _ in [True]:
            try:
                self.vbox('VBoxManage', 'storageattach', self.vm_name,
                    '--storagectl', "SATA Controller",
                    '--port', '0',
                    '--device', '0',
                    '--type', 'hdd',
                    '--medium', '%s.vdi'%(self.vm_name),
                )
            except VBoxManageError as e:
                self.unregister()
                raise e 

        for _ in [True]:
            try:
                self.vbox('VBoxManage', 'modifyvm', self.vm_name,
                    '--ioapic', 'on'
                )
                self.vbox('VBoxManage', 'modifyvm', self.vm_name, 
                    '--memory', '1024',
                    '--vram', '128'
                )
                self.vbox('VBoxManage', 'storagectl', self.vm_name,
                    '--name', "IDE Controller",
                    '--add', 'ide'
                )
                self.vbox('VBoxManage', 'storageattach', self.vm_name,
                    '--storagectl', "IDE Controller",
                    '--port', '0',
                    '--device', '0',
                    '--type', 'dvddrive',
                    '--medium', self.config['media']['iso']
                )
                #self.vbox('VBoxManage', 'modifyvm', self.vm_name,
                #    '--nic1', 'bridged',
                #    #' --bridgeadapter1', 'e1000g0'
                #)
            except VBoxManageError as e:
                L.error(str(e))
                sys.exit(0)

        ## Finally start the machien up.
        # NOTE Should you move this up above? 
        for _ in [True]:
            try:
                self.vbox('VBoxManage', 'startvm', self.vm_name)
            except VBoxManageError as e:
                L.error(str(e))
                sys.exit(0)

    def unregistervm(self, vm_name=None):
        """
            Unregister a vm.  name can be the UUID or the name of the vm
            NOTE:  If you pass it a name it will recusively delete all boxes with that name
        """
        if not vm_name:
            vm_name = self.vm_name

        L.info("unregistervm: " + self.vm_name)

        try:
            self.vbox('vboxmanage', 'unregistervm', vm_name)
        except VBoxManageError as e:
            if "Could not find a registered machine named '%s'"%self.vm_name in e:
                pass
