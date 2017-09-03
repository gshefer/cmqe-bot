import os
import yaml


class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    @classmethod
    def attributize_dict(cls, obj):
        if isinstance(obj, dict):
            attr_dict = cls()
            for key, value in obj.items():
                attr_dict[key] = cls.attributize_dict(value)
            return attr_dict
        return obj


class Singleton(type):

    _instances = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self]


class conf(object):

    __metaclass__ = Singleton
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.yaml')

    def __init__(self, *args, **kwargs):
        self.reload()

    def reload(self):
        if not os.path.exists(self.CONFIG_FILE):
            raise IOError('Config file does not exist, please generate it as '
                          '{} from the template ({}.template)'.format(self.CONFIG_FILE))
        with open(self.CONFIG_FILE, 'r') as confile:
            self._data = AttributeDict.attributize_dict(yaml.load(confile))

    def __getitem__(self, key):
        return self._data[key]

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.__getitem__(name)


if __name__ == '__main__':

    # UNITEST

    print conf().github, conf().users
