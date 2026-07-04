from dataclasses import dataclass

from .models import Pivot


@dataclass
class SwingHierarchy:

    external: bool

    internal: bool

    pivot: Pivot


class HierarchyBuilder:

    def build(
        self,
        external_structure,
        internal_structure,
    ):

        hierarchy = []

        external_ids = {
            id(x)
            for x in external_structure.major_highs
        }

        external_ids.update(
            id(x)
            for x in external_structure.major_lows
        )

        for pivot in internal_structure.pivots:

            hierarchy.append(

                SwingHierarchy(

                    external=id(pivot) in external_ids,

                    internal=True,

                    pivot=pivot,
                )
            )

        return hierarchy