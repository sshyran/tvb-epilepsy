from collections import OrderedDict

from tvb_epilepsy.base.constants.config import CalculusConfig
from tvb_epilepsy.base.utils.log_error_utils import raise_value_error
from tvb_epilepsy.base.utils.data_structures_utils import formal_repr, sort_dict


class Parameter(object):

    def __init__(self, name="Parameter", low=CalculusConfig.MIN_SINGLE_VALUE, high=CalculusConfig.MAX_SINGLE_VALUE,
                 p_shape=(), **kwargs):
        if isinstance(name, basestring):
            self.name = name
        else:
            raise_value_error("Parameter type " + str(name) + " is not a string!")
        if low < high:
            self.low = low
            self.high = high
        else:
            raise_value_error("low (" + str(low) + ") is not smaller than high(" + str(high) + ")!")
        if isinstance(p_shape, tuple):
            self.__p_shape = p_shape
        else:
            raise_value_error("Parameter's " + str(self.name) + " p_shape="
                              + str(p_shape) + " is not a shape tuple!")

    @property
    def p_shape(self):
        return self.__p_shape

    def __repr__(self,  d=OrderedDict()):
        nKeys = len(d)
        for ikey, key in enumerate(["name", "low", "high", "shape"]):
            d.update({str(nKeys+ikey) + ". " + key: str(getattr(self, key))})
        return d

    def __str__(self):
        return formal_repr(self, self.__repr__())
