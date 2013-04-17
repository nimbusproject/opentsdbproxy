OpenTSDB Proxy
==============

OpenTSDB is a SSL and Authz gateway for OpenTSDB. It is meant to sit in between
your OpenTSDB installation(s) and tcollector. It provides the following features:

* SSL connections between tcolector and itself
* Check usernames against a Django user database

The idea is that with this proxy, it is practical to use OpenTSDB over the
internet, but still be able to trust the metrics coming in. 

How it works
------------

You must use our [fork of tcollector](https://github.com/nimbusproject/tcollector),
which adds support for ssl connections. If you would also like to authenticate
the metrics sent by tcollector, you need to add a 'user' and a 'password' tag to
your messages. You can either do this by using the onload function in your 
collectors etc/config.py file, or you can use -tg option when starting
tcollector, like so:

    $ tcollector.py -t user=rogerrabbit -t password=toontown

You must also set up opentsdbproxy somewhere. A convenient place is wherever you
have OpenTSDB installed. You can install it with:

   $ pip install https://github.com/nimbusproject/opentsdbproxy/tarball/master

Then you can run it with:

   $ opentsdb-proxy

SSL Cert and Key
----------------

You must provide an SSL cert and key to use opentsdb-proxy. There are lots of
guides on the internet about how to make one. Try this one if you like:

http://www.akadia.com/services/ssh_test_certificate.html

Backends
--------

OpenTSDB supports 4 backends curently:

* mock - for testing
* forwarding - for providing an SSL gateway to OpenTSDB
* mock_django_authz - for testing Django Authorization
* django_authz - for an SSL gateway with Django Authorization

If you are only interested in SSL between your tcollectors and TSDB, forwarding
is a good option, otherwise you will probably want to use django_authz.
django_authz is meant to hook into an existing django application, and to use
it, you only need to provide the path to that application, and the name of the
django settings module that uses. When a message is recieved, opentsdbproxy will
check against Django to see whether the username and password are in its database,
and if they are, the message is forwarded to TSDB.

See opentsdb-proxy --help for more information on options.
