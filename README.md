# Tangled Web

Tools to publish Gramps data on a WordPress website

Use these tools if you want to publish your Gramps data on a self-hosted WordPress site. It is assumed you know the basics of website maintenance, including uploading an unpacking a directory on a website, as well as installing and activating WordPress plugins.

To see an example of a Tangled Web instance, visit https://www.boldts.net/boldts-molls/.

This is version 0.9. If you're interested in using these tools, please first evaluate it on a test server and inspect the code. I would appreciate any suggestions for improvements.

Installation
============

Gramps
------

Copy the directory "TangledWeb" from directory "Gramps" to the Gramps plugin directory on your computer. On a Linux system, that's typically "~/.gramps/gramps51/plugins".

WordPress
---------

Copy the dirctory "TangledWeb" from directory "WordPress" to directory "wp-content/plugins" on your server.

Usage
=====

Gramps
------

Click on "Reports", then on "Web Pages", then on "Export to Tangled Web...". When satisfied with the options, click on "OK". A set of files are then created in the destination folder.

Once the destination folder is created, you then copy that data to the server. Typically, you will compress that directory into a zip or tar.gz file, which you then extract on the server.

WordPress
---------

On the WordPress dashboard on your website, click on "Plugins". Activate the "Tangled Web" plugin. Then click on the Tangled Web "Settings".

You'll need to create a new Tangled Web instance. In the "Instance Id" column, enter an identifier for this instance. For "Directory", enter the name of the directory with the Tangled Web data. Click on "Add Table". This loads the data into the index.

To display the data, create a new page. Add the following shortcode to the page content:

[tangled-web id='instance']

where 'instance' is the instance id specified in the settings.

If you want to select what to display, use the "show" option, as in:

[tangled-web id='instance' show='photo,note,birthdays,cloud']














