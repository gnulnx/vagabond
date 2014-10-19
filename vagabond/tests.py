import unittest
from vm import VM

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.seq = range(10)

    def test_hello(self):
        self.assertEqual("Hello", "Hell0")

if __name__ == '__main__':
    unittest.main()
