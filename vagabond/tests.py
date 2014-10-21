import unittest
import os
from vm import VM

# To run the tests run the following commands in PROJECT_ROOT
# coverage run -m unittest discover
# coverage report -m --include=vagabond/
# OR: 
# coverage run -m unittest discover ; coverage report -m --include=vagabond/*
class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.TEST=True
        self.VAGRANT_PROJECT_ROOT='.vagabond/'
        self.kwargs = {
            'TEST': self.TEST,
        }
        self.seq = range(10)

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
