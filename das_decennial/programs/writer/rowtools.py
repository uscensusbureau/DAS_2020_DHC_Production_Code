from typing import Dict, Union, Callable, List

import numpy as np

from pyspark.sql import Row
from programs.nodes.nodes import GeounitNode, getNodeAttr, hasNodeAttr
from programs.schema import schema as sk
from das_constants import CC

def makeHistRowsFromMultiSparse(node: Union[GeounitNode, dict],
                                schema: sk,
                                run_id: int = None,
                                row_recoder: Callable = None,
                                add_schema_name: bool = True,
                                microdata_field: str = CC.PRTCTD,
                                geocode_dict: Dict = None) -> List[Row]:
    """
    Converts a node's raw and/or protected histogram into a list of Spark Rows, where columns are the dimensions of the histogram
    and CC.PRTCTD and CC.ORIG are column names containing protected and raw counts respectively. If :microdata_field: is set (CC.PRTCTD/CC.ORIG), then
    instead of having count in that field, the corresponding number (i.e. equal to the count) is inserted in the Row list,
    and the field is discarded.
    :param node: GeounitNode or dict, the node, whose histograms are converted to list or Rows (to then convert to DataFrame)
    :param schema: histogram schema
    :param run_id: auxiliary field, to be keep track of the number of experimental run
    :param row_recoder: recoder class, if some recoding is desired between histogram variables and DataFrame (list of Rows) output columns
    :param add_schema_name: whether to mangle histogram variables name by adding schema name to that, so that they are not confused with desired output names in the recoder
    :param microdata_field: whether to proliferate rows to the histogram count (as opposed to just have a single row for each hist. var. combination with count in a column)
    :param geocode_dict: Geocode dictionary.
    :return:
    """

    data_present = []  # The list that tells whether the node has raw data, protected data or both. If yes, the data is in this list.
    if hasNodeAttr(node, CC.RAW):
        orig = getNodeAttr(node, CC.RAW).sparse_array
        data_present.append((orig, CC.ORIG))
    if hasNodeAttr(node, CC.SYN):
        protected = getNodeAttr(node, CC.SYN).sparse_array
        data_present.append((protected, CC.PRTCTD))

    # Collect (multiD) indices of all non-zero histogram counts, for one or both of protected/raw datasets
    indices = []
    for dataset in data_present:
        indices = indices + dataset[0].indices.tolist()

    # Leave only unique indices, we will have a Row per each index (each index corresponds to a combination of histogram variables)
    all_nonzero_indices = np.unique(indices)

    #print(f'Node indices: {all_nonzero_indices}')
    #print(f'Node orig counts: {orig.data}')
    #print(f'Node .data: {unit_syn.data}')

    rows = []

    if row_recoder is not None:
        if geocode_dict is not None:
            recoder = row_recoder(geocode_dict=geocode_dict)
        else:
            # To ensure backwards compatibility with old writers
            recoder = row_recoder()

    # Build the row list
    for ind in all_nonzero_indices:
        rowdict = {}

        # Add run_id
        if run_id is not None:
            rowdict['run_id'] = run_id

        # Add geocode
        rowdict[CC.GEOCODE] = getNodeAttr(node, CC.GEOCODE)

        # And protected count, or raw count, or both
        for dataset in data_present:
            rowdict[dataset[1]] = int(dataset[0][0, ind])

        # Add all the histogram variables from the schema
        cell = np.unravel_index(ind, schema.shape)
        for dim, level in enumerate(cell):
            dimcol = f"{schema.dimnames[dim]}"
            if add_schema_name:
                dimcol = dimcol + f"_{schema.name}"
            rowdict[dimcol] = str(level)

        protected_count = None

        # Produce microdata (i.e. remove the count column and instead have that number of identical rows)
        if microdata_field is not None:
            # Number of identical rows to add equal to the count (taking either protected count in field CC.PRTCTD, or raw count in field CC.ORIG)
            nrows2add = rowdict[microdata_field]
            # Remove the CC.PRTCTD or CC.ORIG count column, that has been used to calculate number of rows to add
            rowdict.pop(microdata_field, None)
        else:
            nrows2add = 1
            if CC.PRTCTD in rowdict:
                protected_count = rowdict[CC.PRTCTD]

        # Recode the histogram variables to output variables
        if row_recoder is not None:
            rowdict = recoder.recode(rowdict)
            if protected_count is not None:
                rowdict[CC.PRTCTD] = protected_count


        row = Row(**rowdict)
        rows.extend([row] * nrows2add)  # If microdata, then add more than one row, but number of records equal to the count in the histogram

    return rows

