from factory.base import Factory
from factory.fuzzy import FuzzyAttribute, FuzzyText, FuzzyInteger

from nutrition101.domain import NBreakdown, NEntry


_fuzz_num = FuzzyInteger(low=1, high=400)


class NEntryFactory(Factory):
    class Meta:
        model = NEntry

    item = FuzzyText("netry-item-")
    calories = _fuzz_num
    carbs_g = _fuzz_num
    sugars_g = _fuzz_num
    added_sugars_g = _fuzz_num
    protein_g = _fuzz_num
    fat_g = _fuzz_num
    fiber_g = _fuzz_num
    sodium_mg = _fuzz_num


class NBreakdownFactory(Factory):
    class Meta:
        model = NBreakdown

    entries = FuzzyAttribute(lambda: NEntryFactory.build_batch(5))
