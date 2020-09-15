*************************
Installing virtual guests
*************************

The main feature of Koan is contact the Cobbler server, learn about a configuration from Cobbler, and make that
virtualized installation happen.  One other feature is [KoanDoesReinstall reinstallation of existing systems] but
perhaps the more important one is how to do virtualized installs.

Koan is its own separate tool, a separate package from Cobbler, that is designed for use with a remote Cobbler server.
(The same folks that work on Cobbler work on Koan and it's available from the same repositories)

.. code-block:: shell

    yum install koan

It is a very small tool and generally does not always need to be updated when Cobbler is updated, but keeping Koan
updated ensures you have all the latest features available. In general, the major release numbers of Cobbler and Koan
should match, but it's not so important if the minor release numbers don't match.

Example of installing a VM using a profile virtually
####################################################

.. code-block:: shell

    koan --server=cobbler.example.org --virt --profile=foo


Example of installing a VM using a system record
################################################

.. code-block:: shell

    koan --server=cobbler.example.org --virt --system=foo

Overrides
#########

Koan is designed to install things as set up in Cobbler to ensure installs are consistent and repeatable.

Often though, users of Koan may not be Cobbler server administrators or may want to install a VM on a test system -- so
they'll want to override some things as stored in Cobbler. Koan allows an extensive system of overrides to tweak what
Cobbler tells us about how a particular Cobbler profile should be installed.

+-------------------+---------------------------------------+---------------------------+
| Flag              | Explanation                           | Example                   |
+===================+=======================================+===========================+
| ``--virt-name``   | name of virtual machine to create     | testmachine               |
+-------------------+---------------------------------------+---------------------------+
| ``--virt-type``   | forces usage of qemu/xen/vmware       | qemu                      |
+-------------------+---------------------------------------+---------------------------+
| ``--virt-bridge`` | name of bridge device                 | virbr0                    |
+-------------------+---------------------------------------+---------------------------+
| ``--virt-path``   | overwrite this disk partition         | `/dev/sda4`               |
+-------------------+---------------------------------------+---------------------------+
| ``--virt-path``   | use this directory                    | `/opt/myimages`           |
+-------------------+---------------------------------------+---------------------------+
| ``--virt-path``   | use this existing LVM volume          | `VolGroup00`              |
+-------------------+---------------------------------------+---------------------------+
| ``--nogfx``       | do not use VNC graphics (Xen only)    | (does not take options)   |
+-------------------+---------------------------------------+---------------------------+

Nearly all of these variables can also be defined and centrally managed by the Cobbler server and are also described in
the Cobbler manpage in depth.
