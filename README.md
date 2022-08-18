# RTI STAR (Statistical Traffic Analysis Report)

STAR is a Python/Flask-based web application created to help examine traffic 
stop records for evidence of racial disproportionality and is based on the 
[Veil of Darkness method developed by Grogger & Ridgeway (2006)](http://www.rand.org/pubs/reprints/RP1253.html).


Quickstart
----------

You need a `default_config.py` file under `star/`. See 
`star/default_config.py-sample` for an example.

### Docker

Run the following commands to have your environment in a Docker container.

```
docker-compose build
docker-compose up
```

The `MANAGE_ARG` parameter is passed to the `python manage.py` command (defaults to `server`)

Or, run the following commands to bootstrap your environment.

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


Deployment
-------------

**Note**: You need credentials on `cds-mallard` and to be able to ssh into it. You will also need the cfs-production's user/host and the key saved in `~/.ssh/cfs-production-admin.pem`.

To deploy the app, do the following steps:

- ssh into mallard: `ssh <USER>@<CDS_MALLARD_HOST>`
- `sudo su gitlab-runner`
- ssh into cfs-production: `ssh -i ~/.ssh/cfs-production-admin.pem <CFS_PRODUCTION_USER>@<CFS_PRODUCTION_HOST>`
- Go to the `rti-star` directory: `cd rti-star`
- Review the current image's tag in the `docker-compose.yml` file: `cat docker-compose.yml`
    - Look for the image specified and see which tag `rti-star` has:
    ```yml
    services:
    app:
        image: rti-star:<TAG_NUMBER>
    ...
    ```
- Confirm there is a backup of this image in the `backup` folder: `cd backup && ls`
    - There should be a `rti-star<TAG_NUMBER>.tar.gz`
    - If there is not, then from the `rti-star` directory run `docker save rti-star:<TAG_NUMBER> | gzip > backup/rti-star<TAG_NUMBER>.tar.gz`

- From your local environment, build the image if you haven't already: `docker-compose build`
- give the image the appropriate name and tag: `docker tag star_app rti-star:<NEW_TAG_NUMBER>`
    - (`NEW_TAG_NUMBER` = 1 + `TAG_NUMBER`)
- save the updated docker image: `docker save rti-star:<NEW_TAG_NUMBER> | gzip > rti-star<NEW_TAG_NUMBER>.tar.gz`
- scp the new image to mallard: `scp path/to/rti-star<NEW_TAG_NUMBER>.tar.gz <USER>@<CDS_MALLARD_HOST>:~/`
- ssh into mallard: `ssh <USER>@<CDS_MALLARD_HOST>`
- scp the new image to cfs-production: `sudo scp -i ~/.ssh/cfs-production-admin.pem rti-star<NEW_TAG_NUMBER>.tar.gz <CFS_PRODUCTION_USER>@<CFS_PRODUCTION_HOST>:~/rti-star/backup`
- `sudo su gitlab-runner`
- ssh into cfs-production: `ssh -i ~/.ssh/cfs-production-admin.pem <CFS_PRODUCTION_USER>@<CFS_PRODUCTION_HOST>`
- Go to the `rti-star` directory: `cd rti-star`
- Load the new image: `docker load --input backup/rti-star<NEW_TAG_NUMBER>.tar.gz`
- `docker-compose down`
- Update the `docker-compose.yml` file to the new tag: `vi docker-compose.yml`:
    ```yml
    services:
    app:
        image: rti-star:<NEW_TAG_NUMBER>
    ...
    ```
- `docker-compose up - d`


Licensing
---------
This software is released under the BSD 3-Clause License with the exception of 
files under the `star/static/vendor/` directory. Please read LICENSE.txt for 
details.

All files under `star/static/vendor/` are licensed under their respective
license agreements.
