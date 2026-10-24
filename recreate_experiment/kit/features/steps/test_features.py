"""Collects every scenario of the kit's feature files (pytest-bdd).

Run from anywhere:  pytest <kit>/features/steps
The implementation under test is chosen by three environment variables
(see features/README.md): JDL_UNDER_TEST, JDL_CHAIN, JDL_ADAPTER.
"""
import os

from pytest_bdd import scenarios

FEATURES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

scenarios(FEATURES)
