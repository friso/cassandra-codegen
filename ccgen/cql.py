from abc import ABCMeta, abstractmethod
from enum import Enum
from collections import OrderedDict

from .generator import Generator, GeneratorRepresentable

class CqlType(GeneratorRepresentable):
    __metaclass__ = ABCMeta

    @staticmethod
    def simple(cql_type):
        return SimpleType(cql_type)

    @staticmethod
    def map(keys, values):
        return MapType(keys, values)

    @staticmethod
    def list(entries):
        return OneDimensionalContainerType(entries, 'list')

    @staticmethod
    def set(entries):
        return OneDimensionalContainerType(entries, 'set')

    @staticmethod
    def user_defined(name):
        return UserDefinedType(name)

class SimpleType(CqlType):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return self.name

class OneDimensionalContainerType(CqlType):
    def __init__(self, entries, type_name):
        self.entries = entries
        self.name = type_name

    def repr(self):
        return '{name}<{entries}>'.format(name=self.name, entries=self.entries.repr())

class MapType(CqlType):
    def __init__(self,keys,values):
        self.keys = keys
        self.values = values

    def repr(self):
        return 'map<{keys},{values}>'.format(keys=self.keys.repr(),values=self.values.repr())

class UserDefinedType(CqlType):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return 'frozen<{name}>'.format(name=self.name)

class CqlOption(GeneratorRepresentable):
    def __init__(self, name, config):
        self.name = name
        self.stringified = self._optionify(config)

    def _optionify(self, config):
        if isinstance(config, dict):
            return "{ %s }" % ', '.join([ '%s: %s' % (self._optionify(k), self._optionify(v)) for k,v in config.items() ])
        elif str == type(config):
            return "'%s'" % config.replace("'", "''")
        else:
            return config

    def repr(self):
        return self.stringified

class FieldDefinition():
    def __init__(self, name, cql_type):
        self.name = name
        self.cql_type = cql_type

class TypeDefinition():
    def __init__(self, name):
        self.fields = []
        self.name = name

    def add_field(self, name, cql_type):
        self.fields.append(FieldDefinition(name, cql_type))

class ClusteringDefinition():
    def __init__(self, field_name, order):
        self.field_name = field_name
        self.order = order.upper()

class TableDefinition():
    def __init__(self, name):
        self.name = name
        self.fields = []
        self.partition_key = []
        self.clustering = []
        self.options = []

    def add_field(self, name, cql_type):
        self.fields.append(FieldDefinition(name, cql_type))

    def set_partition_key(self, names):
        self.partition_key = names

    def add_clustering(self, name, direction):
        self.clustering.append(ClusteringDefinition(name, direction))

    def add_option(self, name, config):
        self.options.append(CqlOption(name, config))

    @property
    def has_clustering(self):
        return len(self.clustering) > 0

    @property
    def has_options(self):
        return len(self.options) > 0

class CqlGenerator(Generator):
    def __init__(self, yaml_file, dir_name, file_name):
        super().__init__(yaml_file)

        self.cql_types = []
        self.cql_tables = []

        for type_name, type_config in self.config.get('types', {}).items():
            self._add_type(type_name, type_config)

        for table_name, table_config in self.config.get('tables', {}).items():
            self._add_table(table_name, table_config)

        self.add_file(file_name, 'cql.j2', self, dir_name)

    def _deep_config(self, type_config):
        return { 'type': type_config } if str == type(type_config) else type_config

    def _cql_type(self, input_config):
        config = self._deep_config(input_config)
        transformers = {
            'list': lambda t: CqlType.list(self._cql_type(t['entries'])),
            'map': lambda t: CqlType.map(self._cql_type(t['keys']), self._cql_type(t['values'])),
            'set': lambda t: CqlType.set(self._cql_type(t['entries']))
        }

        if config['type'] in self.config.get('types', {}).keys():
            return CqlType.user_defined(config['type'])
        else:
            return transformers.get(config['type'], lambda t: CqlType.simple(t['type']))(config)


    def _add_type(self, name, config):
        result = TypeDefinition(name)
        for field_name, type_config in config.items():
            result.add_field(field_name, self._cql_type(type_config))

        self.cql_types.append(result)

    def _add_table(self, name, config):
        result = TableDefinition(name)
        for field_name, type_config in config['fields'].items():
            result.add_field(field_name, self._cql_type(type_config))

        result.set_partition_key(config['partition_key'])

        for field_name, ordering in config.get('clustering', {}).items():
            result.add_clustering(field_name, ordering)

        for option_name, option_config in config.get('options', {}).items():
            result.add_option(option_name, option_config)

        self.cql_tables.append(result)
