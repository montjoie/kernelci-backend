# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""All boot related celery tasks."""

import bson
import datetime
import io
import os

try:
    import simplejson as json
except ImportError:
    import json

import taskqueue.celery as taskc
import utils

CALLBACK_DUMP_PATH = "/var/www/images/callback"
LAVA_DUMP_PATH = os.path.join(CALLBACK_DUMP_PATH, "lava")


@taskc.app.task(name="callback-import-lava")
def callback_import_lava(json_obj, lab_name):
    """Just a wrapper around the real boot import function.

    This is used to provide a Celery-task access to the import function.

    :param json_obj: The JSON object with the values necessary to import the
    boot report.
    :type json_obj: dictionary
    :param db_options: The database connection parameters.
    :type db_options: dictionary
    :param mail_options: The options necessary to connect to the SMTP server.
    :type mail_options: dictionary
    :return tuple The return code; and the document id.
    """
    utils.LOG.info("Importing LAVA callback data for %s", lab_name)

    dump_dir = os.path.join(LAVA_DUMP_PATH, lab_name)
    now = datetime.datetime.now(tz=bson.tz_util.utc)

    dump_file_name = now.strftime('%Y-%m-%dT%H%M%S%f')
    dump_file_name += ".json"

    dump_file = os.path.join(dump_dir, dump_file_name)

    if not os.path.isdir(dump_dir):
        try:
            os.makedirs(dump_dir)
        except OSError:
            utils.LOG.error("Error creating dump directory %s", dump_dir)
            return

    utils.LOG.info("Writing LAVA callback data into %s", dump_file)
    with io.open(dump_file, mode="w", encoding="utf-8") as w_f:
        w_f.write(unicode(json.dumps(
            json_obj, indent=2, ensure_ascii=False, encoding="utf-8")))
