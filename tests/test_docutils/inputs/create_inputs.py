import yaml


class MyDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(MyDumper, self).increase_indent(flow, False)


def dump_tests(totest, path):
    data = {
        k: [{"in": i.splitlines(), "out": o.splitlines()} for i, o in vs]
        for k, vs in totest.items()
    }
    with open(path, "w") as handle:
        yaml.dump(data, handle, Dumper=MyDumper, default_flow_style=False, indent=2)


# totest = {}

# dump_tests(totest, "tests/docutils_test_data/test_inline_markup.yaml")
