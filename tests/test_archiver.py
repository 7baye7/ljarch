import os
import sys
import unittest
import mock

mainPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(mainPath)

import archiver

class ArchiverTestCase(unittest.TestCase):

    @mock.patch('archiver.SetupLogger', autospec=True)
    @mock.patch('archiver.GetConfig', autospec=True)
    @mock.patch('archiver.ReadPasswordHash', autospec=True)
    @mock.patch('archiver.PostProcessor', autospec=True)
    def test_main_passes(self, mock_postproc, mock_readpwd, mock_config, mock_logger):
        # Arrange
        logger = mock.Mock()
        mock_logger.return_value = logger
        mock_config.return_value = [{'journal': 'user1', 'sectionName': 'server1', 'archiveComments': False},
                                    {'journal': 'user2', 'sectionName': 'server2', 'archiveComments': False}]
        mock_readpwd.return_value = '44C7BE48226EBAD5DCA8216674CAD62B'

        # Act
        archiver.main()

        # Assert
        self.assertEqual(mock_postproc.call_count, 2)
        mock_readpwd.assert_has_calls([mock.call('user1', 'server1'), mock.call('user2', 'server2')])
        self.assertEqual(logger.error.call_count, 0)
        self.assertEqual(logger.critical.call_count, 0)
        

    @mock.patch('archiver.SetupLogger', autospec=True)
    @mock.patch('archiver.GetConfig', autospec=True)
    @mock.patch('archiver.ReadPasswordHash', autospec=True)
    @mock.patch('archiver.PostProcessor', autospec=True)
    @mock.patch('archiver.CommentProcessor', autospec=True)
    def test_main_processesComments(self, mock_commentproc, mock_postproc, mock_readpwd, mock_config, mock_logger):
        # Arrange
        logger = mock.Mock()
        mock_logger.return_value = logger
        mock_config.return_value = [{'journal': 'user1', 'sectionName': 'server1', 'archiveComments': True}]
        mock_readpwd.return_value = '44C7BE48226EBAD5DCA8216674CAD62B'

        # Act
        archiver.main()

        # Assert
        self.assertEqual(mock_commentproc.call_count, 1)
        self.assertEqual(logger.error.call_count, 0)
        self.assertEqual(logger.critical.call_count, 0)


    @mock.patch('archiver.SetupLogger', autospec=True)
    @mock.patch('archiver.GetConfig', autospec=True)
    @mock.patch('archiver.ReadPasswordHash', autospec=True)
    @mock.patch('archiver.PostProcessor', autospec=True)
    def test_main_throwsNormalError(self, mock_postproc, mock_readpwd, mock_config, mock_logger):
        # Arrange
        logger = mock.Mock()
        mock_logger.return_value = logger
        mock_config.return_value = [{'journal': 'user1', 'sectionName': 'server1'}, # no 'archiveComments' causes an exception
                                    {'journal': 'user2', 'sectionName': 'server2', 'archiveComments': False}]
        mock_readpwd.return_value = '44C7BE48226EBAD5DCA8216674CAD62B'

        # Act
        archiver.main()

        # Assert
        self.assertEqual(logger.error.call_count, 1)
        self.assertEqual(logger.critical.call_count, 0)


    @mock.patch('archiver.SetupLogger', autospec=True)
    @mock.patch('archiver.GetConfig', autospec=True)
    @mock.patch('archiver.ReadPasswordHash', autospec=True)
    @mock.patch('archiver.PostProcessor', autospec=True)
    def test_main_throwsCriticalError(self, mock_postproc, mock_readpwd, mock_config, mock_logger):
        # Arrange
        logger = mock.Mock()
        mock_logger.return_value = logger
        mock_config.return_value = None # causes critical exception

        # Act
        archiver.main()

        # Assert
        self.assertEqual(logger.error.call_count, 0)
        self.assertEqual(logger.critical.call_count, 1)

if __name__ == '__main__':    
    unittest.main()