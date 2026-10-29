# codeupipe-add

`codeupipe add` for Python: it makes the files of one component. The
contract is [conformance/ADD.md](../../conformance/ADD.md), and the
Python command passes all its cases (`python conformance/add.py python:add`).

```bash
python -m codeupipe_add filter Discount src/pricing --description "Takes a rate off the price."
```

```
src/pricing/discount_filter.py
tests/test_discount_filter.py
```

- **The kinds** are `filter`, `predicate`, `tap`, `hook` and `pipeline`.
- **The role is added** when the name does not end with it: `filter Discount`
  gives `DiscountFilter`. `at_least` and `audit-log` give `AtLeast...` and
  `AuditLog...`.
- **The component does nothing**, and passes the linters in strict mode.
- **The test fails on purpose**, with `Write the acceptance case for
  DiscountFilter.` Start there.
- **A file is never written over.** If one of the two exists, nothing is
  written, and the exit code is 1.

Run it in the root of the project. The test imports the component by its
module path from the root (`from src.pricing.discount_filter import
DiscountFilter`), so the root must be on the import path of the tests, as it
is when pytest runs there with `PYTHONPATH=.` or with a package install.

Exit code: **0** the files are made, **1** a file exists, **2** the
arguments cannot be used. Nothing is written on 1 or 2.

The version is below 1.0: the package is not stable yet. It is not on PyPI.

## Development

The command is a codeupipe pipeline of five Filters,
[codeupipe_add/add_pipeline.py](codeupipe_add/add_pipeline.py). Its tests
are in `tests/add/`, and the conformance cases in `conformance/add/`.

## License

Apache License 2.0.
