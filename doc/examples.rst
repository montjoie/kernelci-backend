.. _code_examples:

Code Examples
=============

All the following code examples are Python based and rely on the
`requests <http://docs.python-requests.org/en/latest/>`_ module.

Retrieving boot reports
-----------------------

.. literalinclude:: examples/get-all-boot-reports.py
    :language: python

.. literalinclude:: examples/get-all-failed-boot-reports.py
    :language: python

.. literalinclude:: examples/get-all-boot-reports-with-jobid.py
    :language: python

Handling compressed data
------------------------

If you need to directly handle the compressed data as returned by the server,
you can access it from the response object.

Keep in mind though that the `requests <http://docs.python-requests.org/en/latest/>`_
module automatically handles ``gzip`` and ``deflate`` compressions.

.. literalinclude:: examples/handling-compressed-data.py
    :language: python

Creating a new lab
------------------

.. note::

    Creation of new lab that can send boot reports is permitted only with an
    administrative token.

The response object will contain:

* The ``token`` that should be used to send boot lab reports.

* The ``name`` of the lab that should be used to send boot lab reports.

* The lab internal ``_id`` value.

.. literalinclude:: examples/create-new-lab.py
    :language: python

Sending a boot report
---------------------

.. literalinclude:: examples/post-boot-report.py
    :language: python

Sending a boot email report
---------------------------

.. literalinclude:: examples/trigger-boot-email-report.py
    :language: python

Uploading files
---------------

Upload a single file
********************

.. literalinclude:: examples/upload-single-file.py
    :language: python

Upload multiple files
*********************

The following example, before sending the files, will load them in memory.
With big files this might not be convenient.

.. literalinclude:: examples/upload-multiple-files.py
    :language: python

Upload multiple files - 2
*************************

The following example does not load the files in memory, but it relies on an
external library: `requests-toolbelt <https://pypi.python.org/pypi/requests-toolbelt/>`_.

.. literalinclude:: examples/upload-multiple-files-2.py
    :language: python

Uploading tests
---------------

Upload each single test schema
******************************

In this example each test schema - test suite, test set and test case - will be
uploaded one at the time and the results of each API request will be used to create
the next data to be sent.

Notes:

* The test suite data sent does not contain any test sets nor test cases: in this case the response status code will be 201.

.. literalinclude:: examples/single-tests-registration.py
    :language: python

Upload test suite, then test set and case together
**************************************************

In this example, the test suite is first registered, then the test set is created
embedding the test cases data.

Notes:

* The test suite data sent does not contain any test sets nor test cases: in this case the response status code will be 201.
* The test set data sent contains the test cases: in this case the response status code will be 202.
* The embedded test cases do not need the mandatory field ``test_suite_id``: it will be automatically added based on the value in the test set data.

.. literalinclude:: examples/test-suite-registration.py
    :language: python

Upload test suite, set and case all embedded
********************************************

In this example, the test suite data sent contains the test set and case data.

Notes:

* The test suite data contains all the necessary data: in this case the response status code will be 202 (the test set and cases will be imported asynchronously).
* Test set and test case do not need the mandatory ``test_suite_id`` key: it will be automatically added when being imported.

.. literalinclude:: examples/import-tests-all-embedded.py
    :language: python
