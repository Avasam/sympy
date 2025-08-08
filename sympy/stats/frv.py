"""
Finite Discrete Random Variables Module

See Also
========
sympy.stats.frv_types
sympy.stats.rv
sympy.stats.crv
"""
from itertools import product

from sympy.concrete.summations import Sum
from sympy.core.basic import Basic
from sympy.core.cache import cacheit
from sympy.core.function import Lambda
from sympy.core.mul import Mul
from sympy.core.numbers import (I, nan)
from sympy.core.relational import Eq
from sympy.core.singleton import S
from sympy.core.symbol import (Dummy, Symbol)
from sympy.core.sympify import sympify
from sympy.functions.elementary.exponential import exp
from sympy.functions.elementary.piecewise import Piecewise
from sympy.logic.boolalg import (And, Or)
from sympy.sets.sets import Intersection
from sympy.core.containers import Dict
from sympy.core.logic import Logic
from sympy.core.relational import Relational
from sympy.core.sympify import _sympify
from sympy.sets.sets import FiniteSet
from sympy.stats.rv import (RandomDomain, ProductDomain, ConditionalDomain,
                            PSpace, IndependentProductPSpace, SinglePSpace, random_symbols,
                            sumsets, rv_subs, NamedArgsMixin, Density, Distribution)
import sympy
from collections.abc import Iterator
from sympy.series.order import Order
from sympy.stats.crv import ProductContinuousDomain
from sympy.stats.drv import ProductDiscreteDomain
from typing import Any

if TYPE_CHECKING:
    from typing_extensions import Self


class FiniteDensity(dict):
    """
    A domain with Finite Density.
    """
    def __call__(self, item) -> int:
        """
        Make instance of a class callable.

        If item belongs to current instance of a class, return it.

        Otherwise, return 0.
        """
        item = sympify(item)
        if item in self:
            return self[item]
        else:
            return 0

    @property
    def dict(self) -> dict:
        """
        Return item as dictionary.
        """
        return dict(self)

class FiniteDomain(RandomDomain):
    """
    A domain with discrete finite support

    Represented using a FiniteSet.
    """
    is_Finite = True

    @property
    def symbols(self) ->     sympy.FiniteSet:
        return FiniteSet(sym for sym, val in self.elements)

    @property
    def elements(self) ->     sympy.Basic:
        return self.args[0]

    @property
    def dict(self) ->     sympy.FiniteSet:
        return FiniteSet(*[Dict(dict(el)) for el in self.elements])

    def __contains__(self, other) -> bool:
        return other in self.elements

    def __iter__(self):
        return self.elements.__iter__()

    def as_boolean(self) ->     Or:
        return Or(*[And(*[Eq(sym, val) for sym, val in item]) for item in self])


class SingleFiniteDomain(FiniteDomain):
    """
    A FiniteDomain over a single symbol/set

    Example: The possibilities of a *single* die roll.
    """

    def __new__(cls, symbol, set) -> Self:
        if not isinstance(set, FiniteSet) and \
            not isinstance(set, Intersection):
            set = FiniteSet(*set)
        return Basic.__new__(cls, symbol, set)

    @property
    def symbol(self) ->     sympy.Basic:
        return self.args[0]

    @property
    def symbols(self) ->     sympy.FiniteSet:
        return FiniteSet(self.symbol)

    @property
    def set(self) ->     sympy.Basic:
        return self.args[1]

    @property
    def elements(self) ->     sympy.FiniteSet:
        return FiniteSet(*[frozenset(((self.symbol, elem), )) for elem in self.set])

    def __iter__(self) -> Iterator[frozenset[tuple[    sympy.Basic, Any]]]:
        return (frozenset(((self.symbol, elem),)) for elem in self.set)

    def __contains__(self, other) -> bool:
        sym, val = tuple(other)[0]
        return sym == self.symbol and val in self.set


class ProductFiniteDomain(ProductDomain, FiniteDomain):
    """
    A Finite domain consisting of several other FiniteDomains

    Example: The possibilities of the rolls of three independent dice
    """

    def __iter__(self) -> Iterator[frozenset]:
        proditer = product(*self.domains)
        return (sumsets(items) for items in proditer)

    @property
    def elements(self) ->     sympy.FiniteSet:
        return FiniteSet(*self)


