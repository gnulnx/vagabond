import unittest
from vm import VM

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.TEST=True
        self.VAGRANT_PROJECT_ROOT='/Users/jfurr/.vagabond/'
        self.kwargs = {
            'TEST': self.TEST,
        }
        self.seq = range(10)

    def test_add_vagrant_box(self):
        self.kwargs.update({
            'subparser_name': 'box', 
            'box_subparser_name': 'add',
            'name': 'john', 
            'loc': 'http://hashicorp-files.vagrantup.com/precise32.box', 
            'color': None, # Don't think this is needed
        })

        print self.kwargs

        vm = VM(**self.kwargs)

        """
        x box-disk1.vmdk
        x box.ovf
        x Vagrantfile
        """
        

if __name__ == '__main__':
    unittest.main()
