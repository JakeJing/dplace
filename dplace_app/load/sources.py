# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from clldutils.text import split_text
from dplace_app.models import Source

_SOURCE_CACHE = {}


def get_source(ds):
    if ds.id not in _SOURCE_CACHE:
        try:
            o = Source.objects.get(year=ds.spec['year'], author=ds.spec['author'])
        except Source.DoesNotExist:
            o = Source.objects.create(
                name=ds.spec['name'],
                reference=ds.spec['citation'],
                year=ds.spec['year'],
                author=ds.spec['author'])
            o.save()
        _SOURCE_CACHE[ds.id] = o
    return _SOURCE_CACHE[ds.id]


def load_references(datasets):
    keys = set()
    for ds in datasets:
        for r in ds.references:
            if ':' in r.key:
                # skip keys with page numbers.
                continue

            # key is in the format Author, Year
            try:
                author, year = split_text(r.key, separators=',', strip=True)
                if (author, year) not in keys:
                    keys.add((author, year))
                    reference = Source.objects.create(
                        author=author, year=year, reference=r.citation)
                    logging.info("Saved new reference %s (%s)"
                                 % (reference.author, reference.year))
            except Exception as e:  # pragma: no cover
                logging.warn("Could not save reference for row %s: %s" % (str(r), e))
    return len(keys)
