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

"""All callback related celery tasks."""

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
def callback_import_from_lava(json_obj, lab_name, doc_id):
    """Just a wrapper around the real boot import function.

    This is used to provide a Celery-task access to the import function.

    :param json_obj: The JSON object with the values necessary to import the
    boot report.
    :type json_obj: dict
    :param lab_name: The name of the boot lab.
    :type lab_name: str
    :param doc_id: The boot document ID saved in the db.
    :type doc_id: str
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
