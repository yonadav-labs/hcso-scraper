# Hillsborough County Sheriff Scraper

## About

This repository contains Python code for two applications that scrape arrest
records from the Hillsborough County Sheriff's Office website.  One application
is a script that currently runs once per day and sends the the scraped arrest
records to a configurable email address.  The other is a simple web application
that allows a user to select a date range over which arrest records will be
returned.

## Building and Running

These applications have been built and run using docker.  There is a `Makefile`
that is used to do this.  You can build and then run the cron application with
the following commands:

    $ make build-cron
    $ make run-cron

Similarly, you can build and run the web application with these commands:

    $ make build-web
    $ make run-web

## Development and Deployment Workflow

These applications are running on a host whose IP address is currently
45.77.115.74. 

You can then edit, run, commit and push code normally.  When you are ready to
deploy the code to the server, ssh into the machine and `cd` into the working
copy of the code:

    $ ssh root@45.77.115.74
    $ cd hillsborough-sheriff-scraper

Then pull the most recent changes:

    $ git pull

Once that is done, you can then build and run the applications using the `make`
commands given above.