class ConditionalFiniteDomain(ConditionalDomain, ProductFiniteDomain):
    """
    A FiniteDomain that has been restricted by a condition

    Example: The possibilities of a die roll under the condition that the
    roll is even.
    """

    def __new__(cls, domain, condition) -> Self:
        """
        Create a new instance of ConditionalFiniteDomain class
        """
        if condition is True:
            return domain
        cond = rv_subs(condition)
        return Basic.__new__(cls, domain, cond)

    def _test(self, elem):
        """
        Test the value. If value is boolean, return it. If value is equality
        relational (two objects are equal), return it with left-hand side
        being equal to right-hand side. Otherwise, raise ValueError exception.
        """
        val = self.condition.xreplace(dict(elem))
        if val in [True, False]:
            return val
        elif val.is_Equality:
            return val.lhs == val.rhs
        raise ValueError("Undecidable if %s" % str(val))

    def __contains__(self, other) ->     sympy.Basic | bool:
        return other in self.fulldomain and self._test(other)

    def __iter__(self) -> Iterator:
        return (elem for elem in self.fulldomain if self._test(elem))

    @property
    def set(self) ->     sympy.FiniteSet:
        if isinstance(self.fulldomain, SingleFiniteDomain):
            return FiniteSet(*[elem for elem in self.fulldomain.set
                               if frozenset(((self.fulldomain.symbol, elem),)) in self])
        else:
            raise NotImplementedError(
                "Not implemented on multi-dimensional conditional domain")

    def as_boolean(self) ->     Or:
        return FiniteDomain.as_boolean(self)


class SingleFiniteDistribution(Distribution, NamedArgsMixin):
    def __new__(cls, *args) -> Self:
        args = list(map(sympify, args))
        return Basic.__new__(cls, *args)

    @staticmethod
    def check(*args) -> None:
        pass

    @property # type: ignore
    @cacheit
    def dict(self) -> Density | dict:
        if self.is_symbolic:
            return Density(self)
        return {k: self.pmf(k) for k in self.set}

    def pmf(self, *args): # to be overridden by specific distribution
        raise NotImplementedError()

    @property
    def set(self): # to be overridden by specific distribution
        raise NotImplementedError()

    values = property(lambda self: self.dict.values)
    items = property(lambda self: self.dict.items)
    is_symbolic = property(lambda self: False)
    __iter__ = property(lambda self: self.dict.__iter__)
    __getitem__ = property(lambda self: self.dict.__getitem__)

    def __call__(self, *args):
        return self.pmf(*args)

    def __contains__(self, other) -> bool:
        return other in self.set


#=============================================
#=========  Probability Space  ===============
#=============================================


