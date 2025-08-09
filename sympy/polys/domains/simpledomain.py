"""Implementation of :class:`SimpleDomain` class. """
from __future__ import annotations

from typing import TYPE_CHECKING
from sympy.polys.domains.domain import Domain, Er
from sympy.utilities import public

if TYPE_CHECKING:
    from typing_extensions import Self

@public
class SimpleDomain(Domain[Er]):
    """Base class for simple domains, e.g. ZZ, QQ. """

    is_Simple = True

    def inject(self, *gens) -> Self:
        """Inject generators into this domain. """
        return self.poly_ring(*gens)
