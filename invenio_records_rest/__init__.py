# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

u"""REST API for Records.

Invenio-Records-REST is a core component of Invenio which provides configurable
REST APIs for searching, retrieving, creating, modifying and deleting records.

The module uses Elasticsearch as the backend search engine and builds on top
a REST API that supports features such as:

- Search with sorting, filtering, aggregations and pagination, which allows the
  full capabilities of Elasticsearch to be used, such as geo-based quering.
- Record serialization and transformation (e.g., JSON, XML, DataCite,
  DublinCore, JSON-LD, MARCXML, Citation Style Language).
- Pluggable query parser.
- Tombstones and record redirection.
- Customizable access control.
- Configurable record namespaces for exposing different classes of records
  (e.g., authors, publications, grants, ...).
- CRUD operations for records with support for persistent identifier minting.
- Super-fast completion suggesters for implementing Google-like instant
  autocomplete suggestions.

The REST API follows best practices and supports, e.g.:

- Content negotiation and links headers.
- Cache control via ETags and Last-Modified headers.
- Optimistic concurrency control via ETags.
- Rate-limiting, Cross-Origin Resource Sharing, and various security headers.

The Search REST API works as **the** central entry point in Invenio for
accessing records. The REST API in combination with, e.g., Invenio-Search-UI/JS
allows to easily display records anywhere in Invenio and still only maintain
one single search endpoint.

For further extending the REST API take a look at the guide in Invenio-REST:
http://invenio-rest.readthedocs.io/en/latest/.

Basics
------

Records
~~~~~~~
A record in Invenio consists of a structured collection of fields and values
(metadata), which provides information about other data. The format of these
records is defined by a schema, which is represented in Invenio as JSONSchema.
Since the format of a record can change over time, it can be associated to
different JSONSchema versions. For more information on records and schemas
visit
`InvenioRecords <http://invenio-records.readthedocs.io/en/latest/index.html>`_.

Elasticsearch
~~~~~~~~~~~~~

Records are represented as JSON documents internally in Elasticsearch in an
index specified in the configuration. The record index can be created under a
given alias in order to allow for grouping and easy filtering.
The structure, internal fields of the documents, along with indexing preferences
can be defined by mappings, applied to specific indices. The layout of a mapping
can highly affect the search and indexing performance. A mapping is a JSON
file, which is loaded during initialization by Invenio-Search from a path
defined by an entrypoint.

Initialization
--------------

First create a Flask application:

>>> from flask import Flask
>>> app = Flask('myapp')
>>> app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
>>> app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

Initialize the required dependencies:

>>> from invenio_db import InvenioDB
>>> from invenio_rest import InvenioREST
>>> from invenio_pidstore import InvenioPIDStore
>>> from invenio_records import InvenioRecords
>>> from invenio_records_rest import InvenioRecordsREST
>>> from invenio_search import InvenioSearch
>>> from invenio_indexer import InvenioIndexer
>>> from invenio_records_rest.utils import PIDConverter
>>> ext_db = InvenioDB(app)
>>> ext_rest = InvenioREST(app)
>>> ext_pidstore = InvenioPIDStore(app)
>>> ext_records = InvenioRecords(app)
>>> ext_search = InvenioSearch(app)
>>> ext_indexer = InvenioIndexer(app)
>>> app.url_map.converters['pid'] = PIDConverter

In order for the following examples to work, you need to work within a Flask
application context so let’s push one:

>>> ctx = app.app_context()
>>> ctx.push()

Also, for the examples to work we need to create the database and tables (note
that in this example we use an in-memory SQLite database):

>>> from invenio_db import db
>>> db.create_all()

Configuration
-------------

`Namespaces` are an important concept in Invenio-Records-REST. You can think of
them as a way of grouping related metadata.
Imagine a `namespace` called ``records`` and another ``authors``. You could
use ``records`` to provide bibliographic metadata and ``authors`` for author
metadata.

In Invenio-Records-REST these namespaces are mapped to endpoints (i.e.,
``/records/`` or ``/authors/``), which are defined by routes and persistent
identifiers. Going back to our general example, a persistent identifier for
our namespace ``authors`` could be an `ORCID <https://orcid.org/>`_ and a
specific author would be identified by an endpoint like
``/authors/<AUTHOR_ORCID>``.

Among other preferences, routes, PID types, as well as search specific options
are customizable through configuration. The following dictionary shows the
default options in the out of the box minimal configuration.


>>> from invenio_indexer.api import RecordIndexer
>>> from invenio_search import RecordsSearch
>>> app.config.update({'RECORDS_REST_ENDPOINTS': dict(recid=dict(
...     pid_type='recid',
...     pid_minter='recid',
...     pid_fetcher='recid',
...     search_class=RecordsSearch,
...     indexer_class=RecordIndexer,
...     search_index=None,
...     search_type=None,
...     record_serializers={
...         'application/json': ('invenio_records_rest.serializers'
...                              ':json_v1_response'),
...     },
...     search_serializers={
...         'application/json': ('invenio_records_rest.serializers'
...                              ':json_v1_search'),
...     },
...     list_route='/records/',
...     item_route='/records/<pid(recid):pid_value>',
...     default_media_type='application/json',
...     max_result_window=10000,
...     error_handlers=dict(),
...     ))}
... )
>>> ext_records_rest = InvenioRecordsREST(app)

This configuration is not limited to only one endpoint, we could define as
many as we want. This is a rough idea on how ``/authors/`` would be implemented.

>>> app.config['RECORDS_REST_ENDPOINTS']['orcid'] = dict(
...    pid_type='orcid',
...    # ...,
...    list_route='/authors/',
...    item_route='/authors/<pid(orcid):pid_value>',
...    # ...,
... )

Now that we have configured the endpoint as we want, we can go ahead and install
the extension with:



Searching
---------
Invenio-Records-REST offers a rich set of fundamental search operations using
query strings, filters, sorting and pagination and also more advanced
operations including aggregations and suggestions.

`/records/?q=&size=10&page=1&sort=bestmatch&type=test`

Faceted Search
~~~~~~~~~~~~~~

Faceted search is enabled through filters and aggregations. It can be used to
obtain subsets of documents which meet certain criteria, group results by
categories, and provide an easy to navigate faceted menu.

`/records/?type=test&type=anoterhvalye/`


Aggregations
++++++++++++
By exposing the Elasticsearch API by default, we can use the advanced features it
provides, such as the `aggregations framework <https://www.elastic.co/guide/en/elasticsearch/reference/5.6/search-aggregations.html>`_.

These features include:

- `bucketing <https://www.elastic.co/guide/en/elasticsearch/reference/5.6/search-aggregations-bucket.html>`_
  "used to group the documents by a certain criterion".
- `metric <https://www.elastic.co/guide/en/elasticsearch/reference/5.6/search-aggregations-metrics.html>`_
  "used to create different types of metrics from values extracted from the documents
  being aggregated".
- `matrix <https://www.elastic.co/guide/en/elasticsearch/reference/5.6/search-aggregations-matrix.html>`_
  "used to produce a matrix result based on the values extracted from the requested document fields".
- `pipeline <https://www.elastic.co/guide/en/elasticsearch/reference/5.6/search-aggregations-pipeline.html>`_
  "used to aggregate the output of other aggregations and their associated metrics".


Filters
+++++++
Filters can be applied at different points of a query having different effects
for aggregations, but not for search queries.


To set the aggregations and filters you want you can modify the
`RECORDS_REST_FACETS`.

>>> from .facets import terms_filter
>>> app.config['RECORDS_REST_FACETS'] = {
...     'index_name': {
...         'aggs': {
...             'type': {'terms': {'field': 'type'}}
...         },
...         'post_filters': {
...             'type': terms_filter('type'),
...         },
...         'filters': {
...             'typefilter': terms_filter('type'),
...         }
...     }
... }

Sorting
~~~~~~~
Sorting is based by default on a relevance score, but this can
be configured as well. The following ways are possible:

- `Sorting by field values <https://www.elastic.co/guide/en/elasticsearch/guide/current/_sorting.html#_sorting_by_field_values>`_
- `Multilevel sorting <https://www.elastic.co/guide/en/elasticsearch/guide/current/_sorting.html#_multilevel_sorting>`_
- `Sorting on multilevel fields <https://www.elastic.co/guide/en/elasticsearch/guide/current/_sorting.html#_sorting_on_multivalue_fields>`_

This can be configured through the `RECORDS_REST_SORT_OPTIONS`:

>>> RECORDS_REST_SORT_OPTIONS = dict(
...    records=dict(
...        bestmatch=dict(
...            title='Best match',
...            fields=['_score'],
...        default_order='desc',
...            order=1,
...        ),
...        mostrecent=dict(
...        title='Most recent',
...            fields=['_created'],
...            default_order='asc',
...            order=2,
...        ),
...    )
... )

The default configuration will return the results sorted by the best match when
filtering by a given query, or sorted by their creation date when querying
all results:

>>> RECORDS_REST_DEFAULT_SORT = dict(
...    records=dict(
...        query='bestmatch',
...        noquery='mostrecent',
...    )
... )

"""

from __future__ import absolute_import, print_function

from .ext import InvenioRecordsREST
from .proxies import current_records_rest
from .version import __version__

__all__ = ('__version__', 'current_records_rest', 'InvenioRecordsREST')