def makeHistRowsFromUnitMultiSparse(node: Union[GeounitNode, dict],
                                schema: sk,
                                rows: List[Row],
                                run_id: int = None,
                                row_recoder: Callable = None,
                                add_schema_name: bool = True,
                                microdata_field: str = CC.PRTCTD,
                                geocode_dict: Dict = None) -> List[Row]:
    """
    Converts a node's raw and/or protected histogram into a list of Spark Rows, where columns are the dimensions of the histogram
    and CC.PRTCTD and CC.ORIG are column names containing protected and raw counts respectively. If :microdata_field: is set (CC.PRTCTD/CC.ORIG), then
    instead of having count in that field, the corresponding number (i.e. equal to the count) is inserted in the Row list,
    and the field is discarded.
    :param node: GeounitNode or dict, the node, whose histograms are converted to list or Rows (to then convert to DataFrame)
    :param schema: histogram schema
    :param rows: List of Rows.
    :param run_id: auxiliary field, to be keep track of the number of experimental run
    :param row_recoder: recoder class, if some recoding is desired between histogram variables and DataFrame (list of Rows) output columns
    :param add_schema_name: whether to mangle histogram variables name by adding schema name to that, so that they are not confused with desired output names in the recoder
    :param microdata_field: whether to proliferate rows to the histogram count (as opposed to just have a single row for each hist. var. combination with count in a column)
    :param geocode_dict: Geocode dictionary.
    :return:
    """

    unit_syn = getNodeAttr(node, CC.UNIT_SYN).sparse_array

    # Collect (multiD) indices of all non-zero histogram counts, for one or both of protected/raw datasets
    indices = unit_syn.indices.tolist()

    # Leave only unique indices, we will have a Row per each index (each index corresponds to a combination of histogram variables)
    all_nonzero_indices = np.unique(indices)

    if row_recoder is not None:
        if geocode_dict is not None:
            recoder = row_recoder(geocode_dict=geocode_dict)
        else:
            # To ensure backwards compatibility with old writers
            recoder = row_recoder()

    # Build the row list
    for ind in all_nonzero_indices:
        rowdict = {}

        # Add geocode
        rowdict[CC.GEOCODE] = getNodeAttr(node, CC.GEOCODE)

        # And protected count, or raw count, or both
        rowdict[CC.PRTCTD] = int(unit_syn[0, ind])

        # Add all the histogram variables from the schema
        cell = np.unravel_index(ind, schema.shape)
        for dim, level in enumerate(cell):
            dimcol = f"{schema.dimnames[dim]}"
            rowdict[dimcol] = str(level)


        # Produce microdata (i.e. remove the count column and instead have that number of identical rows)
        if microdata_field is not None:
            # Number of identical rows to add equal to the count (taking either protected count in field CC.PRTCTD, or raw count in field CC.ORIG)
            nrows2add = rowdict[microdata_field]
            # Remove the CC.PRTCTD or CC.ORIG count column, that has been used to calculate number of rows to add
            rowdict.pop(microdata_field, None)
        else:
            nrows2add = 1

        #Only include vacant/GQ rows. TODO: parameterize or refactor this
        if int(rowdict['tenvacgq']) <= 3:
            continue

        # Recode the histogram variables to output variables
        rowdict = recoder.recode(rowdict)

        row = Row(**rowdict)
        rows.extend([row] * nrows2add)  # If microdata, then add more than one row, but number of records equal to the count in the histogram

    return rows
