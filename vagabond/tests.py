import unittest
import time
import shutil
import os
from vm import VM, VagabondError
from vagabond.version import API_VERSION

# To run the tests run the following commands in PROJECT_ROOT
# coverage run -m unittest discover
# coverage report -m --include=vagabond/
# OR: 
# coverage run -m unittest discover ; coverage report -m --include=vagabond/*
class TestVMActions(unittest.TestCase):

    def setUp(self):
        self.TEST=True
        
        self.kwargs = {
            'TEST': self.TEST,
        }

        self.vm = None

    def tearDown(self):     
        print "tearDown: "
        if self.vm:
            print "halting..."
            self.vm.halt()
            print "destroy..."
            self.vm.unregistervm()

    def _vm_factory(self, project_name):
        self.kwargs.update({
            'subparser_name':'init',
            'force':True,
            'project-name':project_name,
            'iso':os.path.expanduser('~/Downloads/ubuntu-14.04.1-server-i386.iso')
            #'box_name':'hashicopy/precise64', 
        })
        vm = VM(**self.kwargs)

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

    def test_barebones_init(self):
        project_name='virtual_machine_1'
        self.kwargs.update({
            'subparser_name':'init', 
            'force':True, 
            'project-name':project_name, 
            #'box_name':'hashicopy/precise64', 
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
        project_name='Ubuntu_1404'
        self.kwargs.update({
            'subparser_name':'init',
            'force':True,
            'project-name':project_name,
            'iso':os.path.expanduser('~/Downloads/ubuntu-14.04.1-server-i386.iso')
            #'box_name':'hashicopy/precise64', 
        })
        self.vm = VM(**self.kwargs)

        os.chdir(project_name)
        kwargs = {
            'subparser_name': 'up', 
            'force': False, 
            'hard_force': False, 
            'TEST': self.TEST
        }
        self.vm = VM(**kwargs)    

        self.vm.halt() 

        self.vm.up()

        self.vm.halt()

        self.vm.unregistervm()

    def test_halt_after_poweroff(self):
        self.vm = self._vm_factory('halt_test')

        self.vm.poweroff()

        self.vm.halt()

    def test_halt(self):
        self.vm = self._vm_factory('halt_test')

        self.vm.halt()

        self.vm.halt()

        # Test that you can't poweroff a halted machine
        self.vm.poweroff()
       
        
    def test_startvm(self): 
        self.vm = self._vm_factory('halt_test')
        #Should be warning
        self.vm.up()

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
        

if __name__ == '__main__':
    unittest.main()
