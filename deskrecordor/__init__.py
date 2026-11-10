"""Compatibility wrapper for the src-layout DeskRecordor package."""
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

_src_pkg = Path(__file__).resolve().parents[1] / 'src' / 'deskrecordor'
__path__.insert(0, str(_src_pkg))

_spec = spec_from_file_location('_deskrecordor_src_init', _src_pkg / '__init__.py')
if _spec and _spec.loader:
    _module = module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    __version__ = getattr(_module, '__version__', '0.1.0')
else:
    __version__ = '0.1.0'
