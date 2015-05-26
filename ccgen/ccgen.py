import os
import argparse

from jinja2 import Template, Environment, FileSystemLoader

from .cql import CqlGenerator
from .java import JavaGenerator
from .generator import Generator

def _write_file(name, directory, contents):
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(os.path.join(directory, name), 'w', encoding='utf-8') as f:
        f.write(contents)

def _main():
    args = _parse_args()
    cql_dir, cql_file = os.path.split(args.cql)
    java_dir = args.java

    env = Environment(loader=FileSystemLoader('/Users/friso/code/cassandra-codegen/ccgen/templates/'))
    for fn in args.files:
        cql_generator = CqlGenerator(fn, cql_dir, cql_file)
        for f in cql_generator.files:
            template = env.get_template(f.template)
            _write_file(f.name, f.directory, template.render(data=f.data))

        java_generator = JavaGenerator(fn, java_dir)
        for f in java_generator.files:
            template = env.get_template(f.template)
            _write_file(f.name, f.directory, template.render(data=f.data))

def _parse_args():
    parser = argparse.ArgumentParser(description='Generate CQL DDL and Java POJOs from YAML descriptions of Cassandra tables.')

    parser.add_argument(
        '--java', '-j', metavar='JAVA_SOURCE_DIR', type=str, required=False, default='.',
        help="Output directory for the generated Java source files. Directories for packages will be created underneath if they do not exist.")
    parser.add_argument(
        '--cql', '-c', metavar='CQL_SOURCE_FILE', type=str, required=False, default='./create-script.cql',
        help="Output directory for the generated CQL source files.")

    parser.add_argument(
        'files', metavar='YAML_FILES', type=str, nargs='+',
        help="YAML files with table descriptions to parse. Multiple files may be specified.")

    args = parser.parse_args()

    return args

if __name__ == '__main__':
    _main()
