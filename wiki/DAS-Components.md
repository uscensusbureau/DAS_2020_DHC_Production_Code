The internal Census Bureau DAS implementation is divided among many
different GIT repositories, arranged within the root `das_decennial`
repo as submodules. The source code included in this release consists
of all the source source code modules used in executing the DAS for
that production run (on 2020 and 2010 Census Edited Files). We
flattened references to code in different repositories into a single
directory tree. This page summarizes the individual components found
in this flattened tree, marking those that constitute separate GIT
repositories in the current internal DAS
repository.

* `configs` contains default configuration files used by the DAS itself, such as INI files read by Python
* `das_framwework/ctools` (**repo**) common tools for working with Census data
* `das_framework` (**repo**) contains the general (read/protect/write) framework of the DAS engine
* `programs/nodes` implements the classes for the geographic nodes, instances of which represent a specific geographic location at a specific level of the geographic hierarchy, with attributes representing, for example, its privacy-protected measurements and, if available, privacy-protected microdata
* `programs/geographic_spines` implements the representation of the geographic hierarchy used by the Top-Down Algorithm (TDA), including optimization of the spine to reduce error in selected off-spine geographies
* `programs/queries` implements the DAS Query classes (especially DPQuery) which are the basic units of disclosure avoidance in the DAS
* `programs/schemas` describes the query and result schemas for specific queries
* `programs/workload` contains query workloads used by the TDA for different data products
* `programs/optimization` implements code for generating microdata (represented as `numpy` `ndarray` data structures, interpreted as histograms) with minimum distance to the noisy measurements (using the `Gurobi` solver)
* `programs/invariants` implements the representation of invariants used in the optimization process
* `programs/constraints` implements the various constraints applied during the optimization process for different Census products
* `programs/strategies` includes objects specifying the ordering of query processing for linear solving, rounding, and other methods
* `programs/engine` implements the Top-Down Algorithm (TDA) used for Decennial disclosure avoidance, coordinating the interplay between the other major DAS "protect"-step processes (e.g., taking of noisy measurements, nodes, optimization, queries)
* `programs/reader` reads input files (the CEF files and the geographic files) and transforms them into the geographic tree-of-histogram representation expected by the processing steps implemented in `programs/engine`
* `programs/writers` converts from the Block-level histogram objects generated by `engine` to microdata-formatted MDF files suitable for downstream consumption for, e.g., Census tabulation
* `programs/validator` checks that the DAS outputs satisfies the required constraints, including *invariants* to be unchanged by DA (such as total population counts) and consistency with counts in the 2020 Redistricting data release
* `programs/utilities` contains utility code, e.g. for the geo hierarchy and numpy
* `programs/metrics` implements tests to evaluate errors resulting from a single application of the TDA
* `programs/experiment` provides abstractions for running experiments testing varying workloads, strategies, and other algorithms in the TDA

Broadly speaking, the DAS code flows - as organized by
`das_framework` - from `reader` to `engine` to `writers`, with the
other subfolders playing supporting roles and defining objects used in
one or several of these major steps.
