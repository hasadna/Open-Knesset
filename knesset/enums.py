class Enum(object):
    @classmethod
    def get_keys(cls):
        return filter(lambda x: not x.startswith('_'), cls.__dict__.keys())

    @classmethod
    def get_values(cls):
        return map(lambda x: getattr(cls, x), cls.get_keys())

    @classmethod
    def as_choices(cls):
        _choices = cls.get_values()
        choices = []
        for choice in _choices:
            choices.append((choice, cls.get_key_from_value(choice)))

        return tuple(choices)

    @classmethod
    def inverted_choices(cls):
        _choices = cls.get_keys()
        choices = []
        for choice in _choices:
            choices.append((choice, getattr(cls, choice)))

        return tuple(choices)

    @classmethod
    def get_key_from_value(cls, value):
        for key, v in cls.__dict__.items():
            if value == v:
                return key

    @classmethod
    def get_value(cls, key):
        return getattr(cls, key)