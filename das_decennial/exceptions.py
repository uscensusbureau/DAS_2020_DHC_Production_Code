""" Module for implementing exceptions
2019-04-09 - Created by Some Human
2021-02-01 - Moved to das_decennial directory. Some Human
"""

import logging

class Error(Exception):
    """Base class for DAS exceptions."""

    def __init__(self, msg: str = '') -> None:
        """Logs all exceptions that are created."""
        self.message = msg
        logging.error(msg)
        super().__init__(msg)

    def __repr__(self) -> str:
        return self.message

    __str__ = __repr__


class DASConfigError(Error):
    """ Errors resulting from parsing the config file"""

    def __init__(self, msg: str, option: str, section: str) -> None:
        if option is not None:
            message = f"{msg}: No option '{option}' in config section: [{section}]"
        else:
            message = f"{msg}: No section '{section}' in config file"
        super().__init__(message)
        self.option = option
        self.section = section
        self.args = (option, section)


class DASValueError(Error):
    def __init__(self, msg: str, value) -> None:
        super().__init__(f"{msg}: value '{value}' is invalid")
        self.value = value
        self.args = (value, )


class DASConfigValdationError(Exception):
    """ Errors resulting from parsing the config file"""

    def __init__(self, msg: str, options: tuple, section: str) -> None:
        Exception.__init__(self, f"{msg} in config section/options [{section}]/{','.join(options)}")
        logging.error(msg)


class IncompatibleAddendsError(Error):
    """ Errors when two objects of different type or with unaddable attributes are added"""

    def __init__(self, msg: str, attrname: str, addend1attr, addend2attr) -> None:
        super().__init__(f"{msg} cannot be added: addends have different {attrname}: {addend1attr} != {addend2attr}")
        self.attrname = attrname
        self.addend1attr = addend1attr
        self.addend2attr = addend2attr
        self.args = (attrname, addend1attr, addend2attr)

class NodeRDDValidationError(Exception):
    """ Error for when some elements (nodes) of RDD fail indicated criteria"""

    def __init__(self, msg: str, sample_msg: str, sample) -> None:
        Exception.__init__(self, f"{msg}\n{sample_msg} {sample}")
        logging.error(msg)
        self.msg = msg
        self.sample_msg = sample_msg
        self.sample = sample


class RandomGurobiLicenseError(Exception):
    """ Intentionally induced error to allow exercising of the Gurobi optimizer license acquisition process.

    Attributes:
        msg -- explanation of the error
    """

    def __init__(self, msg: str) -> None:
        Exception.__init__(self, f"{msg}\n")
        logging.error(msg)
        self.msg = msg

class GurobiLicenseError(Exception):
    """ Signalled when a gurobi license cannot be acquired

    Attributes:
        msg -- explanation of the error
    """

    def __init__(self, msg: str) -> None:
        Exception.__init__(self, f"{msg}\n")
        logging.error(msg)
        self.msg = msg
