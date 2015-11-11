# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import pytest
from flask import Flask
from flask_cli import FlaskCLI
from invenio_db import InvenioDB, db
from invenio_pidstore import InvenioPIDStore
from invenio_pidstore.resolver import Resolver
from invenio_records import InvenioRecords
from invenio_records.api import Record
from invenio_rest import InvenioREST
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from invenio_records_rest import InvenioRecordsREST


@pytest.fixture()
def app(request):
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()
    app = Flask('testapp', instance_path=instance_path)
    app.config.update(
        TESTING=True,
        SERVER_NAME='localhost:5000',
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'
        )
    )
    FlaskCLI(app)
    InvenioDB(app)
    InvenioREST(app)
    InvenioRecords(app)
    InvenioPIDStore(app)
    InvenioRecordsREST(app)

    with app.app_context():
        if not database_exists(str(db.engine.url)) and \
           app.config['SQLALCHEMY_DATABASE_URI'] != 'sqlite://':
            create_database(db.engine.url)
        db.drop_all()
        db.create_all()

    def finalize():
        with app.app_context():
            db.drop_all()
            if app.config['SQLALCHEMY_DATABASE_URI'] != 'sqlite://':
                drop_database(db.engine.url)
            shutil.rmtree(instance_path)

    request.addfinalizer(finalize)
    return app


@pytest.fixture(scope='session')
def resolver():
    """Create a persistent identifier resolver."""
    return Resolver(pid_type='recid', object_type='rec',
                    getter=Record.get_record)
