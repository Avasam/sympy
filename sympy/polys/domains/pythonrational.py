"""
Rational number type based on Python integers.

The PythonRational class from here has been moved to
sympy.external.pythonmpq

This module is just left here for backwards compatibility.
"""
from __future__ import annotations


from sympy.core.numbers import Integer, Rational
from sympy.core.sympify import _sympy_converter
from sympy.utilities import public
from sympy.external.pythonmpq import PythonMPQ


PythonRational = public(PythonMPQ)


def sympify_pythonrational(arg) -> Rational | Integer:
    return Rational(arg.numerator, arg.denominator)
_sympy_converter[PythonRational] = sympify_pythonrational
