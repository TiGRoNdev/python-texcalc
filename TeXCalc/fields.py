import re
from decimal import *

from .exceptions import TeXCalcException
from .defines import DEFAULT_DECIMAL_PRECISION


class Field:
    _type = str

    def __init__(self, *args, context=False, indexed=False, choices=None, default=None, **kwargs):
        self.__value = {}
        self._may_context = context
        self._may_indexed = indexed
        self._choices = choices
        self._default = default

    def __get__(self, instance, owner):
        try:
            return self.__value[instance._id]
        except KeyError:
            return None

    def __set__(self, instance, value):
        self.__value[instance._id] = {'value': self._default, 'context': False, 'index': False}

        if value is None:
            return

        try:
            self.__value[instance._id]['value'] = self._type(value)
        except:
            if (
                    self._may_context and not
            (re.fullmatch(r'/\d+/', str(value)) or re.fullmatch(r'@/\d+/@', str(value)))
            ):
                self.__value[instance._id]['value'] = str(value)
                self.__value[instance._id]['context'] = True
            elif self._may_indexed and value.replace('/', '').replace('@', '').isdigit():
                self.__value[instance._id]['value'] = int(value.replace('/', '').replace('@', ''))
                self.__value[instance._id]['index'] = True
            else:
                raise TeXCalcException.FieldError.BadFieldArgument(value=value)

        if self._choices:
            try:
                self.__value[instance._id]['value'] = self._choices[
                    self.__value[instance._id]['value']
                ]
            except KeyError:
                raise TeXCalcException.FieldError.BadChoicesMap(value=self.__value[instance._id]['value'])


class IntegerField(Field):
    _type = int


class FloatField(Field):
    _type = float


class DecimalField(Field):
    _type = Decimal

    def __init__(self, *args, precision=DEFAULT_DECIMAL_PRECISION, **kwargs):
        self.precision = precision
        super(DecimalField, self).__init__(*args, **kwargs)

    def __call__(self, value, index=False):
        getcontext().prec = self.precision
        return super(DecimalField, self).__call__(value, index=index)
