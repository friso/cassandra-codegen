import os

from abc import ABCMeta, abstractmethod
from enum import Enum
from collections import OrderedDict

from .generator import Generator, GeneratorRepresentable

class JavaType(GeneratorRepresentable):
    __metaclass__ = ABCMeta

    @staticmethod
    def classnamify(name):
        return ''.join([part.capitalize() for part in name.split('_')])

    @staticmethod
    def simple(name):
        return SimpleType(name)

    @staticmethod
    def map(keys, values):
        return MapType(keys, values)

    @staticmethod
    def list(entries):
        return OneDimensionalContainerType(entries, 'java.util.List')

    @staticmethod
    def set(entries):
        return OneDimensionalContainerType(entries, 'java.util.Set')

    @staticmethod
    def user_defined(name):
        return UserDefinedType(name)

class SimpleType(JavaType):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return self.name

class OneDimensionalContainerType(JavaType):
    def __init__(self, entries, type_name):
        self.entries = entries
        self.name = type_name

    def repr(self):
        return '{name}<{entries}>'.format(name=self.name, entries=self.entries.repr())

class MapType(JavaType):
    def __init__(self,keys,values):
        self.keys = keys
        self.values = values

    def repr(self):
        return 'java.util.Map<{keys},{values}>'.format(keys=self.keys.repr(),values=self.values.repr())

class UserDefinedType(JavaType):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return '{name}'.format(name=JavaType.classnamify(self.name))

class JavaFieldDefinition():
    def __init__(self, name, java_type, getter_format):
        self.name = name
        self.java_type = java_type
        self.getter_format = getter_format

    def _camelify(self, name):
        return ''.join(name.split('_')[:1] + [part.capitalize() for part in name.split('_')[1:]])

    @property
    def java_name(self):
        return self._camelify(self.name)

    @property
    def cql_name(self):
        return self.name

    def getter(self, variable):
        return self.getter_format.format(java_name=self.java_name, cql_name=self.cql_name, variable=variable)

class JavaTypeDefinition():
    def __init__(self, name, package):
        self.name = name
        self.package = package
        self.fields = []

    @property
    def java_name(self):
        return JavaType.classnamify(self.name)

    @property
    def cql_name(self):
        return self.name

    def add_field(self, name, java_type, getter):
        self.fields.append(JavaFieldDefinition(name, java_type, getter))

class JavaGenerator(Generator):
    def __init__(self, yaml_file, dir_name):
        super().__init__(yaml_file)

        for type_name, type_config in self.config.get('types', {}).items():
            self.add_file(
                '%s.java' % JavaType.classnamify(type_name),
                'java_type.j2',
                self._get_type(type_name, type_config),
                os.path.join(dir_name, self.config['options']['package'].replace('.', os.path.sep)))

        for table_name, table_config in self.config.get('tables', {}).items():
            self.add_file(
                '%s.java' % JavaType.classnamify(table_name),
                'java_class.j2',
                self._get_table(table_name, table_config),
                os.path.join(dir_name, self.config['options']['package'].replace('.', os.path.sep)))

    def _deep_config(self, type_config):
        return { 'type': type_config } if str == type(type_config) else type_config

    def _java_type(self, input_config, boxed=False):
        config = self._deep_config(input_config)
        transformers = {
            'ascii': lambda t: JavaType.simple('String'),
            'bigint': lambda t: JavaType.simple('Long' if boxed else 'long'),
            'blob': lambda t: JavaType.simple('java.nio.ByteBuffer'),
            'boolean': lambda t: JavaType.simple('Boolean' if boxed else 'boolean'),
            'counter': lambda t: JavaType.simple('Long' if boxed else 'long'),
            'decimal': lambda t: JavaType.simple('java.math.BigDecimal'),
            'double': lambda t: JavaType.simple('Double' if boxed else 'double'),
            'float': lambda t: JavaType.simple('Float' if boxed else 'float'),
            'inet': lambda t: JavaType.simple('java.net.InetAddress'),
            'int': lambda t: JavaType.simple('Integer' if boxed else 'int'),
            'text': lambda t: JavaType.simple('String'),
            'timestamp': lambda t: JavaType.simple('java.time.Instant'),
            'timeuuid': lambda t: JavaType.simple('java.util.UUID'),
            'uuid': lambda t: JavaType.simple('java.util.UUID'),
            'varchar': lambda t: JavaType.simple('String'),
            'varint': lambda t: JavaType.simple('java.math.BigInteger'),
            'list': lambda t: JavaType.list(self._java_type(t['entries'], True)),
            'map': lambda t: JavaType.map(self._java_type(t['keys'], True), self._java_type(t['values'], True)),
            'set': lambda t: JavaType.set(self._java_type(t['entries'], True))
        }

        if config['type'] in self.config.get('types', {}).keys():
            return JavaType.user_defined(config['type'])
        else:
            return transformers[config['type']](config)

    def _getter_format(self, input_config):
        config = self._deep_config(input_config)
        transformers = {
            'ascii': lambda t: '{variable}.getString("{cql_name}")',
            'bigint': lambda t: '{variable}.getLong("{cql_name}")',
            'blob': lambda t: '{variable}.getBytes("{cql_name}")',
            'boolean': lambda t: '{variable}.getBool("{cql_name}")',
            'counter': lambda t: '{variable}.getLong("{cql_name}")',
            'decimal': lambda t: '{variable}.getDecimal("{cql_name}")',
            'double': lambda t: '{variable}.getDouble("{cql_name}")',
            'float': lambda t: '{variable}.getDouble("{cql_name}")',
            'inet': lambda t: '{variable}.getInet("{cql_name}")',
            'int': lambda t: '{variable}.getInt("{cql_name}")',
            'text': lambda t: '{variable}.getString("{cql_name}")',
            'timestamp': lambda t: '{variable}.getDate("{cql_name}").toInstant()',
            'timeuuid': lambda t: '{variable}.getUUID("{cql_name}")',
            'uuid': lambda t:  '{variable}.getUUID("{cql_name}")',
            'varchar': lambda t: '{variable}.getString("{cql_name}")',
            'varint': lambda t: '{variable}.getVarint("{cql_name}")',
            'list': lambda t: '{variable}.getList("{cql_name}", %s.class)' % self._java_type(t['entries'], True).repr(),
            'map': lambda t: '{variable}.getMap("{cql_name}", %s.class, %s.class)' % (self._java_type(t['keys'], True).repr(), self._java_type(t['values'], True).repr()),
            'set': lambda t: '{variable}.getSet("{cql_name}", %s.class)' % self._java_type(t['entries'], True).repr()
        }

        if config['type'] in self.config.get('types', {}).keys():
            return 'new %s({variable}.getUDTValue("{cql_name}"))' % self._java_type(config).repr()
        else:
            return transformers[config['type']](config)

    def _get_type(self, name, config):
        result = JavaTypeDefinition(name, self.config['options']['package'])
        for field_name, type_config in config.items():
            result.add_field(field_name, self._java_type(type_config), self._getter_format(type_config))

        return result

    def _get_table(self, name, config):
        result = JavaTypeDefinition(name, self.config['options']['package'])
        for field_name, type_config in config['fields'].items():
            result.add_field(field_name, self._java_type(type_config), self._getter_format(type_config))

        return result
