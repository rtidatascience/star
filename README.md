# RTI STAR (Statistical Traffic Analysis Report)

STAR is a Python/Flask-based web application created to help examine traffic 
stop records for evidence of racial disproportionality and is based on the 
[Veil of Darkness method developed by Grogger & Ridgeway (2006)](http://www.rand.org/pubs/reprints/RP1253.html).


Quickstart
----------

You need a `default_config.py` file under `star/`. See 
`star/default_config.py-sample` for an example.

Run the following commands to bootstrap your environment.

```
pip install -r requirements.txt
python3 ./manage.py server
```

Shell
-----

To open the interactive shell, run:

    python3 ./manage.py shell

By default, you will have access to `app`.


Running Tests
-------------

To run all tests, run:

    py.test


Licensing
---------
This software is released under the BSD 3-Clause License with the exception of 
files under the `star/static/vendor/` directory. Please read LICENSE.txt for 
details.

All files under `star/static/vendor/` are licensed under their respective
license agreements.
