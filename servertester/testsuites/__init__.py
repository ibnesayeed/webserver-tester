import glob
import traceback
import os

from inspect import isclass

from servertester.base.httptester import HTTPTester

def _import_all_modules():
    """Dynamically import all test suite classes from all modules in this package"""
    global __all__
    __all__ = []
    globals_, locals_ = globals(), locals()

    testsuites = {}

    pkd_dir = os.path.dirname(os.path.abspath(__file__))
    for fpath in sorted(glob.glob(f"{pkd_dir}/*.py")):
        mod_name = fpath.split("/")[-1].split(".")[0]
        if not mod_name.startswith("_"):
            pkg_mod = ".".join([__name__, mod_name])
            try:
                mod = __import__(pkg_mod, globals_, locals_, [mod_name])
            except:
                traceback.print_exc()
                raise
            for name, ref in mod.__dict__.items():
                if not name.startswith("_") and name != "HTTPTester" and isclass(ref) and issubclass(ref, HTTPTester):
                    globals_[name] = mod.__dict__[name]
                    __all__.append(name)
                    testsuites[name.lower()] = ref

    globals_["testsuites"] = testsuites
    __all__.append("testsuites")

_import_all_modules()
