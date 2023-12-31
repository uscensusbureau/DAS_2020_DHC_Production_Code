from pyspark.sql import functions as sf
import das_utils as du
from das_constants import CC
import analysis.constants as AC
import numpy as np
from pyspark.sql.functions import udf
from pyspark.sql.types import BooleanType, StringType

from programs.geographic_spines.define_spines import make_aian_ranges_dict

"""
Crosswalk Info:
Below are the geolevels that are available in the following S3 location:

${DAS_S3INPUTS}/2010/geounit_crosswalks/24vars/


Note that the getCrosswalkDF function performs additional concatenations
or other operations on the crosswalk codes to put them into the form we expect.


Central Path Geolevels:
BLOCK
BLOCK_GROUP
TRACT
TRACT_GROUP
COUNTY
STATE
NATION


Non-central Path Geolevels
CD        # Congressional District (111th)
SLDU      # State Legislative District (Upper Chamber) (Year 1)
SLDL      # State Legislative District (Lower Chamber) (Year 1)
VTD       # Voting District
COUSUB    # County Subdivision (FIPS)
SUBMCD    # Subminor Civil Division (FIPS)
UA        # Urban Areas
CBSA      # Metropolitan Statistical Area
METDIV    # Metropolitan Division
CSA       # Combined Statistical Area
UGA       # Urban Growth Area
PUMA      # Public Use Microdata Area
PLACE     # Place (FIPS)
ZCTA5     # ZIP Code Tabulation Area (5-digit)


GRFC Info:
${DAS_S3INPUTS}/2010/cefv2/pp10_grf_tab_ikeda_100219.csv

From this file, we can extract the land area (AREALAND) for each block
and join it with the population totals to calculate population density.
"""

