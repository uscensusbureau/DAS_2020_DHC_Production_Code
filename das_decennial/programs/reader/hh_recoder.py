# hh_recoder.py
# Some Human
# Last Modified: 1/9/2019

"""
    This module is a variable recoder library for household tables. Each class is specific to a table.

    The recoder class must contain a method called "recode".
    The recode method operates on a single SparkDataFrame row
    and returns the row with the recoded variable(s) added.

    A recoder class is specified in the main config file.
    The config file reader section must contain the following options:
        table_name.recoder: recoder class to be used with table_name
        table_name.recode_variables: space-delimited list of new variable names
                               e.g.: votingage cenrace
        for each new variable the config file contains:
        var_name: space-delimited list of original table variable names needed to create var_name
            e.g.: votingage: age
            e.g.: cenrace: white black sor
    Note: recode variable names can't clash with original variable names.

    The recoder class __init__ method must have one arg for each new variable.
    An arg is a list of original table variable names needed to create one recode variable.
    The args should be ordered according to the ordering of table_name.recode_variables.

    Sample class using the above recode variable examples.
    class sample_recoder:
        def __init__(self, arg1_list, arg2_list):
            # arg1_list = ["age"]
            # arg2_list = ["white", "black", "sor"]
            self.arg1 = arg1
            self.arg2 = arg2
        def recode(self, row):
            do_some_stuff()
            return new_row

"""

import bisect
from typing import List

from programs.schema.attributes.hhgq_unit_demoproduct import HHGQUnitDemoProductAttr
from programs.schema.attributes.hhgq import HHGQAttr
from programs.schema.attributes.tenvacgq import TenureVacancyGQAttr
from pyspark.sql import Row

class table12_recoder:
    """
        This is the recoder for table12a.
        It creates hhage and rent
    """
    def __init__(self, age_list: List, rent_list: List, size_list: List):
        self.age = age_list[0] # list only contains "age"
        self.ten = rent_list[0] # list only contains "ten"
        self.size = size_list[0] # list only contains "hhsize"

    def recode(self, row: Row):
        row = self.age_recode(row, self.age)
        row = self.ten_recode(row, self.ten)
        row = self.size_recode(row, self.size)
        return row

    @staticmethod
    def age_recode(row: Row, age):
        """
        householder age cat recode
        15-24, 25-34, 35-44, 45-54, 55-59, 60-64, 65-74, 75-84, 85-115 (9 cats)
        116 values 0-115
        """
        cutoffs = [15,25,35,45,55,60,65,75,85]

        return Row(**row.asDict(), hhage=bisect.bisect_right(cutoffs,int(row[age]))-1)

    @staticmethod
    def ten_recode(row: Row, ten):
        """ recode of tenure. """

        assert int(row[ten]) != 0, "vacant housing unit found within household table"
        rent = 0 if int(row[ten]) < 3 else 1
        return Row(**row.asDict(), rent=rent)

    @staticmethod
    def size_recode(row: Row, size):
        """ topcode of household size """
        assert 0 < int(row[size]) < 100
        # size cats: 1,2,3,4,5,6,7+
        hhsize = 7 if int(row[size]) >= 7 else int(row[size])
        return Row(**row.asDict(), size = hhsize)


class TenUnit2010Recoder(table12_recoder):
    """ Recoder for Household with full tenure """
    #def __init__(self, *args):
    #    super.__init__(tuple(*args))

    @staticmethod
    def ten_recode(row: Row, ten):
        assert int(row[ten]) != 0, "vacant housing unit found"
        return Row(**row.asDict(), tenure=(int(row[ten]) - 1))
        # return Row(**row.asDict(), tenure=(int(row[ten]) - 1) % 3)  # To decrease number of levels in tenure var, for testing (also need to change config reader section and tenure attribute)


class Table10RecoderSimple:
    """
    This recoder for Table 10 recodes the hhgq vector
    [occupied housing units, vacant_housing units, [gqtypes]] into
    [total_housing_units, [gqtypes]].
    Occupied and vacant are protected, and total is invariant (as well as all gqtypes), so we're
    leaving only invariants to pass through the DAS as raw_housing vector in GeounitNodes.
    """

    def __init__(self, hhgq_list: List):
        self.hhgq = hhgq_list[0]

    def recode(self, row: Row):
        hhgqinv = int(row[self.hhgq])
        # 0 stands for occupied housing units, 1 stands for vacant, everything else is a GQ type
        # We want to bundle occupied and vacant housing units under the index 0
        if hhgqinv == 1:
            hhgqinv = 0
        elif hhgqinv > 1:  # Need to shift indices, since we removed one cell
           hhgqinv -= 1
        return Row(**row.asDict(), hhgqinv=hhgqinv)


class Table10Recoder:

    def __init__(self, hhgq_list: List):
        self.gqtype = hhgq_list[0]
        self.vacs = hhgq_list[1]

    def recode(self, row: Row):
        gqtype = row[self.gqtype]
        vacs = row[self.vacs]
        if  gqtype == "000" or gqtype == "   ":
            if int(vacs) == 0:
                hhgq = 0 # occupied
            else:
                hhgq = 1 # vacant
        else:
            hhgq = HHGQUnitDemoProductAttr.cef2das(gqtype)

        return Row(**row.asDict(), hhgq=hhgq)


class h1_recoder:
    def __init__(self, hhgq_list: List):
        self.gqtype = hhgq_list[0]
        self.vacs = hhgq_list[1]

    def recode(self, row: Row):
        gqtype = row[self.gqtype]
        vacs = row[self.vacs]
        if gqtype == "000":
            if int(vacs) == 0:
                h1 = 1 # occupied
            else:
                h1 = 0 # vacant
            return Row(**row.asDict(), h1=h1)
        # if not a housing unit return None and it will be filtered out.
        return None


class Table10VacsRecoder:

    def __init__(self, tenvacgq_list: List):
        self.gqtype = tenvacgq_list[2]
        self.vacs = tenvacgq_list[1]
        self.ten = tenvacgq_list[0]

    def recode(self, row: Row):

        tenvacgq = TenureVacancyGQAttr.cef2das(row[self.ten], row[self.vacs], row[self.gqtype])

        return Row(**row.asDict(), tenvacgq=tenvacgq)

class Table10RecoderDHCP:
    def __init__(self, hhgq_list: List):
        self.gqtype = hhgq_list[0]
        #self.vacs = hhgq_list[1]

    def recode(self, row: Row):
        gqtype = row[self.gqtype]
        #vacs = row[self.vacs]
        if  gqtype == "000" or gqtype == "   ":
            #if int(vacs) == 0:
            #    hhgq = 0
            #else:
            #    hhgq = 1
            hhgq = 0
        else:
            hhgq = HHGQAttr.cef2das(gqtype)

        return Row(**row.asDict(), hhgq_unit_dhcp=hhgq)
