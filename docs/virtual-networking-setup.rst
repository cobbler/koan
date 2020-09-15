************************
Virtual Networking Setup
************************

Notice
######

For Xen and QEMU/KVM virtual machines to be able to get outside access they will need to have a virtual bridge
configured on the virtual host. (If you're using VMware this page won't apply to you)

While "virbr0" should automatically be set up if you are using a newer libvirt, it's not a real bridge and you won't be
able to contact your guests from outside -- it's a private network. So you most likely do NOT want to use virbr0 if you
are doing anything useful. "xenbr0" if you have that, is fine to use.

The following instructions show about how to set up bridging manually which must be done on a host to make things work
as you would expect.

Remember if you have a "xenbr0", you can use that though -- it's a real bridge. If you want something more specific you
can still create your own. xenbr0 is created in most versions of RHEL by xend startup.

Networking
##########

Virtualization networking in Koan uses "bridged" mode. This is so that guests by default can be connected to from the
outside world, which is very important for them to be able to do useful things.

If a network bridge already exists, Koan will be able to use that, though in some cases, you'll have to create your own
bridge in order to get Koan to work. You do this by modifying the network configuration on your virtual host, and then
using the Koan parameter ``--virt-bridge=bridgename``.

(As we mentioned, if you use virbr0, it's a fake bridge, so be aware you won't be able to ssh into your guests...
However koan can use that if you REALLY want to)

Basics
######

The configuration in this section is adapted from `here <http://watzmann.net/blog/2007/04/networking-with-kvm-and-libvirt.html>`_.
We're going to be ignoring the parts in that article about using virt-install as we want to use Koan -- we want to make our
virtualized configurations be managed server side, by Cobbler -- and to take advantage of things that cobbler provides for us,
like syslog setup, templating, remote profile browsing, etc.

So here's the short rundown of what you need to do to create a bridge if you do not already have one. Once you do this
once for each guest, you're set up -- so if you have bare metal profiles for Cobbler set up, it may make sense to make
those profiles set up your bridge at install time as well.

Set up ``/etc/sysconfig/network-scripts/ifcfg-peth0`` to define your physical NIC:

    DEVICE=peth0
    ONBOOT=yes
    BRIDGE=eth0
    HWADDR=XX:XX:XX:XX:XX:XX

Substitute the X's in HWADDR for the mac address of the NIC you'd get from ``/sbin/ifconfig``

Now set up the bridge interface: ``/sbin/sysconfig/network-scripts/ifcfg-eth0``:

    DEVICE=eth0
    BOOTPROTO=dhcp
    ONBOOT=yes
    TYPE=Bridge

As the above link recommends, "You also want to add an iptables rule that allows forwarding of packets on the bridged
physical NIC (otherwise DHCP from your guests won't work)".

    # service iptables start
    # iptables -I FORWARD -m physdev --physdev-is-bridged -j ACCEPT
    # service iptables save

Alternatively, you could also disable iptables (at your own risk).

Now you should be able to use Koan as follows:

.. code-block:: shell

    koan --server=bootserver.example.org --profile=RHEL5-i386 --virt

To force a specific choice, you can use ``--virt-bridge`` and specify the name of any bridge you like. Note that this
must be a /real/ bridge, and not a physical interface. If you use a physical interface things will not work.

.. code-block:: shell

    koan --server=bootserver.example.org --profile=RHEL5-i386 --virt --virt-bridge=peth0

Hopefully that helps address some of the basics around virtual networking setup. The above instructions work for both
Xen and QEMU/KVM.

(If you encounter problems with the above please bring them up on the gitter-chat list)

Network Manager
###############

At the time of writing this (Fedora 10), Network Manager does not support bridging.

You should also set NM_MANAGED=No in the configuration file for your physical interface to disable NetworkManager on
hosts that use it.

(This has the side effect of tricking firefox into offline mode on startup, but we are hopefully talking about servers
here... if this bothers you, go into `about:config` and search for networkmanager. Turn off the firefox network manager
toolkit).