def getCrosswalkDF(spark, columns, grfc_path, strong_mcd_states=CC.STRONG_MCD_STATES_DEFAULT, aian_areas=CC.DAS_AIAN_AREAS_CNSTAT,
                   aian_ranges_path=CC.AIAN_RANGES_PATH_DEFAULT, fed_airs=AC.FED_AIRS, prim_crosswalk={}):
    """
    Loads the 2010 crosswalk files that Some Human generated from the 2010 GRFC into a Spark DF

    Parameters
    ==========
    spark : SparkSession

    columns : str or list of str (default is None, which will return all columns in the file)
        - This determines which columns survive from the original crosswalk data file, as the function will
          only return a Spark DF with the columns listed here

    Returns
    =======
    a Spark DF containing crosswalk columns

    Notes
    =====
    - This function also generates a number of additional columns to expand the ease-of-use when aggregating
      blocks to form geographic units in different geographic levels.
        - e.g. Rather than COUNTY being the 3-digit FIPS code, the COUNTY column will concatenate both the
               2-digit STATE FIPS code and the 3-digit COUNTY FIPS code to create a 5-digit COUNTY code that
               is unique from all other 5-digit COUNTY codes.
    """
    sc = spark.builder.getOrCreate()
    crossdf = sc.read.csv(grfc_path, sep='|', header=True)
    # crosswalk = f"{DAS_S3ROOT}/2010/geounit_crosswalks/24vars/"
    # crossdf = spark.read.option("header", "true").csv(crosswalk)

    crossdf = crossdf.withColumn("STATE", sf.col("TABBLKST"))
    # generate unique counties
    crossdf = crossdf.withColumn("COUNTY", sf.concat(sf.col("STATE"), sf.col("TABBLKCOU")))

    # generate unique tract groups
    crossdf = crossdf.withColumn("TRACT_GROUP", sf.concat(sf.col("COUNTY"), crossdf.TABTRACTCE[0:4]))

    # generate unique tracts
    crossdf = crossdf.withColumn("TRACT", sf.concat(sf.col("COUNTY"), sf.col("TABTRACTCE")))

    # generate block group column
    crossdf = crossdf.withColumn("BLOCK_GROUP", crossdf.TABBLK[0:1])

    # generate unique block groups
    crossdf = crossdf.withColumn("BLOCK_GROUP", sf.concat(sf.col("TRACT"), sf.col("BLOCK_GROUP")))

    # generate unique blocks
    crossdf = crossdf.withColumn("BLOCK", sf.concat(sf.col("BLOCK_GROUP"), sf.col("TABBLK")))

    # add "geocode" column based on GEOID (which is the 16 digit block id)
    crossdf = crossdf.withColumn("geocode", sf.col('BLOCK'))

    # generate unique SLDLs (only unique if state fips has been prepended to the SLDL identifier)
    crossdf = crossdf.withColumn("SLDL", sf.concat(sf.col("STATE"), sf.col("SLDLST")))

    # generate unique SLDUs (only unique if state fips has been prepended to the SLDU identifier)
    crossdf = crossdf.withColumn("SLDU", sf.concat(sf.col("STATE"), sf.col("SLDUST")))

    # generate unique Congressional Districts (111th Congress) - only unique if state fips has been prepended to the CD identifier
    crossdf = crossdf.withColumn("CD", sf.concat(sf.col("STATE"), sf.col("CDCURFP")))

    # generate unique school districts (only unique if state fips has been prepended to the identifiers)
    crossdf = crossdf.withColumn("SDELM", sf.concat(sf.col("STATE"), sf.col("SDELMLEA")))
    crossdf = crossdf.withColumn("SDSEC", sf.concat(sf.col("STATE"), sf.col("SDSECLEA")))
    crossdf = crossdf.withColumn("SDUNI", sf.concat(sf.col("STATE"), sf.col("SDUNILEA")))

    # generate unique urban areas and urban growth areas (only unique if state prepended)
    crossdf = crossdf.withColumn("UA", sf.concat(sf.col("STATE"), sf.col("UACE")))
    crossdf = crossdf.withColumn("UGA", sf.concat(sf.col("STATE"), sf.col("UGACE")))

    # generate unique puma and place ids (only unique if state prepended)
    crossdf = crossdf.withColumn("PUMA", sf.concat(sf.col("STATE"), sf.col("PUMA")))
    crossdf = crossdf.withColumn("PLACE", sf.concat(sf.col("STATE"), sf.col("PLACEFP")))

    # generate unique county subdivisions (only unique if state and county prepended)
    crossdf = crossdf.withColumn("COUSUB", sf.concat(sf.col("COUNTY"), sf.col("COUSUBFP")))

    # generate unique subminor civil divisions (only unique if state, county, and county subdivisions prepended)
    crossdf = crossdf.withColumn("SUBMCD", sf.concat(sf.col("COUSUB"), sf.col("SUBMCDFP")))

    # voting districts appear to have a floating space (" ") character in every VTD code, so we'll remove them as they
    # don't appear in the BlockAssign files for VTD
    ### Update - 2019-06-25 - The floating space is a valid character in the 6-character VTD codes; the first character
    #                         isn't always a " ", so " " is just another part of the code.
    #crossdf = crossdf.withColumn("VTD1st", crossdf.VTD[0:1])

    # generate unique voting districts (only unique if state and county prepended)
    crossdf = crossdf.withColumn("VTD", sf.concat(sf.col("COUNTY"), sf.col("VTDST")))

    # create a column for the nation
    crossdf = crossdf.withColumn("US", sf.lit("Nation"))

    # Note: When using any of the columns from the next block, filter out IDs composed only of "9"'s
    aian_ranges_dict = make_aian_ranges_dict(aian_ranges_path, aian_areas)
    is_fed_air_udf = udf(lambda aiannhce: in_aian_class(aiannhce, fed_airs, aian_ranges_dict), BooleanType())
    is_aian_udf = udf(lambda aiannhce: in_aian_class(aiannhce, aian_areas, aian_ranges_dict), BooleanType())
    # aian_areas:
    crossdf = crossdf.withColumn("AIAN_AREAS", sf.when(is_aian_udf("AIANNHCE"), sf.col("AIANNHCE")).otherwise(CC.NOT_AN_AIAN_AREA))
    crossdf = crossdf.withColumn("FED_AIRS", sf.when(is_fed_air_udf("AIANNHCE"), sf.col("AIANNHCE")).otherwise(CC.NOT_AN_AIAN_AREA))
    # portions of Blocks/Tracts/States within aian_areas:
    crossdf = crossdf.withColumn("AIANBlock", sf.when(sf.col("AIAN_AREAS") != CC.NOT_AN_AIAN_AREA, sf.col("BLOCK")).otherwise(CC.NOT_AN_AIAN_BLOCK))
    crossdf = crossdf.withColumn("AIANTract", sf.col("AIANBlock")[0:11])
    crossdf = crossdf.withColumn("AIANState", sf.col("AIANTract")[0:2])
    # Define an off-spine entity (OSE) as Place in AIAN areas and/or non-strong-MCD states and MCD otherwise:
    strong_mcd_states = list(strong_mcd_states) if type(strong_mcd_states) == tuple else strong_mcd_states
    crossdf = crossdf.withColumn("OSE", sf.when((sf.col("AIAN_AREAS") == CC.NOT_AN_AIAN_AREA) & (sf.col("STATE").isin(strong_mcd_states)), sf.col("COUSUB")).otherwise(sf.col("PLACE")))
    crossdf = crossdf.withColumn("COUNTY_NSMCD", sf.when(sf.col("STATE").isin(strong_mcd_states), CC.STRONG_MCD_COUNTY).otherwise(sf.col("COUNTY")))
    crossdf = crossdf.withColumn("MCD", sf.when(sf.col("STATE").isin(strong_mcd_states), sf.col("COUSUB")).otherwise(sf.lit(CC.NOT_A_MCD)))

    crossdf = crossdf.withColumn(CC.GEOCODE15, sf.concat(sf.col("BLOCK").substr(1, 11), sf.col("BLOCK").substr(13, 4)))
    prim_udf = sf.udf(lambda geocode: prim_crosswalk_map(geocode, prim_crosswalk), StringType())
    crossdf = crossdf.withColumn(CC.GEOLEVEL_PRIM, prim_udf(CC.GEOCODE15))

    if columns is None:
        return crossdf
    # always want 'geocode' (aka Block ID, GEOID) in the crosswalk dataframe
    columns = np.unique(du.aslist(columns) + ['geocode']).tolist()
    crossdf = crossdf.select(columns)
    return crossdf

