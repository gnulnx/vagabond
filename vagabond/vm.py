#!/usr/bin/env python
import os
import glob, os
import errno
import requests
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
    """ A generic error for VBoxManager errors """
    pass

class VagabondError(ValueError):
    """ A generic Vagabond specific error """
    pass

class VM(object):
    def __init__(self, options, *args, **kwargs):
        self.config = options.config
        self.args = kwargs.get('args')
          
        self.vm_name = self.config.get('vmname', "ubuntu-64bit")
       
        #if kwargs.get('destroy') or kwargs.get("halt"):
        #    self._set_project_dir()
        #else:

        try:
            self._create_project_dir()
        except VagabondError as e:
            self._set_project_dir()

    def _set_project_dir(self):
        # boxdir ~./vagabond/boxes
        boxdir = os.path.join(
            os.path.expanduser("~"),
            ".vagabond/boxes/",
        )

        # projdir ~/.vagabond/boxes/self.vm_name
        self.projdir = os.path.normpath(os.path.join(boxdir, self.vm_name))

    def _create_project_dir(self):
        """
            Create a new project directory or raise VagabondError
        """
        self._set_project_dir()

        if not os.path.isdir(self.projdir):
            os.makedirs(self.projdir)
        else:
            
            if not self.args.__dict__.get('force', False):
                L.error("Project directory(%s) already exists.  Use --force to ignore this warning" % self.projdir)
                raise VagabondError("Project dir(%s) already exists" % self.projdir)

    @staticmethod
    def download(link, file_name):
        """
            Uses the clint library to show a download progress bar for downloads
        """
        from clint.textui import progress
        L.info("downloading: " + link)
        r = requests.get(link, stream=True)
        with open(file_name, 'wb') as f:
            total_length = int(r.headers.get('content-length'))
            for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1): 
                if chunk:
                    f.write(chunk)
                    f.flush()

        return r

    @staticmethod
    def addbox(args):
        boxdir = os.path.join(
            os.path.expanduser("~"),
            ".vagabond/boxes/",
        )
        if args.loc.startswith("http://") and args.loc.endswith(".box"):
            # the vagabond project directory typically ~/.vagrant/boxes/args.name
            projdir = os.path.normpath(os.path.join(boxdir, args.name))
            try:
                os.makedirs(projdir)
            except OSError as e:
                if errno.errorcode[e.errno] != 'EEXIST':
                    raise

            download_fname = os.path.join(projdir, args.name)

            r = VM.download(args.loc, download_fname)
            if r.status_code == 200:        
                # save current location
                hold = os.getcwd() 
                
                os.chdir(projdir)
    
                # uncompress the downloaded files
                subprocess.check_output(['tar', 'xvfz', download_fname])

                # Remove any vagrant related files.
                for _file in glob.glob("Vagrant*"):
                    os.remove(_file)
                
                # Now remove the downloaded file
                os.remove(download_fname) 
                
                # return to previous directory
                os.chdir(hold)
            else:
                raise ValueError("status_code: " + r.status_code)
    
    def listvms(self):
        out = self.vbox('VBoxManage', 'list', 'vms')

        outDict = {}
        for line in out.split("\n"):
            if line:
                (name, UUID) = line.split()
                outDict[name.replace('"','')] = UUID
       
        return outDict

    def up(self):
        # Check for Vagabond.py file
        _file = os.path.join(os.getcwd(), "Vagabond.py")
        if not os.path.isfile(_file):
            L.error("No Vagabond.py file found.  Is this is this a vagabond project?")
            sys.exit(0)
      
        media = self.config.get('media')
        if not media:
            raise ValueError("No media specified in Vagabond.py file")
       

        if self.vm_name in self.listvms():
            self.startvm()
        elif media.get('iso'):
            self.iso_up()
        elif media.get('vmdx'):
            raise Exception("vmdx media type not supported yet")
        elif media.get('vdi'):
            raise Exception("vdi media type not supported yet")

    
    def _check_vbox_errors(self, err_log, args=None):
        """
            Check for errors and raise VBoxManageError
            *Compiles a list of VBoxManage: error: 
        """
        if not os.path.isfile(err_log):
            return None

        with open(err_log, 'r') as f:
            tmp_error = f.readlines()
            
        errors = []
        for line in tmp_error:
            if "VBoxManage: error: " in line:
                errors.append(line)

        if errors:  
            os.unlink(err_log)
            # Log the command that failed
            L.error(" ".join(args))
            raise VBoxManageError(errors)

        return None
      
    def vbox(self, *args):
        """
            Pass in a list of command/args to call VBoxManage.  We use subprocess to
            write to stderr to a file. On subprocess.CalledProcessError we read in the error
            file and raise a VBoxManageError with the contents of the file as the message
        """
        err_log=".vagabond.error.log"
        try:
            L.info(" ".join(args))
            out = ''
            with open(err_log, 'w') as f:
                out = subprocess.check_output(args, stderr=f)
                if out:
                    L.info("cmd out:"+str(out))
            
            # sometimes subprocess exits cleanly, but VBoxManage still throws an error...
            self._check_vbox_errors(err_log, args)
            return out
        except subprocess.CalledProcessError as e:
            # Log an error containing the failed command.
            self._check_vbox_errors(err_log, args)

            # Probably won't get here
            raise

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

        # TODO File name needs to be in a better location...like .vagabond/boxes/self.vm_name
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
       
    def addSATA(self):
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

        self.addSATA()
           
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

        self.startvm()
        
    def startvm(self, vm_name=None):
        ## Finally start the machien up.
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
            self.vbox('VBoxManage', 'unregistervm', vm_name, "--delete")
        except VBoxManageError as e:
            if "Could not find a registered machine named '%s'"%self.vm_name in e:
                pass

        
        # Now remove the Vagabond Project directory
        if os.path.isdir(self.projdir):
            L.info("rmdir(%s)" % self.projdir)
            os.rmdir(self.projdir)