class FinitePSpace(PSpace):
    """
    A Finite Probability Space

    Represents the probabilities of a finite number of events.
    """
    is_Finite = True

    def __new__(cls, domain, density) -> Self:
        density = {sympify(key): sympify(val)
                for key, val in density.items()}
        public_density = Dict(density)

        obj = PSpace.__new__(cls, domain, public_density)
        obj._density = density
        return obj

    def prob_of(self, elem):
        elem = sympify(elem)
        density = self._density
        if isinstance(list(density.keys())[0], FiniteSet):
            return density.get(elem, S.Zero)
        return density.get(tuple(elem)[0][1], S.Zero)

    def where(self, condition) -> ConditionalFiniteDomain:
        assert all(r.symbol in self.symbols for r in random_symbols(condition))
        return ConditionalFiniteDomain(self.domain, condition)

    def compute_density(self, expr) -> FiniteDensity:
        expr = rv_subs(expr, self.values)
        d = FiniteDensity()
        for elem in self.domain:
            val = expr.xreplace(dict(elem))
            prob = self.prob_of(elem)
            d[val] = d.get(val, S.Zero) + prob
        return d

    @cacheit
    def compute_cdf(self, expr) -> dict:
        d = self.compute_density(expr)
        cum_prob = S.Zero
        cdf = []
        for key in sorted(d):
            prob = d[key]
            cum_prob += prob
            cdf.append((key, cum_prob))

        return dict(cdf)

    @cacheit
    def sorted_cdf(self, expr, python_float=False) -> list[tuple[Any, float]] | list[tuple[Any, Any]]:
        cdf = self.compute_cdf(expr)
        items = list(cdf.items())
        sorted_items = sorted(items, key=lambda val_cumprob: val_cumprob[1])
        if python_float:
            sorted_items = [(v, float(cum_prob))
                    for v, cum_prob in sorted_items]
        return sorted_items

    @cacheit
    def compute_characteristic_function(self, expr) -> Lambda:
        d = self.compute_density(expr)
        t = Dummy('t', real=True)

        return Lambda(t, sum(exp(I*k*t)*v for k,v in d.items()))

    @cacheit
    def compute_moment_generating_function(self, expr) -> Lambda:
        d = self.compute_density(expr)
        t = Dummy('t', real=True)

        return Lambda(t, sum(exp(k*t)*v for k,v in d.items()))

    def compute_expectation(self, expr, rvs=None, **kwargs):
        rvs = rvs or self.values
        expr = rv_subs(expr, rvs)
        probs = [self.prob_of(elem) for elem in self.domain]
        if isinstance(expr, (Logic, Relational)):
            parse_domain = [tuple(elem)[0][1] for elem in self.domain]
            bools = [expr.xreplace(dict(elem)) for elem in self.domain]
        else:
            parse_domain = [expr.xreplace(dict(elem)) for elem in self.domain]
            bools = [True for elem in self.domain]
        return sum(Piecewise((prob * elem, blv), (S.Zero, True))
                for prob, elem, blv in zip(probs, parse_domain, bools))

    def compute_quantile(self, expr) -> Lambda:
        cdf = self.compute_cdf(expr)
        p = Dummy('p', real=True)
        set = ((nan, (p < 0) | (p > 1)),)
        for key, value in cdf.items():
            set = set + ((key, p <= value), )
        return Lambda(p, Piecewise(*set))

    def probability(self, condition):
        cond_symbols = frozenset(rs.symbol for rs in random_symbols(condition))
        cond = rv_subs(condition)
        if not cond_symbols.issubset(self.symbols):
            raise ValueError("Cannot compare foreign random symbols, %s"
                             %(str(cond_symbols - self.symbols)))
        if isinstance(condition, Relational) and \
            (not cond.free_symbols.issubset(self.domain.free_symbols)):
            rv = condition.lhs if isinstance(condition.rhs, Symbol) else condition.rhs
            return sum(Piecewise(
                       (self.prob_of(elem), condition.subs(rv, list(elem)[0][1])),
                       (S.Zero, True)) for elem in self.domain)
        return sympify(sum(self.prob_of(elem) for elem in self.where(condition)))

    def conditional_space(self, condition) -> "FinitePSpace":
        domain = self.where(condition)
        prob = self.probability(condition)
        density = {key: val / prob
                for key, val in self._density.items() if domain._test(key)}
        return FinitePSpace(domain, density)

    def sample(self, size=(), library='scipy', seed=None) -> dict:
        """
        Internal sample method

        Returns dictionary mapping RandomSymbol to realization value.
        """
        return {self.value: self.distribution.sample(size, library, seed)}


