import unittest
import yaml
import os

from ccgen import ccgen

class TestCCGen(unittest.TestCase):
    
    def test_generate_cql_code(self):
        file_name = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tables.yaml')
        input = yaml.load(open(file_name, 'r'))
        result = ccgen.generate_cql(input)
