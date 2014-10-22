#!/usr/bin/env python
import os
import shutil
import time
import glob, os
import errno
import requests
import re
import sys
import subprocess
import logging
import logging.config

from vagabond.logger.logger import get_logger

L = get_logger()

from vagabond.version import API_VERSION

class VBoxManageError(ValueError):
    """ A generic error for VBoxManager errors """
    pass

class VagabondError(ValueError):
    """ A generic Vagabond specific error """
    pass


class VM(object):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
   
        self.setup_proj() 
        

        L.debug("VM.__init__  kwargs(%s): ", self.kwargs)
        action = self.kwargs.get('subparser_name')

        if action == 'init':
            self.init()
        elif action == 'up':
            self.up()
        elif action == 'halt':
            self.halt()
        elif action == 'destroy':
            self.halt()
            self.unregistervm()
        elif action == 'box':
            # I kinda feel like this sub logix should be factored out...Box class maybe?
            subaction = self.kwargs.get('box_subparser_name')
            if subaction == 'add':
                self.addbox()
            else:
                L.debug(self.kwargs)
                raise Exception("No sub action found")
        else:
            L.critical("action (%s) not defined")
            raise VagabondError("action (%s) not defined")
        
        return

    def setup_proj(self):
        """
            Takes care of setting up vagabond for the first time.
            A single project directory is created in the users home directory with the following structure
            ~/.vagabond/boxes/

            Inside these boxes will sub subdirectories for each imported box.  This method also 
            initializes a few instance variables:
            
            VAGABOND_ROOT:  typically ~/.vagabond
            VAGABOND_BOX_ROOT:  VAGABOND_PROJECT_ROOT/boxes
        """
        self.TEST = self.kwargs.get('TEST')
        if self.TEST:
            self.VAGABOND_ROOT=os.path.join(os.path.abspath("."), ".vagabond/")
        else:
            self.VAGABOND_ROOT=os.path.join(os.path.expanduser("~"), ".vagabond/")

        L.info("TEST(%s) - VAGABOND_ROOT(%s)", self.TEST, self.VAGABOND_ROOT)

        try:
            self.VAGABOND_BOX_ROOT = os.path.join(self.VAGABOND_ROOT, "boxes")
            os.makedirs(self.VAGABOND_BOX_ROOT)
        except OSError as e:
            if errno.errorcode[e.errno] == 'EEXIST':
                L.debug("%s already exists", self.VAGABOND_BOX_ROOT)
            else:
                raise

    def init(self):
        """
            Initialize a project by:
            1)  Create a direction (args.name)
            2)  Use template to create initial Vagabond.py file
        """

        self.hostname = self.kwargs.get('project-name')
        L.info("self.hostname: %s", self.hostname)

        self.PROJECT_DIR = os.path.abspath(self.hostname)     
        L.info("PROJECT_DIR: %s", self.PROJECT_DIR)

        force = self.kwargs.get('force')

        if not os.path.isdir(self.PROJECT_DIR):
            os.mkdir(self.PROJECT_DIR)
        else:
            if force:
                L.warn("Removing %s and all contents because you passed --force", self.PROJECT_DIR)
                shutil.rmtree(self.PROJECT_DIR)
                os.mkdir(self.PROJECT_DIR)
            else:
                L.critical("Directory (%s) already exists.  --force to remove and recreate", self.hostname)
                if self.TEST:
                    raise VagabondError("Directory (%s) already exists.  --force to remove and recreate", self.hostname)
                sys.exit(0)
                
                
        iso = self.kwargs.get('iso')
        if iso:
            iso = os.path.abspath(os.path.expanduser(iso))
        box = self.kwargs.get('box', 'hashicopy/precise64')

        if iso:
            box = None
            if not iso.endswith(".iso"):
                L.warn("ISO (%s) does not have a .iso extension")
        
        # Import the VagabondTemplate and apply our context to it.
        from vagabond.templates import VagabondTemplate
        vfile = os.path.join( os.path.abspath(self.hostname), "Vagabond.py") 
        with open(vfile, 'w') as f:
            f.write( VagabondTemplate.render({
                'version':API_VERSION,
                'hostname':self.hostname,
                'box':box,
                'iso':iso,
            }))

        # TODO:  Do we really want a retun status code type thing?
        self.RET = {'STATUS':'SUCCESS'}


    def _set_project_dir(self):
        # boxdir ~./vagabond/boxes
        boxdir = os.path.join(
            os.path.expanduser("~"),
            ".vagabond/boxes/",
        )

        # projdir ~/.vagabond/boxes/self.hostname
        self.projdir = os.path.normpath(os.path.join(boxdir, self.hostname))


    def download(self, link, file_name):
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

    def addbox(self):
        self.RET = {}
        self.loc = self.kwargs['loc']
        self.box_name = self.kwargs['name']
        L.info("Adding box %s",self.loc)

        # First make sure the box directory is present
        self.VAGABOND_PROJECT_ROOT = os.path.normpath(os.path.join(self.VAGABOND_BOX_ROOT, self.box_name))
        try:
            os.makedirs(self.VAGABOND_PROJECT_ROOT)
        except OSError as e:
            if errno.errorcode[e.errno] != 'EEXIST':
                L.warn("Box directory (%s) already present", self.VAGABOND_PROJECT_ROOT)
                raise

        L.info("VAGABOND_PROJECT_ROOT: %s", self.VAGABOND_PROJECT_ROOT)
            
        # Check if Vagrant *.box
        if self.loc.startswith("http://") and self.loc.endswith(".box"):

            download_fname = os.path.join(self.VAGABOND_PROJECT_ROOT, self.box_name)
            L.info("download_fname: %s", download_fname)

            r = self.download(self.loc, download_fname)
            if r.status_code == 200:        
                # save current location
                hold = os.getcwd() 
                
                os.chdir(self.VAGABOND_PROJECT_ROOT)
    
                # uncompress the downloaded files
                subprocess.check_output(['tar', 'xvfz', download_fname])

                # Now remove the downloaded file
                L.error("You commented out the download_fname deletion")
                os.remove(download_fname) 
                
                # return to previous directory
                os.chdir(hold)

        self.RET = {
            'STATUS':'SUCCESS',
            'VAGABOND_PROJECT_ROOT':self.VAGABOND_PROJECT_ROOT,
        } 

    def listboxes(self):
        return os.listdir(self.VAGABOND_BOX_ROOT)

    def listvms(self):
        out = self.vbox('VBoxManage', 'list', 'vms')

        outDict = {}
        for line in out.split("\n"):
            if line:
                (name, UUID) = line.split()
                outDict[name.replace('"','')] = UUID
       
        return outDict

    def readVagabond(self):
        path = os.getcwd()
        # Check for Vagabond file in local directory
        vfile = os.path.join(path, "Vagabond.py")
        if not os.path.isfile(vfile):
            raise IOError("You must have a Vagabond file in your current directory")
    
        L.info("Vagabond.py: %s", vfile)

        # Add current directory to sys path...
        # so that when we load the Vagabond module it loads the users module
        sys.path.insert(0, path)

        import Vagabond
        reload(Vagabond)
        self.config_version = Vagabond.VAGABOND_API_VERSION
        L.debug("Importing Vagabond.VAGABOND_API_VERSION: %s", self.config_version)
        
        self.config = Vagabond.config
        self.vm = self.config['vm']
        self.hostname = self.vm.get('hostname', 'vagabond')
       
        print "self.vm: ", self.vm 
        self.media = os.path.expanduser(
            self.vm.get('box', 
                self.vm.get('iso', 
                    self.vm.get('vmdx')
                )
            )
        )

        return Vagabond

    def up(self):
        L.warn("up: %s", self.kwargs)
        
        # Sets self.config
        self.readVagabond()
        L.debug(self.media)
        if not self.hostname:
            raise VagabondError("You must have a hostname")

        if self.hostname in self.listboxes() \
        and self.hostname in self.listvms():
            self.startvm()
        elif self.media.endswith(".iso"):
            self.iso_up()
        else:
            raise Exception("media type (%s) not supported", self.media)
    
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
            # TODO Move this to a better spot in config...config['vm']['hdd'] perhaps?
            size = self.config['hdd']['size']
        except KeyError:
            size = '32768'

        # TODO File name needs to be in a better location...like .vagabond/boxes/self.hostname
        # Create the virtual hard drive
        try:   
            self.vbox('VBoxManage', 'createhd','--filename', '%s.vdi'%self.hostname,'--size', size,)
        except VBoxManageError as e:
            if "Could not create the medium storage unit" in str(e):
                if self.kwargs['force']:
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
                            vdi_path = os.path.join(self.PROJECT_ROOT, self.hostname)
                            self.vbox('VBoxManage', 'createhd','--filename', '%s.vdi'%vdi_path,'--size', size,)
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
            self.vbox('VBoxManage', 'createvm','--name', self.hostname, '--ostype', ostype ,'--register')
        except VBoxManageError as e:
            L.error(str(e))
            if "Machine settings file" in str(e) and "already exists" in str(e):
                if self.kwargs.get('force'):
                    out = re.findall(r'Machine settings file([^(]*)already exists', str(e))[0]
                    out = out.strip().replace("'","")
                    while out[-1] == '.':       
                        out = out[:-1]
                    if os.path.isfile(out) and out.endswith('.vbox'):
                        L.info("force=True.  Removing %s"%out)
                        os.unlink(out)
                        try:
                            L.info("Force=True, Rerunning")
                            self.vbox('VBoxManage', 'createvm','--name', self.hostname, '--ostype', ostype ,'--register')
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
                self.vbox('VBoxManage', 'storagectl', self.hostname, 
                    '--name', "SATA Controller", 
                    '--add', 'sata', 
                    '--controller', 'IntelAHCI'
                )
            except VBoxManageError as e:
                if "Storage controller named" in str(e) and "already exists" in str(e):
                    if self.kwargs.get('force'):
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
        

        ## Create the box directory
        self.BOX_ROOT = os.path.join(self.VAGABOND_BOX_ROOT, self.hostname) 
        try:
            os.makedirs(self.BOX_ROOT)
        except OSError as e:
            if "[Errno 17] File exists" in str(e):
                if self.kwargs.get('force'):
                    L.warn("vagabond project already exists")
                    pass
            else:
                raise e
        
        # This is a --hard-force switch....dirty, but works for cleaning it all up
        if self.kwargs.get('hard_force'):
            self.unregistervm()

        self.createhd()

        self.createvm()

        self.addSATA()
           
        for _ in [True]:
            try:
                self.vbox('VBoxManage', 'storageattach', self.hostname,
                    '--storagectl', "SATA Controller",
                    '--port', '0',
                    '--device', '0',
                    '--type', 'hdd',
                    '--medium', '%s.vdi'%(self.hostname),
                )
            except VBoxManageError as e:
                self.unregister()
                raise e 

        for _ in [True]:
            try:
                self.vbox('VBoxManage', 'modifyvm', self.hostname,
                    '--ioapic', 'on'
                )
                self.vbox('VBoxManage', 'modifyvm', self.hostname, 
                    '--memory', '1024',
                    '--vram', '128'
                )
                self.vbox('VBoxManage', 'storagectl', self.hostname,
                    '--name', "IDE Controller",
                    '--add', 'ide'
                )
                self.vbox('VBoxManage', 'storageattach', self.hostname,
                    '--storagectl', "IDE Controller",
                    '--port', '0',
                    '--device', '0',
                    '--type', 'dvddrive',
                    '--medium', self.media
                )
                #self.vbox('VBoxManage', 'modifyvm', self.hostname,
                #    '--nic1', 'bridged',
                #    #' --bridgeadapter1', 'e1000g0'
                #)
            except VBoxManageError as e:
                L.error("%s -- %s", self.media, str(e))
                sys.exit(0)

        self.startvm()
        
    def startvm(self, vm_name=None):
        ## Finally start the machien up.
        try:
            self.vbox('VBoxManage', 'startvm', self.hostname)
        except VBoxManageError as e:
            if "The machine 'jane' is already locked by a session (or being locked or unlocked)" in str(e):
                L.warning("Machine already running")
            else:
                raise

    def halt(self, vm_name=None):
        # This block is repeated in self.up()
        self.readVagabond()

        try:
            self.vbox('VBoxManage', 'controlvm', self.hostname, 'savestate')
        except VBoxManageError as e:
            if 'Machine in invalid state 1 -- powered off' in str(e):
                L.warn('Machine in invalid state 1 -- powered off')
            elif 'Machine in invalid state 2 -- saved' in str(e):
                L.warn('Machine in invalid state 2 -- saved')
            elif "Could not find a registered machine named '%s'"%self.hostname:
                L.warn("Could not find a registered machine named '%s'"%self.hostname)
            else:
                raise
    
    def unregistervm(self, count=0):
        """
            Unregister a vm.  name can be the UUID or the name of the vm
            NOTE:  If you pass it a name it will recusively delete all boxes with that name
        """
        if not self.hostname:
            # Third time this block is repeated
            VAGABOND = self.readVagabond()
            self.config = VAGABOND.config
            self.hostname = self.config.get('vmname', 'vagabond')

        self._set_project_dir()

        try:
            self.vbox('VBoxManage', 'unregistervm', self.hostname, "--delete")
        except VBoxManageError as e:
            if "Could not find a registered machine named '%s'"%self.hostname in str(e):
                pass
            elif "Cannot unregister the machine '%s' while it is locked"%self.hostname in str(e):
                L.error("Cannot unregister the machine '%s' while it is locked"%self.hostname)
                L.info("Trying again in 1 second")
                time.sleep(1)
                if count < 10:
                    self.unregistervm(count=count+1)
                else:
                    raise e
            else:
                raise

        
        # Now remove the Vagabond Project directory
        if os.path.isdir(self.projdir):
            L.info("Removing the project directory(%s)" % self.projdir)
            for _file in os.listdir(self.projdir):
                os.unlink(os.path.join(self.projdir, _file))

            os.rmdir(self.projdir)



