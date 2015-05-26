import os
import yaml
import argparse
from jinja2 import Template, Environment, FileSystemLoader
from collections import OrderedDict
from functools import partial

# Inspired by: https://gist.github.com/enaeseth/844388
# We need this as ordering is important for example when
# defining user defined types that depend on each other.
class OrderedDictYAMLLoader(yaml.Loader):
    def __init__(self, *args, **kwargs):
        yaml.Loader.__init__(self, *args, **kwargs)

        self.add_constructor(u'tag:yaml.org,2002:map', type(self).construct_yaml_map)
        self.add_constructor(u'tag:yaml.org,2002:omap', type(self).construct_yaml_map)

    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(None, None,
                'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise yaml.constructor.ConstructorError('while constructing a mapping',
                    node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

def _cql_type(input, all_types):
    tp = { 'type': input } if str == type(input) else input
    tranformers = {
        'map': lambda t: {
            'type': 'map',
            'repr': 'map<{keys},{values}>'.format(**t)
            },
        'set': lambda t: { 'type': 'set', 'repr': 'set<{entries}>'.format(**t) },
        'list': lambda t: { 'type': 'list', 'repr': 'list<{entries}>'.format(**t) }
    }
    udt_transformer = lambda t: { 'type': t['type'], 'repr': 'frozen<{type}>'.format(**t) }
    simple_transformer = lambda t: { 'type': t, 'repr': t['type'] }
    default_transformer = udt_transformer if tp['type'] in all_types.keys() else simple_transformer
    
    return tranformers.get(tp['type'], default_transformer)(tp)

def _optionify(input):
    if isinstance(input, dict):
        return "{ %s }" % ', '.join([ '%s: %s' % (_optionify(k), _optionify(v)) for k,v in input.items() ])
    elif str == type(input):
        return "'%s'" % input.replace("'", "''")
    else:
        return input

def _camelify(name):
    return ''.join(name.split('_')[:1] + [part.capitalize() for part in name.split('_')[1:]])

def _classnamify(name):
    return ''.join([part.capitalize() for part in name.split('_')])

def _java_type(input, all_types, package):
    tp = { 'type': input } if str == type(input) else input
    tranformers = {
        'map': lambda t: 'java.util.Map<{keys},{values}>'.format(
            keys=_java_type(t['keys'], all_types, package),
            values=_java_type(t['values'], all_types, package)),
        'set': lambda t: 'java.util.Set<{entries}>'.format(
            entries=_java_type(t['entries'], all_types, package)),
        'list': lambda t: 'java.util.List<{entries}>'.format(
            entries=_java_type(t['entries'], all_types, package)),
            'ascii': lambda t: 'String',
            'bigint': lambda t: 'Long',
            'blob': lambda t: 'java.nio.ByteBuffer',
            'boolean': lambda t: 'Boolean',
            'counter': lambda t: 'Long',
            'decimal': lambda t: 'java.math.BigDecimal',
            'double': lambda t: 'Double',
            'float': lambda t: 'Float',
            'inet': lambda t: 'java.net.InetAddress',
            'int': lambda t: 'Integer',
            'text': lambda t: 'String',
            'timestamp': lambda t: 'java.util.Date',
            'timeuuid': lambda t: 'java.util.UUID',
            'uuid': lambda t: 'java.util.UUID',
            'varchar': lambda t: 'String',
            'varint': lambda t: 'java.math.BigInteger'
    }

    udt_transformer = lambda t: '{package}.{type}'.format(
        package=package,
        type=_classnamify(t['type']))

    return (udt_transformer if tp['type'] in all_types.keys() else tranformers.get(tp['type']))(tp)

def generate_cql(input):
    env = Environment(loader=FileSystemLoader('/Users/friso/code/cassandra-codegen/ccgen/templates/'))
    env.globals['cql_type'] = partial(_cql_type, all_types=input['types'])
    env.globals['optionify'] = _optionify
    template = env.get_template('cql.j2')
    return template.render(input=input)

def generate_java(input):
    env = Environment(loader=FileSystemLoader('/Users/friso/code/cassandra-codegen/ccgen/templates/'))
    env.globals['camelify'] = _camelify
    env.globals['classnamify'] = _classnamify
    env.globals['java_type'] = partial(_java_type, all_types=input['types'], package=input['options']['package'])

    type_template = env.get_template('java_type.j2')

    for name, fields in input['types'].items():
        print(type_template.render(name=name, fields=fields, package=input['options']['package']))

    return ""

def _main():
    args = _parse_args()
    for fn in args.files:
        input = yaml.load(open(fn, 'r'), Loader=OrderedDictYAMLLoader)
        print(generate_cql(input))
        # print(generate_java(input))

def _parse_args():
    parser = argparse.ArgumentParser(description='Generate CQL DDL and Java POJOs from YAML descriptions of Cassandra tables.')

    parser.add_argument(
        '--java', '-j', metavar='JAVA_SOURCE_DIR', type=str, required=False,
        help="Output directory for the generated Java source files. Directories for packages will be created underneath if they do not exist.")
    parser.add_argument(
        '--cql', '-c', metavar='CQL_SOURCE_FILE', type=str, required=False,
        help="Output directory for the generated CQL source files.")

    parser.add_argument(
        'files', metavar='YAML_FILES', type=str, nargs='+',
        help="YAML files with table descriptions to parse. Multiple files may be specified.")

    args = parser.parse_args()

    return args

if __name__ == '__main__':
    _main()
