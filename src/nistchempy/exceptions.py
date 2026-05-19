'''NistChemPy exceptions.'''


class NistChemPyError(Exception):
    '''Base exception for NistChemPy errors.'''


class NistChemPyIndexNotFoundError(NistChemPyError):
    '''Raised when a user-local WebBook index is not available.'''


class NistChemPyIndexError(NistChemPyError):
    '''Raised when a user-local WebBook index is invalid.'''