def prim_crosswalk_map(geocode, prim_crosswalk):
    return '' if geocode not in prim_crosswalk.keys() else prim_crosswalk[geocode]

def in_aian_class(aiannhce, aian_class, aian_ranges_dict):
    if aiannhce == CC.NOT_AN_AIAN_AREA:
        return False
    else:
        # Check if AIAN area catagory is included in the user's specification of AIAN areas:
        for aian_definition, aian_range in aian_ranges_dict.items():
            if aiannhce <= aian_range[1] and aiannhce >= aian_range[0]:
                return True if aian_definition in aian_class else False
    # The only way aiannhce is not in any of the aian_ranges should not occur:
    assert False, "AIANNHCE codes cannot be between 4990 and 4999"

def getStateAbbreviations():
    """
    Returns a dictionary of (FIPS code, State abbreviation)
    """
    state_abbrev = {
        "01": "AL",
        "02": "AK",
        "04": "AZ",
        "05": "AR",
        "06": "CA",
        "08": "CO",
        "09": "CT",
        "10": "DE",
        "11": "DC",
        "12": "FL",
        "13": "GA",
        "15": "HI",
        "16": "ID",
        "17": "IL",
        "18": "IN",
        "19": "IA",
        "20": "KS",
        "21": "KY",
        "22": "LA",
        "23": "ME",
        "24": "MD",
        "25": "MA",
        "26": "MI",
        "27": "MN",
        "28": "MS",
        "29": "MO",
        "30": "MT",
        "31": "NE",
        "32": "NV",
        "33": "NH",
        "34": "NJ",
        "35": "NM",
        "36": "NY",
        "37": "NC",
        "38": "ND",
        "39": "OH",
        "40": "OK",
        "41": "OR",
        "42": "PA",
        "44": "RI",
        "45": "SC",
        "46": "SD",
        "47": "TN",
        "48": "TX",
        "49": "UT",
        "50": "VT",
        "51": "VA",
        "53": "WA",
        "54": "WV",
        "55": "WI",
        "56": "WY",
        "72": "PR"
    }
    return state_abbrev


def getAreaDF(spark):
    """
    Returns a Spark DF containing the BLOCK geocodes and the Land and Water area columns

    Parameters
    ==========
    spark : SparkSession

    Returns
    =======
    a Spark DF

    Notes
    =====
    - Converts the AREALAND and AREAWATER columns from square meters to square miles
    - Used primarily for calculating Population Density
    """
    area_cols = ['AREALAND', 'AREAWATER']
    area = getGRFC(spark, columns=area_cols)
    for area_col in area_cols:
        area = area.withColumn(area_col, sf.col(area_col).cast("long")).persist()
        # calculation for converting square meters (current units for AREALAND from the GRFC) to square miles
        # square miles = square meters / 2,589,988
        # https://www.census.gov/quickfacts/fact/note/US/LND110210
        area = area.withColumn(area_col, sf.col(area_col) / sf.lit(2589988)).persist()

    area = area.withColumn("AREA_SQUARE_MILES", sf.expr(" + ".join(area_cols))).persist()
    return area


def getGRFC(spark, columns=None):
    """
    returns the GRFC columns as a Spark DataFrame

    Parameters
    ==========
    spark : SparkSession

    columns : str or list of str
        Default: None - return all columns


    Returns
    =======
    a Spark DataFrame containing information from the GRFC file
    """
    grfc_loc = "${DAS_S3INPUTS}/2010/cefv2/pp10_grf_tab_ikeda_100219.csv"

    grfc = spark.read.option("header", "true").csv(grfc_loc)

    grfc = grfc.withColumn('BLOCK', sf.concat(sf.col("TABBLKST"), sf.col("TABBLKCOU"), sf.col("TABTRACTCE"), sf.col("TABBLK")[0:1], sf.col("TABBLK")))
    grfc = grfc.withColumn('geocode', sf.col('BLOCK')).persist()

    if columns is None:
        columns = grfc.columns
    else:
        # want geocode, at least, as the join column
        columns = np.unique(du.aslist(columns) + ['geocode']).tolist()

    grfc = grfc.select(columns)

    return grfc
