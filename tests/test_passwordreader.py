import os
import sys
import unittest
import mock

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))
from passwordreader import ReadPasswordHash

class PasswordReaderTestCase(unittest.TestCase):

    @mock.patch('passwordreader.getpass', autospec=True)
    def test_ReadPasswordHash_ReadsPasswordHash(self, mock_getpass):
        # Arrange
        mock_getpass.return_value = 'SECRET'

        # Act
        result = ReadPasswordHash('server', 'user')

        # Assert
        self.assertEqual(result.lower(),	'44C7BE48226EBAD5DCA8216674CAD62B'.lower())

if __name__ == '__main__':    
    unittest.main()