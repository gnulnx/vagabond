import unittest
import time
import shutil
import os
import sys
from vm import (
    VM, 
    VagabondError, 
    VagabondActionUndefined,
)
from vagabond.version import API_VERSION

# import this now so we don't get path errors in 
# VM.init() when we try to import VagabondTemplate
from vagabond import templates
from vagabond.ostypes import OSTYPES

# To run the tests run the following commands in PROJECT_ROOT
# coverage run -m unittest discover
# coverage report -m --include=vagabond/
# OR: 
# coverage run -m unittest discover ; coverage report -m --include=vagabond/*

# Should set a root directory for the tests to run in..
# This directory will have project directories created/destroyed in it
TEST_ROOT = os.path.join(os.getcwd(), 'vagrant_test_tmp')
class TestVMActions(unittest.TestCase):

    def setUp(self):
        self.TEST=True
        
        self.kwargs = {
            'TEST': self.TEST,
        }

        # Make sure the previous test directory is removed
        if os.path.isdir(TEST_ROOT):
            shutil.rmtree(TEST_ROOT)

        # Create a new test directory
        os.mkdir(TEST_ROOT)

        self.vm = None

    def tearDown(self):     
        print "\n** tearDown ** "
        if self.vm:
            self.vm.halt()
            self.vm.unregistervm()

        # Now remove the root testing directory
        shutil.rmtree(TEST_ROOT)

    def _vm_factory(self, project_name):
        # Return to the root test directory
        os.chdir(TEST_ROOT)
        self.kwargs.update({
            'subparser_name':'init',
            'force':True,
            'project-name':project_name,
            'iso':os.path.expanduser('~/Downloads/ubuntu-14.04.1-server-i386.iso')
        })
        VM(**self.kwargs)

        os.chdir(project_name)
        kwargs = {
            'subparser_name': 'up',
            'force': True,
            'hard_force': False,
            'TEST': self.TEST
        }
        vm = VM(**kwargs)
        time.sleep(3)
    
        return vm
    

    def test_startvm(self): 
        self.vm = self._vm_factory('start_test')
        #Should be warning
        self.vm.up()

    def test_halt(self):
        # Test halt by calling the halt() method on an instantiated vm
        self.vm = self._vm_factory('halt_test')
        self.vm.halt()

        # Test calling halt on a halted vm.
        self.vm.halt()

        # Test that you can't poweroff a halted machine
        self.vm.poweroff()

        # Bring the vm back up.
        # and call halt with command line parameters
        self.vm.up()
        kwargs = {
            'subparser_name': 'halt',
            'force': False,
            'TEST': self.TEST
        }
        self.vm = VM(**kwargs)

    def test_barebones_init(self):
        project_name='virtual_machine_1'
        self.kwargs.update({
            'subparser_name':'init', 
            'force':True, 
            'project-name':project_name, 
        })

        vm = VM(**self.kwargs)
        self.assertEqual(vm.RET['STATUS'], 'SUCCESS')
        
        self.assertTrue(os.path.isdir(project_name))

        # Check that we have to be in correct directory
        self.assertRaises(IOError, vm.readVagabond)

        hold_dir = os.getcwd()
        os.chdir(project_name)
        vm.readVagabond() 
        config = vm.config
        self.assertEqual(vm.config_version, API_VERSION)
        
        # confirm that that config has a vm section
        self.assertTrue(config.get('vm'))

        # Confirm that the defaults are correct
        vm = config.get('vm')
        self.assertEqual('hashicopy/precise64',  vm.get('box'))
        self.assertEqual(None,  vm.get('iso'))

        self.assertEqual(project_name, vm.get('hostname'))
        
        # Now go back to parent directory and try again to see errors
        os.chdir(hold_dir)

        # Now test that trying to create the project again without --force throws errors
        self.kwargs.update({'force':False})
        self.assertRaises(VagabondError, VM, **self.kwargs)
        
        self.kwargs.update({'force':True})
        vm = VM(**self.kwargs)

        project_path=os.path.abspath(project_name)
        shutil.rmtree(project_path)
        self.assertFalse(os.path.isdir(project_path))

    unittest.skip("showing class skipping")
    def test_iso_box(self): 
        print "ENTERING test_iso_box"
        self.vm = self._vm_factory('Ubuntu_1404')

        self.vm.halt() 

        self.vm.up()

        self.vm.halt()

        self.vm.unregistervm()

    def test_halt_after_poweroff(self):
        # Bring up a VM and test power off by call poweroff on instance
        self.vm = self._vm_factory('halt_test')
        self.vm.poweroff()

        # test that you can't halt a powered off machine
        self.vm.halt()  
        
        #clean up the machine
        self.vm.unregistervm()

        # Bring up a VM and test poweroff with command line parameters
        self.vm = self._vm_factory('halt_test')
        kwargs = {
            'subparser_name': 'destroy',
            'force': False,
            'TEST': self.TEST
        }
        self.vm = VM(**kwargs)

       
    def test_action_not_defined(self):
        kwargs = {
            'subparser_name': 'noaction',
            'force': False,
            'TEST': self.TEST
        }        

        self.assertRaises(VagabondActionUndefined, VM, **self.kwargs)
   
    def test_box_subaction_not_defined(self):
        self.kwargs.update({
            'subparser_name': 'box',
            'box_subparser_name': 'noaction',
            'name': 'ubuntu_1404',
            'loc': 'http://hashicorp-files.vagrantup.com/precise32.box',
        })
        self.assertRaises(VagabondError, VM, **self.kwargs)     
    

    unittest.skip("showing class skipping")
    def test_add_vagrant_box(self):
        self.kwargs.update({
            'subparser_name': 'box', 
            'box_subparser_name': 'add',
            'name': 'ubuntu_1404', 
            'loc': 'http://hashicorp-files.vagrantup.com/precise32.box', 
        })

        vm = VM(**self.kwargs)

        self.assertEqual(vm.RET['STATUS'], 'SUCCESS')

        # Test that all the typicaly vagrant files are there.
        VAGABOND_PROJECT_ROOT = vm.RET['VAGABOND_PROJECT_ROOT']
        for _file in ['box-disk1.vmdk', 'box.ovf', 'Vagrantfile']:
            vfile = os.path.join(VAGABOND_PROJECT_ROOT, _file)
            self.assertTrue(os.path.isfile(vfile))

        """
        x box-disk1.vmdk
        x box.ovf
        x Vagrantfile
        """

    def test_show_valid_os_types(self):
        ostypes = VM.show_valid_os_types()      
        self.assertEqual(ostypes, OSTYPES)
        
        

if __name__ == '__main__':
    unittest.main()
