"""A script: its classes are __main__.X when run, so steps defined here and
added from the __main__ block (directly or via a function it calls) are flagged."""

from codeupipe import Payload, Pipeline


class Local:
    def call(self, payload):
        return payload


def is_on(payload):
    return True


def library_builder():
    # Not reached from the __main__ block: an importer gets a real module name.
    p = Pipeline()
    p.add_filter(Local())
    return p


def main():
    p = Pipeline()
    p.add_filter(Local())  # expect: CUP-A006
    p.add_valve(is_on, Local())  # expect: CUP-A006 CUP-A006
    helper(p)
    return p.run(Payload({}))


def helper(p):
    p.add_tap(Local())  # expect: CUP-A006


if __name__ == "__main__":
    main()
    q = Pipeline()
    q.add_filter(Local())  # expect: CUP-A006
