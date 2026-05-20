'''NistChemPy exceptions.'''


class NistChemPyError(Exception):
    '''Base exception for NistChemPy errors.'''


class NistChemPyIndexNotFoundError(NistChemPyError):
    '''Raised when a user-local WebBook index is not available.'''


class NistChemPyIndexError(NistChemPyError):
    '''Raised when a user-local WebBook index is invalid.'''


class NistChemPyIndexBuildError(NistChemPyIndexError):
    '''Raised when a user-local WebBook index build fails.'''


class NistChemPyDataTermsError(NistChemPyIndexBuildError):
    '''Raised when local index creation lacks explicit acknowledgement.'''


class NistChemPyOptionalDependencyError(NistChemPyError):
    '''Raised when an optional dependency is required but unavailable.'''
