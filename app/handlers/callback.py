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

"""The RequestHandler for /callback URLs."""

import tornado.web

try:
    import simplejson as json
except ImportError:
    import json

import handlers.base as hbase
import handlers.common.query
import handlers.common.token
import handlers.response as hresponse
import models
import models.boot as mboot
import models.token as mtoken
import taskqueue.tasks.callback as taskq
import utils.boot
import utils.db


class CallbackException(Exception):
    """Class for handling internal callback exceptions"""
    def __init__(self, msg, code):
        self.msg = msg
        self.code = code

    def __str__(self):
        return repr(self.msg)


class CallbackHandler(hbase.BaseHandler):
    """Base handler for the /callback URLs."""

    def __init__(self, application, request, **kwargs):
        super(CallbackHandler, self).__init__(application, request, **kwargs)

    @staticmethod
    def _valid_keys(method):
        """Return the valid keys for the JSON response.

        Subclasses should provide their own method. It should return either a
        list or a dictionary.
        """
        return None

    @staticmethod
    def _token_validation_func():
        # Reuse the same token logic validation for the boot resource.
        return handlers.common.token.valid_token_bh

    def execute_get(self, *args, **kwargs):
        return hresponse.HandlerResponse(501)

    def execute_delete(self, *args, **kwargs):
        return hresponse.HandlerResponse(501)

    def execute_put(self, *args, **kwargs):
        return hresponse.HandlerResponse(501)

    def execute_post(self, *args, **kwargs):
        """Execute the POST pre-operations.

        Checks that everything is OK to perform a POST.
        """
        response = None
        valid_token, token = self.validate_req_token("POST")

        if valid_token:
            valid_request = handlers.common.request.valid_post_request(
                self.request.headers, self.request.remote_ip)

            if valid_request == 200:
                try:
                    json_obj = json.loads(
                        self.request.body.decode("utf-8"),
                        encoding="utf-8")

                    kwargs["json_obj"] = json_obj
                    kwargs["token"] = token

                    response = self._post(*args, **kwargs)
                except ValueError, ex:
                    self.log.exception(ex)
                    error = "No JSON data found in the POST request"
                    self.log.error(error)
                    response = hresponse.HandlerResponse(422)
                    response.reason = error
            else:
                response = hresponse.HandlerResponse(valid_request)
                response.reason = (
                    "%s: %s" %
                    (
                        self._get_status_message(valid_request),
                        "Use %s as the content type" % self.content_type
                    )
                )
        else:
            response = hresponse.HandlerResponse(403)

        return response

    def _post(self, *args, **kwargs):
        response = hresponse.HandlerResponse()

        try:
            lab_name = self.get_query_argument(models.LAB_NAME_KEY)
            req_token = kwargs["token"]

            valid_lab, error = self._is_valid_token(req_token, lab_name)
            if valid_lab:
                try:
                    response.status_code = 202
                    response.reason = "Request accepted and being imported"
                    doc_id = self._execute_callback(
                        kwargs["json_obj"], lab_name)
                except CallbackException as ex:
                    response.status_code = ex.code
                    response.reason = ex.msg
            else:
                response.status_code = 403
                response.reason = (
                    "Provided authentication token is not associated with "
                    "lab '%s' or is not valid" % lab_name)

            response.errors = error
        except tornado.web.MissingArgumentError:
            response.status_code = 400
            response.reason = "Missing lab name in query string"

        return response

    def _is_valid_token(self, req_token, lab_name):
        """Make sure the token used to perform the POST is valid.

        We are being paranoid here. We need to make sure the token used to
        post is really associated with the provided lab name.

        To be valid to post boot report, the token must either be an admin
        token or a valid token associated with the lab.

        :param req_token: The token string from the request.
        :type req_token: str
        :param lab_name: The name of the lab to check.
        :type lab_name: str
        :return True if the token is valid, False otherwise.
        """
        valid_lab = False
        error = None

        lab_doc = utils.db.find_one2(
            self.db[models.LAB_COLLECTION], {models.NAME_KEY: lab_name})

        if lab_doc:
            lab_token_doc = utils.db.find_one2(
                self.db[models.TOKEN_COLLECTION], lab_doc[models.TOKEN_KEY])

            if lab_token_doc:
                lab_token = mtoken.Token.from_json(lab_token_doc)
                if req_token.is_admin:
                    valid_lab = True
                    self.log.warn(
                        "Received callback POST request from an admin token")
                    error = (
                        "Using an admin token to send boot reports: "
                        "use the lab token")
                elif (req_token.token == lab_token.token and
                        not lab_token.expired):
                    valid_lab = True
                else:
                    self.log.warn(
                        "Provided token (%s) is not associated with "
                        "lab '%s' or is not valid",
                        req_token, lab_name
                    )

        return valid_lab, error

    def _execute_callback(self, json_obj, lab_name):
        """A wrapper for the real callback execution logic.

        This should be an async operation.

        :param json_obj: The JSON data to parse.
        :type json_obj: dict
        :param lab_name: The name of the boot lab.
        :type lab_name: str
        :return The boot report id.
        """
        pass


class LavaCallbackHandler(CallbackHandler):
    """Handler specialized to parse LAVA callbacks.

    Bound to /callback/lava
    """

    @staticmethod
    def _valid_keys(method):
        return models.LAVA_CALLBACK_VALID_KEYS.get(method, None)

    @staticmethod
    def to_boot_document(data, lab_name):
        """Transform the data found in the paylond into a valid BootDocument.

        :param data: The JSON payload.
        :type data: dict
        :param lab_name: The name of the boot lab.
        :type lab_name: str
        :return A BootDocument
        """
        metadata = data.get("metadata")
        get_func = metadata.get
        if metadata:
            defconfig = get_func("kernel.defconfig_base")
            defconfig_full = get_func("kernel.defconfig") or \
                get_func("kernel.defconfig_base")
            return mboot.BootDocument(
                get_func("device.type"),
                get_func("kernel.tree"),
                get_func("kernel.version"),
                defconfig,
                lab_name,
                get_func("git.branch"),
                defconfig_full=defconfig_full,
                arch=get_func("job.arch")
            )
        else:
            raise CallbackException("No metadata found", 400)

    def find_previous_boot_report(self, boot_doc):
        return utils.boot.find_previous_boot_report(boot_doc, self.db)

    def save_boot_report(self, boot_doc):
        return utils.db.save2(self.db, models.BOOT_COLLECTION, boot_doc)

    def _execute_callback(self, json_obj, lab_name):
        new_doc = self.to_boot_document(json_obj, lab_name)
        prev_doc = self.find_previous_boot_report(new_doc)

        if prev_doc:
            doc_id = prev_doc.id
        else:
            ret_val, doc_id = self.save_boot_report(new_doc)
            if ret_val == 500:
                raise CallbackException("Error saving boot document", 500)

        taskq.callback_import_from_lava.apply_async([
            json_obj,
            lab_name,
            doc_id
        ])

        return doc_id
