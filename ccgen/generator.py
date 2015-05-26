from abc import ABCMeta, abstractmethod
import yaml
from collections import OrderedDict

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

class GeneratedFile():
    def __init__(self, name, template, data, directory=None):
        self.name = name
        self.template = template
        self.data = data
        self.directory = directory or '.'

class Generator():
    __metaclass__ = ABCMeta

    def __init__(self, yaml_file):
        self.config = yaml.load(open(yaml_file, 'r'), Loader=OrderedDictYAMLLoader)
        self.files = []

    def add_file(self, name, template, data, directory=None):
        self.files.append(GeneratedFile(name, template, data, directory))

class GeneratorRepresentable():
    __metaclass__ = ABCMeta

    @abstractmethod
    def repr(self):
        pass
