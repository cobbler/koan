**************
Reinstallation
**************

Cobbler's helper program, koan, can be installed on remote systems.

It can then be used to reinstall systems, as well as it's original purpose of installing virtual machines.

Usage is as follows:

.. code-block:: shell

    koan --server cobbler.example.com --profile profileName
    koan --server cobbler.example.com --system systemName

Koan will then configure the bootloader to reinstall the system at next boot. This can also be used for OS upgrades with
an upgrade kickstart as opposed to a kickstart that specifies a clean install.

