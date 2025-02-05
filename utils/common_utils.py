from textwrap import fill
import re

from tabulate import tabulate
from more_itertools import chunked
from IPython.display import Markdown


def pprint(text, width=80):
    print(fill(text, width=width))


def md(text):
    return Markdown(text)


def remove_code_block(text):
    # Remove any code block indicators (e.g., ```python, ```json, etc.)
    response_text = re.sub(r"^```.*\n", "", text)  # Remove opening marker
    response_text = re.sub(r"```$", "", response_text)  # Remove closing marker
    return response_text.strip()


def peep(obj):
    attrs = [attr for attr in dir(obj) if not attr.startswith("_")]

    # Separate properties and methods
    properties = []
    methods = []

    for attr in attrs:
        if callable(getattr(obj, attr)):
            methods.append(attr)
        else:
            properties.append(attr)

    # Format into rows of 4 columns for each category
    def create_table_rows(items):
        return list(chunked(items, 4))

    # Print tables if they have content
    if properties:
        print("\nPublic attributes:")
        print(tabulate(create_table_rows(properties), tablefmt="fancy_grid"))

    if methods:
        print("\nPublic methods:")
        print(tabulate(create_table_rows(methods), tablefmt="fancy_grid"))
