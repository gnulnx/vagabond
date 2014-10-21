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
        self.TEST = self.kwargs.get('TEST')
        self.VAGRANTBASE=os.path.expanduser("~")
        if self.TEST:
            self.VAGRANTBASE=os.path.abspath(".")

        self.VAGRANT_PROJECT_ROOT=os.path.join(os.path.expanduser("~"), ".vagabond/",)

        try:
            self.BOXDIR = os.path.join(self.VAGRANT_PROJECT_ROOT, "boxes")
            os.makedirs(self.BOXDIR)
        except OSError as e:
            if errno.errorcode[e.errno] == 'EEXIST':
                L.debug("%s already exists", self.BOXDIR)
            else:
                raise

    def init(self):
        """
            Initialize a project by:
            1)  Create a direction (args.name)
            2)  Use UPDATE_ME template to create initial Vagabond.py file
        """
        self.vm_name = self.kwargs.get('name')
        L.info("self.vm_name: %s", self.vm_name)

        force = self.kwargs.get('force')
        if force:
            L.info("--force option issued")

        # Try to create the machine directory...
        # This is the users project direct.
        self.machine_dir = os.path.abspath(self.vm_name)     
        if not os.path.isdir(self.machine_dir):
            os.mkdir(self.machine_dir)
        else:
            if force:
                L.warn("Removing %s and all contents because you passed --force", self.machine_dir)
                shutil.rmtree(self.machine_dir)
                os.mkdir(self.machine_dir)
            else:
                L.critical("Directory (%s) already exists.  --force to remove and recreate", self.vm_name)
                sys.exit(0)
                
         
        # Create the project directory    
        self._create_project_dir()

        media = self.kwargs.get('media')

        # TODO This is for debug only
        if not media:
            media="/Users/jfurr/Downloads/ubuntu-14.04.1-server-i386.iso"

        #if "~" in args.media:
        media = os.path.normpath( os.path.expanduser(media) )

        # Check to see if --media option was present 
        iso=None
        vdi=None
        vmdx=None
        if media:
            iso = media if media.endswith(".iso") else None
            vdi = media if media.endswith(".vdi") else None
            vmdx = media if media.endswith(".vmdx") else None

        
        # Now we need to use a templating system to copy our initial Vagabond.py file into the project directory 
        from vagabond.templates import VagabondTemplate
        vfile = os.path.join( os.path.abspath(self.vm_name), "Vagabond.py") 
        with open(vfile, 'w') as f:
            f.write( VagabondTemplate.render({
                'version':API_VERSION,
                'vmname':self.vm_name,
                'iso':iso,
                'vdi':vdi,
                'vmdx':vmdx,
            }))


    def readVagabond(self):
        # Check for Vagabond file in local directory
        vfile = os.path.join(os.getcwd(), "Vagabond.py")
        if not os.path.isfile(vfile):
            raise IOError("You must have a Vagabond file in your current directory")

        # Add current directory to sys path...
        # so that when we load the Vagabond module it loads the users module
        sys.path.insert(0, os.getcwd())
        import Vagabond

        #TODO Need to do a verify/check on the imported Vagabond file.

        return Vagabond


    def _set_project_dir(self):
        # boxdir ~./vagabond/boxes
        boxdir = os.path.join(
            os.path.expanduser("~"),
            ".vagabond/boxes/",
        )

        # projdir ~/.vagabond/boxes/self.vm_name
        self.projdir = os.path.normpath(os.path.join(boxdir, self.vm_name))

    # Rename to something like _create_vagabond_box
    def _create_project_dir(self, count=0):
        """
            Create the project directory.  
            If the project directory exists and --force was issued
            then we remove the prject directory and do a single shot
            recursive call self._create_project_dir(count=1) setting
            the count variable to inform us to short circuit if 
            creation of the project directory fails a second time.
        """
        # Set the project directory
        self._set_project_dir()

        L.info("Checking for project directory")
        if not os.path.isdir(self.projdir):
            L.info("Creating project directory %s"%self.projdir)
            os.makedirs(self.projdir)
        else:
            if count > 0:
                L.critical("Project directory(%s) already exists and unable to remove."%self.projdir)
                sys.exit(0)
            else:
                L.warning("Project directory(%s) already exists."%self.projdir)
                
            if self.kwargs['force']:
                L.warn("--force Removing project directry %s", self.projdir)
                shutil.rmtree(os.path.abspath(self.projdir))
                return self._create_project_dir(count=count+1)
            else:
                L.critical("Project directory(%s) already exists.  Try --force to remove it and start fresh"%self.projdir)
                sys.exit(0)


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
        #self.VAGRANT_PROJECT_ROOT = self.kwargs['VAGRANT_PROJECT_ROOT']
        #self.BOXDIR = os.path.join(self.VAGRANT_PROJECT_ROOT, "boxes")
        self.loc = self.kwargs['loc']
        self.box_name = self.kwargs['name']
        L.warn(self.loc)

        #if args.loc.startswith("http://") and args.loc.endswith(".box"):
        if self.loc.startswith("http://") and self.loc.endswith(".box"):
            # the vagabond project directory typically ~/.vagrant/boxes/args.name
            projdir = os.path.normpath(os.path.join(self.BOXDIR, self.box_name))
            try:
                os.makedirs(projdir)
            except OSError as e:
                if errno.errorcode[e.errno] != 'EEXIST':
                    L.warn("Box directory (%s) already present", projdir)
                    raise

            download_fname = os.path.join(projdir, self.box_name)
            L.info("download_fname: %s", download_fname)

            r = self.download(self.loc, download_fname)
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
 
        VAGABOND = self.readVagabond() 
        self.config = VAGABOND.config
        self.vm_name = self.config.get('vmname', 'vagabond')
        
        media = self.config.get('media')
        if not media:
            raise ValueError("No media specified in Vagabond.py file")
    
        L.info("media type: %s", media)   

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
                            vdi_path = os.path.join(self.projdir, self.vm_name)
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
        if self.kwargs.get('hard_force'):
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

    def halt(self, vm_name=None):
        # This block is repeated in self.up()
        VAGABOND = self.readVagabond()
        self.config = VAGABOND.config
        self.vm_name = self.config.get('vmname', 'vagabond')

        try:
            self.vbox('VBoxManage', 'controlvm', self.vm_name, 'savestate')
        except VBoxManageError as e:
            if 'Machine in invalid state 1 -- powered off' in str(e):
                L.warn('Machine in invalid state 1 -- powered off')
            elif 'Machine in invalid state 2 -- saved' in str(e):
                L.warn('Machine in invalid state 2 -- saved')
            elif "Could not find a registered machine named '%s'"%self.vm_name:
                L.warn("Could not find a registered machine named '%s'"%self.vm_name)
            else:
                raise
    
    def unregistervm(self, count=0):
        """
            Unregister a vm.  name can be the UUID or the name of the vm
            NOTE:  If you pass it a name it will recusively delete all boxes with that name
        """
        if not self.vm_name:
            # Third time this block is repeated
            VAGABOND = self.readVagabond()
            self.config = VAGABOND.config
            self.vm_name = self.config.get('vmname', 'vagabond')

        self._set_project_dir()

        try:
            self.vbox('VBoxManage', 'unregistervm', self.vm_name, "--delete")
        except VBoxManageError as e:
            if "Could not find a registered machine named '%s'"%self.vm_name in str(e):
                pass
            elif "Cannot unregister the machine '%s' while it is locked"%self.vm_name in str(e):
                L.error("Cannot unregister the machine '%s' while it is locked"%self.vm_name)
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
            os.rmdir(self.projdir)