class SingleFinitePSpace(SinglePSpace, FinitePSpace):
    """
    A single finite probability space

    Represents the probabilities of a set of random events that can be
    attributed to a single variable/symbol.

    This class is implemented by many of the standard FiniteRV types such as
    Die, Bernoulli, Coin, etc....
    """
    @property
    def domain(self) -> SingleFiniteDomain:
        return SingleFiniteDomain(self.symbol, self.distribution.set)

    @property
    def _is_symbolic(self):
        """
        Helper property to check if the distribution
        of the random variable is having symbolic
        dimension.
        """
        return self.distribution.is_symbolic

    @property
    def distribution(self) ->     sympy.Basic:
        return self.args[1]

    def pmf(self, expr):
        return self.distribution.pmf(expr)

    @property # type: ignore
    @cacheit
    def _density(self):
        return {FiniteSet((self.symbol, val)): prob
                    for val, prob in self.distribution.dict.items()}

    @cacheit
    def compute_characteristic_function(self, expr) -> Lambda:
        if self._is_symbolic:
            d = self.compute_density(expr)
            t = Dummy('t', real=True)
            ki = Dummy('ki')
            return Lambda(t, Sum(d(ki)*exp(I*ki*t), (ki, self.args[1].low, self.args[1].high)))
        expr = rv_subs(expr, self.values)
        return FinitePSpace(self.domain, self.distribution).compute_characteristic_function(expr)

    @cacheit
    def compute_moment_generating_function(self, expr) -> Lambda:
        if self._is_symbolic:
            d = self.compute_density(expr)
            t = Dummy('t', real=True)
            ki = Dummy('ki')
            return Lambda(t, Sum(d(ki)*exp(ki*t), (ki, self.args[1].low, self.args[1].high)))
        expr = rv_subs(expr, self.values)
        return FinitePSpace(self.domain, self.distribution).compute_moment_generating_function(expr)

    def compute_quantile(self, expr) -> Lambda:
        if self._is_symbolic:
            raise NotImplementedError("Computing quantile for random variables "
            "with symbolic dimension because the bounds of searching the required "
            "value is undetermined.")
        expr = rv_subs(expr, self.values)
        return FinitePSpace(self.domain, self.distribution).compute_quantile(expr)

    def compute_density(self, expr) -> Lambda | FiniteDensity:
        if self._is_symbolic:
            rv = list(random_symbols(expr))[0]
            k = Dummy('k', integer=True)
            cond = True if not isinstance(expr, (Relational, Logic)) \
                     else expr.subs(rv, k)
            return Lambda(k,
            Piecewise((self.pmf(k), And(k >= self.args[1].low,
            k <= self.args[1].high, cond)), (S.Zero, True)))
        expr = rv_subs(expr, self.values)
        return FinitePSpace(self.domain, self.distribution).compute_density(expr)

    def compute_cdf(self, expr) -> Lambda | dict:
        if self._is_symbolic:
            d = self.compute_density(expr)
            k = Dummy('k')
            ki = Dummy('ki')
            return Lambda(k, Sum(d(ki), (ki, self.args[1].low, k)))
        expr = rv_subs(expr, self.values)
        return FinitePSpace(self.domain, self.distribution).compute_cdf(expr)

    def compute_expectation(self, expr, rvs=None, **kwargs) -> tuple |     sympy.Sum | Order | Any |     sympy.Piecewise |     sympy.Basic |     sympy.Equality | Relational |     sympy.Ne | None:
        if self._is_symbolic:
            rv = random_symbols(expr)[0]
            k = Dummy('k', integer=True)
            expr = expr.subs(rv, k)
            cond = True if not isinstance(expr, (Relational, Logic)) \
                    else expr
            func = self.pmf(k) * k if cond != True else self.pmf(k) * expr
            return Sum(Piecewise((func, cond), (S.Zero, True)),
                (k, self.distribution.low, self.distribution.high)).doit()

        expr = _sympify(expr)
        expr = rv_subs(expr, rvs)
        return FinitePSpace(self.domain, self.distribution).compute_expectation(expr, rvs, **kwargs)

    def probability(self, condition):
        if self._is_symbolic:
            #TODO: Implement the mechanism for handling queries for symbolic sized distributions.
            raise NotImplementedError("Currently, probability queries are not "
            "supported for random variables with symbolic sized distributions.")
        condition = rv_subs(condition)
        return FinitePSpace(self.domain, self.distribution).probability(condition)

    def conditional_space(self, condition) -> FinitePSpace:
        """
        This method is used for transferring the
        computation to probability method because
        conditional space of random variables with
        symbolic dimensions is currently not possible.
        """
        if self._is_symbolic:
            self
        domain = self.where(condition)
        prob = self.probability(condition)
        density = {key: val / prob
                for key, val in self._density.items() if domain._test(key)}
        return FinitePSpace(domain, density)


class ProductFinitePSpace(IndependentProductPSpace, FinitePSpace):
    """
    A collection of several independent finite probability spaces
    """
    @property
    def domain(self) -> ProductDiscreteDomain | ProductContinuousDomain | ProductFiniteDomain:
        return ProductFiniteDomain(*[space.domain for space in self.spaces])

    @property  # type: ignore
    @cacheit
    def _density(self):
        proditer = product(*[iter(space._density.items())
            for space in self.spaces])
        d = {}
        for items in proditer:
            elems, probs = list(zip(*items))
            elem = sumsets(elems)
            prob = Mul(*probs)
            d[elem] = d.get(elem, S.Zero) + prob
        return Dict(d)

    @property  # type: ignore
    @cacheit
    def density(self) -> dict:
        return Dict(self._density)

    def probability(self, condition):
        return FinitePSpace.probability(self, condition)

    def compute_density(self, expr) -> FiniteDensity:
        return FinitePSpace.compute_density(self, expr)
