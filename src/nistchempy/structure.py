'''Optional RDKit-backed structure helpers.'''

from __future__ import annotations

import importlib as _importlib
from pathlib import Path as _Path
import typing as _tp

from nistchempy.exceptions import NistChemPyOptionalDependencyError

_RDKIT_INSTALL_MESSAGE = (
    'RDKit is required for this structural conversion. Install it with '
    '`pip install rdkit` or `conda install -c conda-forge rdkit`, or pass '
    'a MOL block/file directly when possible.'
)


def _load_chem():
    '''Return the RDKit Chem module or raise a clear optional-dependency error.'''
    try:
        return _importlib.import_module('rdkit.Chem')
    except ImportError as exc:
        raise NistChemPyOptionalDependencyError(
            _RDKIT_INSTALL_MESSAGE
        ) from exc


def _load_inchi():
    '''Return the RDKit InChI module or raise a clear dependency error.'''
    try:
        return _importlib.import_module('rdkit.Chem.inchi')
    except ImportError as exc:
        raise NistChemPyOptionalDependencyError(
            _RDKIT_INSTALL_MESSAGE
        ) from exc


def _compute_2d_coords(mol) -> None:
    '''Compute 2D coordinates when RDKit depiction support is available.'''
    try:
        rd_depictor = _importlib.import_module('rdkit.Chem.rdDepictor')
    except ImportError:
        return
    rd_depictor.Compute2DCoords(mol)


def mol_from_smiles(smiles: str):
    '''Create an RDKit molecule from a SMILES string.

    Args:
        smiles: SMILES string.

    Returns:
        rdkit.Chem.Mol: RDKit molecule.

    Raises:
        NistChemPyOptionalDependencyError: If RDKit is not installed.
        ValueError: If RDKit cannot parse the SMILES string.
    '''
    if not smiles:
        raise ValueError('smiles must be a non-empty string')
    chem = _load_chem()
    mol = chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f'RDKit could not parse SMILES: {smiles}')
    return mol


def mol_from_inchi(inchi: str):
    '''Create an RDKit molecule from an InChI string.

    Args:
        inchi: InChI string.

    Returns:
        rdkit.Chem.Mol: RDKit molecule.

    Raises:
        NistChemPyOptionalDependencyError: If RDKit is not installed.
        ValueError: If RDKit cannot parse the InChI string.
    '''
    if not inchi:
        raise ValueError('inchi must be a non-empty string')
    inchi_module = _load_inchi()
    mol = inchi_module.MolFromInchi(inchi)
    if mol is None:
        raise ValueError(f'RDKit could not parse InChI: {inchi}')
    return mol


def mol_from_molblock(molblock: str, sanitize: bool = True):
    '''Create an RDKit molecule from a MOL block.

    Args:
        molblock: MOL block text.
        sanitize: Whether RDKit should sanitize the molecule.

    Returns:
        rdkit.Chem.Mol: RDKit molecule.

    Raises:
        NistChemPyOptionalDependencyError: If RDKit is not installed.
        ValueError: If RDKit cannot parse the MOL block.
    '''
    if not molblock:
        raise ValueError('molblock must be a non-empty string')
    chem = _load_chem()
    mol = chem.MolFromMolBlock(
        molblock,
        sanitize=sanitize,
        removeHs=False,
    )
    if mol is None:
        raise ValueError('RDKit could not parse the MOL block')
    return mol


def mol_from_molfile(path: _tp.Union[str, _Path], sanitize: bool = True):
    '''Create an RDKit molecule from a MOL file.

    Args:
        path: Path to a MOL file.
        sanitize: Whether RDKit should sanitize the molecule.

    Returns:
        rdkit.Chem.Mol: RDKit molecule.

    Raises:
        NistChemPyOptionalDependencyError: If RDKit is not installed.
        ValueError: If RDKit cannot parse the MOL file.
    '''
    chem = _load_chem()
    mol = chem.MolFromMolFile(
        str(path),
        sanitize=sanitize,
        removeHs=False,
    )
    if mol is None:
        raise ValueError(f'RDKit could not parse MOL file: {path}')
    return mol


def molblock_from_mol(mol) -> str:
    '''Convert an RDKit molecule into a MOL block.

    Args:
        mol: RDKit molecule.

    Returns:
        str: MOL block text.
    '''
    chem = _load_chem()
    if mol.GetNumConformers() == 0:
        _compute_2d_coords(mol)
    return chem.MolToMolBlock(mol)


def molblock_from_smiles(smiles: str) -> str:
    '''Convert a SMILES string into a MOL block using RDKit.

    Args:
        smiles: SMILES string.

    Returns:
        str: MOL block text.
    '''
    return molblock_from_mol(mol_from_smiles(smiles))


def molblock_from_inchi(inchi: str) -> str:
    '''Convert an InChI string into a MOL block using RDKit.

    Args:
        inchi: InChI string.

    Returns:
        str: MOL block text.
    '''
    return molblock_from_mol(mol_from_inchi(inchi))


def mol_to_inchi_key(mol) -> str:
    '''Return the RDKit-computed InChIKey for a molecule.

    Args:
        mol: RDKit molecule.

    Returns:
        str: InChIKey.
    '''
    inchi_module = _load_inchi()
    return inchi_module.MolToInchiKey(mol)


def query_mol_from_input(
        *, smiles: str | None = None, inchi: str | None = None,
        molblock: str | None = None, molfile: _tp.Union[str, _Path, None] = None):
    '''Create an RDKit molecule from exactly one structural input.

    Args:
        smiles: Optional SMILES query.
        inchi: Optional InChI query.
        molblock: Optional MOL block query.
        molfile: Optional path to a MOL file query.

    Returns:
        rdkit.Chem.Mol: Query molecule.

    Raises:
        ValueError: If zero or multiple structural inputs are supplied.
    '''
    provided = [
        value is not None for value in (smiles, inchi, molblock, molfile)
    ]
    if sum(provided) != 1:
        raise ValueError(
            'Exactly one of smiles, inchi, molblock, or molfile must be '
            'provided.'
        )
    if smiles is not None:
        return mol_from_smiles(smiles)
    if inchi is not None:
        return mol_from_inchi(inchi)
    if molblock is not None:
        return mol_from_molblock(molblock)
    return mol_from_molfile(molfile)


def morgan_fingerprint(mol, radius: int = 2, fp_size: int = 2048):
    """Return an RDKit Morgan fingerprint bit vector.

    Args:
        mol: RDKit molecule.
        radius: Morgan fingerprint radius.
        fp_size: Fingerprint size in bits.

    Returns:
        ExplicitBitVect: RDKit fingerprint.
    """
    try:
        generator_module = _importlib.import_module(
            'rdkit.Chem.rdFingerprintGenerator'
        )
    except ImportError as exc:
        raise NistChemPyOptionalDependencyError(
            _RDKIT_INSTALL_MESSAGE
        ) from exc
    generator = generator_module.GetMorganGenerator(
        radius=radius,
        fpSize=fp_size,
    )
    return generator.GetFingerprint(mol)


def tanimoto_similarity(fp1, fp2) -> float:
    """Return Tanimoto similarity between two RDKit fingerprints.

    Args:
        fp1: First RDKit fingerprint.
        fp2: Second RDKit fingerprint.

    Returns:
        float: Tanimoto similarity.
    """
    try:
        data_structs = _importlib.import_module('rdkit.DataStructs')
    except ImportError as exc:
        raise NistChemPyOptionalDependencyError(
            _RDKIT_INSTALL_MESSAGE
        ) from exc
    return float(data_structs.TanimotoSimilarity(fp1, fp2))
