"""
koan = kickstart over a network
general usage functions

Copyright 2006-2008 Red Hat, Inc and Others.
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import os
import random
import tempfile
import traceback
import distro
import urllib.request
import xmlrpc.client
import netifaces
import subprocess
import shutil
import sys
import time
from .cexceptions import InfoException

VIRT_STATE_NAME_MAP = {
    0: "running",
    1: "running",
    2: "running",
    3: "paused",
    4: "shutdown",
    5: "shutdown",
    6: "crashed"
}

VALID_DRIVER_TYPES = ['raw', 'qcow', 'qcow2', 'vmdk', 'qed']


def setupLogging(appname):
    """
    set up logging ... code borrowed/adapted from virt-manager
    """
    import logging.handlers

    dateFormat = "%a, %d %b %Y %H:%M:%S"
    fileFormat = "[%(asctime)s " + appname + \
                 " %(process)d] %(levelname)s (%(module)s:%(lineno)d) %(message)s"
    streamFormat = "%(asctime)s %(levelname)-8s %(message)s"
    filename = "/var/log/koan/koan.log"

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    fileHandler = logging.handlers.RotatingFileHandler(filename, "a",
                                                       1024 * 1024, 5)

    fileHandler.setFormatter(logging.Formatter(fileFormat,
                                               dateFormat))
    rootLogger.addHandler(fileHandler)

    streamHandler = logging.StreamHandler(sys.stderr)
    streamHandler.setFormatter(logging.Formatter(streamFormat,
                                                 dateFormat))
    streamHandler.setLevel(logging.DEBUG)
    rootLogger.addHandler(streamHandler)


def urlread(url):
    """
    to support more distributions, implement (roughly) some
    parts of urlread and urlgrab from urlgrabber, in ways that
    are less cool and less efficient.
    """
    print("- reading URL: %s" % url)
    if url is None or url == "":
        raise InfoException("invalid URL: %s" % url)

    elif url[0:3] == "nfs":
        try:
            ndir = os.path.dirname(url[6:])
            nfile = os.path.basename(url[6:])
            nfsdir = tempfile.mkdtemp(prefix="koan_nfs", dir="/tmp")
            nfsfile = os.path.join(nfsdir, nfile)
            cmd = ["mount", "-t", "nfs", "-o", "ro", ndir, nfsdir]
            subprocess_call(cmd)
            fd = open(nfsfile)
            data = fd.read()
            fd.close()
            cmd = ["umount", nfsdir]
            subprocess_call(cmd)
            return data
        except:
            traceback.print_exc()
            raise InfoException("Couldn't mount and read URL: %s" % url)

    elif url[0:4] == "http":
        try:
            fd = urllib.request.urlopen(url)
            data = fd.read()
            fd.close()
            return data
        except:
            traceback.print_exc()
            raise InfoException("Couldn't download: %s" % url)
    elif url[0:4] == "file":
        try:
            fd = open(url[5:])
            data = fd.read()
            fd.close()
            return data
        except:
            raise InfoException("Couldn't read file from URL: %s" % url)

    else:
        raise InfoException("Unhandled URL protocol: %s" % url)


def urlgrab(url, saveto):
    """
    like urlread, but saves contents to disk.
    see comments for urlread as to why it's this way.
    """
    data = urlread(url)
    fd = open(saveto, "w+b")
    fd.write(data)
    fd.close()


def subprocess_call(cmd, ignore_rc=0):
    """
    Wrapper around subprocess.call(...)
    """
    print("- %s" % cmd)
    rc = subprocess.call(cmd)
    if rc != 0 and not ignore_rc:
        raise InfoException("command failed (%s)" % rc)
    return rc


def subprocess_get_response(cmd, ignore_rc=False, get_stderr=False):
    """
    Wrapper around subprocess.check_output(...)
    """
    print("- %s" % cmd)
    rc = 0
    result = ""
    if get_stderr:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    result, stderr_result = p.communicate()
    rc = p.wait()
    if not ignore_rc and rc != 0:
        raise InfoException("command failed (%s)" % rc)
    if get_stderr:
        return rc, result.decode(), stderr_result.decode()
    return rc, result.decode()


def input_string_or_dict(options, delim=None, allow_multiples=True):
    """
    Older cobbler files stored configurations in a flat way, such that all values for strings.
    Newer versions of cobbler allow dictionaries.  This function is used to allow loading
    of older value formats so new users of cobbler aren't broken in an upgrade.
    """

    if options is None:
        return {}
    elif isinstance(options, list):
        raise InfoException("No idea what to do with list: %s" % options)
    elif isinstance(options, type("")):
        new_dict = {}
        tokens = options.split(delim)
        for t in tokens:
            tokens2 = t.split("=", 1)
            if len(tokens2) == 1:
                # this is a singleton option, no value
                key = tokens2[0]
                value = None
            else:
                key = tokens2[0]
                value = tokens2[1]

            # if we're allowing multiple values for the same key,
            # check to see if this token has already been
            # inserted into the dictionary of values already

            if key in new_dict.keys() and allow_multiples:
                # if so, check to see if there is already a list of values
                # otherwise convert the dictionary value to an array, and add
                # the new value to the end of the list
                if isinstance(new_dict[key], list):
                    new_dict[key].append(value)
                else:
                    new_dict[key] = [new_dict[key], value]
            else:
                new_dict[key] = value

        # dict.pop is not avail in 2.2
        if "" in new_dict:
            del new_dict[""]
        return new_dict
    elif isinstance(options, type({})):
        options.pop('', None)
        return options
    else:
        raise InfoException("invalid input type: %s" % type(options))


def dict_to_string(hash):
    """
    Convert a hash to a printable string.
    used primarily in the kernel options string
    and for some legacy stuff where koan expects strings
    (though this last part should be changed to hashes)
    """
    buffer = ""
    if not isinstance(hash, dict):
        return hash
    for key in hash:
        value = hash[key]
        if value is None:
            buffer = buffer + str(key) + " "
        elif isinstance(value, list):
            # this value is an array, so we print out every
            # key=value
            for item in value:
                buffer = buffer + str(key) + "=" + str(item) + " "
        else:
            buffer = buffer + str(key) + "=" + str(value) + " "
    return buffer


def nfsmount(input_path):
    # input:  [user@]server:/foo/bar/x.img as string
    # output:  (dirname where mounted, last part of filename) as 2-element tuple
    # we have to mount it first
    filename = input_path.split("/")[-1]
    dirpath = "/".join(input_path.split("/")[:-1])
    tempdir = tempfile.mkdtemp(suffix='.mnt', prefix='koan_', dir='/tmp')
    mount_cmd = [
        "/bin/mount", "-t", "nfs", "-o", "ro", dirpath, tempdir
    ]
    print("- running: %s" % mount_cmd)
    rc = subprocess.call(mount_cmd)
    if not rc == 0:
        shutil.rmtree(tempdir, ignore_errors=True)
        raise InfoException("nfs mount failed: %s" % dirpath)
    # NOTE: option for a blocking install might be nice, so we could do this
    # automatically, if supported by virt-install
    print("after install completes, you may unmount and delete %s" % tempdir)
    return (tempdir, filename)


def get_vms(conn):
    """
    Get virtual machines

    @param ? conn
    @return list virtual machines
    """

    vms = []

    # this block of code borrowed from virt-manager:
    # get working domain's name
    ids = conn.listDomainsID()
    for id in ids:
        vm = conn.lookupByID(id)
        vms.append(vm)

    # get defined domain
    names = conn.listDefinedDomains()
    for name in names:
        vm = conn.lookupByName(name)
        vms.append(vm)

    return vms


def find_vm(conn, vmid):
    """
    Extra bonus feature: vmid = -1 returns a list of everything
    This function from Func:  fedorahosted.org/func
    """

    vms = get_vms(conn)
    for vm in vms:
        if vm.name() == vmid:
            return vm

    raise InfoException("koan could not find the VM to watch: %s" % vmid)


def get_vm_state(conn, vmid):
    """
    Returns the state of a libvirt VM, by name.
    From Func:  fedorahosted.org/func
    """
    state = find_vm(conn, vmid).info()[0]
    return VIRT_STATE_NAME_MAP.get(state, "unknown")


def os_release():
    """
    This code detects your os with the distro module and return the name and version. If it is not detected correctly it
    returns "unknown" (str) and "0" (float).
    :returns tuple (str, float)
        WHERE
        str is the name
        int is the version number
    """
    distroname = distro.id()
    distrolike = distro.like()
    version = distro.version()

    redhat = ["centos", "fedora", "rhel"]

    if distroname in redhat or distrolike in redhat:
        if distroname in ["centos", "fedora"]:
            return distroname, float(version)
        else:
            return "redhat", float(version)

    if distroname in ["debian", "ubuntu"]:
        return distroname, float(version)

    if "suse" in distrolike:
        return "suse", float(version)

    return "unknown", 0.0


def uniqify(lst, purge=None):
    temp = {}
    for x in lst:
        temp[x] = 1
    if purge is not None:
        temp2 = {}
        for x in temp.keys():
            if x != purge:
                temp2[x] = 1
        temp = temp2
    return list(temp.keys())


def get_network_info():
    interfaces = {}
    # get names
    inames = netifaces.interfaces()

    for iname in inames:
        mac = netifaces.ifaddresses(iname)[netifaces.AF_LINK][0]['addr']

        if mac == "00:00:00:00:00:00":
            mac = "?"

        try:
            ip = netifaces.ifaddresses(iname)[netifaces.AF_INET][0]['addr']
            if ip == "127.0.0.1":
                ip = "?"
        except:
            ip = "?"

        bridge = 0
        module = ""

        try:
            nm = netifaces.ifaddresses(iname)[netifaces.AF_INET][0]['netmask']
        except:
            nm = "?"

        interfaces[iname] = {
            "ip_address": ip,
            "mac_address": mac,
            "netmask": nm,
            "bridge": bridge,
            "module": module
        }

    # print interfaces
    return interfaces


def connect_to_server(server=None, port=None):
    if server is None:
        server = os.environ.get("COBBLER_SERVER", "")
    if server == "":
        raise InfoException("--server must be specified")

    try_urls = []
    if port is None:
        try_urls = [
            "https://%s:443/cobbler_api" % (server),
            "http://%s:80/cobbler_api" % (server),
        ]
    else:
        try_urls = [
            "https://%s:%s/cobbler_api" % (server, port),
            "http://%s:%s/cobbler_api" % (server, port),
        ]

    for url in try_urls:
        print("- looking for Cobbler at %s" % url)
        server = __try_connect(url)
        if server is not None:
            return server
    raise InfoException("Could not find Cobbler.")


def create_xendomains_symlink(name):
    """
    Create an /etc/xen/auto/<name> symlink for use with "xendomains"-style
    VM boot upon dom0 reboot.
    """
    src = "/etc/xen/%s" % name
    dst = "/etc/xen/auto/%s" % name

    # Make sure symlink does not already exist.
    if os.path.exists(dst):
        print("Could not create %s symlink. File already exists in this "
              "location." % dst)
        return False

    # Verify that the destination is writable
    if not os.access(os.path.dirname(dst), os.W_OK):
        print("Could not create %s symlink. Please check write permissions "
              "and ownership." % dst)
        return False

    # check that xen config file exists and create symlink
    if os.path.exists(src):
        os.symlink(src, dst)
        return True
    else:
        print("Could not create %s symlink, source file %s is "
              "missing." % (dst, src))
        return False


def libvirt_enable_autostart(domain_name):
    import libvirt
    try:
        conn = libvirt.open("qemu:///system")
        conn.listDefinedDomains()
        domain = conn.lookupByName(domain_name)
        domain.setAutostart(1)
    except:
        raise InfoException("libvirt could not find domain %s" % domain_name)

    if not domain.autostart:
        raise InfoException(
            "Could not enable autostart on domain %s." %
            domain_name)


def make_floppy(autoinst):
    (fd, floppy_path) = tempfile.mkstemp(
        suffix='.floppy', prefix='tmp', dir="/tmp")
    print("- creating floppy image at %s" % floppy_path)

    # create the floppy image file
    cmd = "dd if=/dev/zero of=%s bs=1440 count=1024" % floppy_path
    print("- %s" % cmd)
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("dd failed")

    # vfatify
    cmd = "mkdosfs %s" % floppy_path
    print("- %s" % cmd)
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("mkdosfs failed")

    # mount the floppy
    mount_path = tempfile.mkdtemp(suffix=".mnt", prefix='tmp', dir="/tmp")
    cmd = "mount -o loop -t vfat %s %s" % (floppy_path, mount_path)
    print("- %s" % cmd)
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("mount failed")

    # download the autoinst file onto the mounted floppy
    print("- downloading %s" % autoinst)
    save_file = os.path.join(mount_path, "unattended.txt")
    urlgrab(autoinst, save_file)

    # umount
    cmd = "umount %s" % mount_path
    print("- %s" % cmd)
    rc = os.system(cmd)
    if not rc == 0:
        raise InfoException("umount failed")

    # return the path to the completed disk image to pass to virt-install
    return floppy_path


def sync_file(ofile, nfile, uid, gid, mode):
    subprocess.call(['/usr/bin/diff', ofile, nfile])
    shutil.copy(nfile, ofile)
    os.chmod(ofile, mode)
    os.chown(ofile, uid, gid)


def __try_connect(url):
    try:
        xmlrpc_server = xmlrpc.client.ServerProxy(url)
        xmlrpc_server.ping()
        return xmlrpc_server
    except:
        traceback.print_exc()
        return None


def create_qemu_image_file(path, size, driver_type):
    if driver_type not in VALID_DRIVER_TYPES:
        raise InfoException("Invalid QEMU image type: %s" % driver_type)

    cmd = ["qemu-img", "create", "-f", driver_type, path, "%sG" % size]
    try:
        subprocess_call(cmd)
    except:
        traceback.print_exc()
        raise InfoException(
            "Image file create failed: %s" % " ".join(cmd)
        )


def random_mac():
    """
    from xend/server/netif.py
    Generate a random MAC address.
    Uses OUI 00-50-56, allocated to
    VMWare. Last 3 fields are random.
    return: MAC address string
    """
    mac = [0x00, 0x50, 0x56,
           random.randint(0x00, 0x3f),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def generate_timestamp():
    return str(int(time.time()))


def check_version_greater_or_equal(version1, version2):
    ass = version1.split(".")
    bss = version2.split(".")
    if len(ass) != len(bss):
        raise Exception("expected version format differs")
    for i, a in enumerate(ass):
        a = int(a)
        b = int(bss[i])
        if a > b:
            return True
        if a < b:
            return False
    return True


def is_uefi_system() -> bool:
    """
    Helper function to check if the system we are currently running on is being booted by UEFI or a BIOS.

    :return: True if ``/sys/firmware/efi`` exists, otherwise False.
    """
    if os.path.exists("/sys/firmware/efi"):
        return True
    return False


def get_grub2_mkrelpath_executable() -> str:
    """
    Searches through the path for the mkrelpath executable of GRUB2.

    :raises RuntimeError: In case the executable could not be found.
    :return: The path to the executable
    """
    executable_path = ""
    binary_names = ["grub2-mkrelpath", "grub-mkrelpath"]
    for possible_name in binary_names:
        tmp_result = shutil.which(possible_name)
        if tmp_result is not None:
            executable_path = tmp_result
            break
    if not executable_path:
        raise RuntimeError("The executable for making a GRUB2 real path was not found. Tried executable names: \"%s\""
                           % str(binary_names))
    return executable_path


def get_grub_real_path(path: str):
    """
    This function provides a wrapper to get the real path of a file to be able to write this to a grub config file.

    :param path: The path which should be converted.
    :raises FileNotFoundError: In case the path specifed did not exist.
    :raises RuntimeError: In case the executable did return a non-zero exitcode.
    :return: The value of ``path`` or the real path converted by ``grub2-mkrelpath``.
    """
    if not os.path.exists(path):
        raise FileNotFoundError("Path specified did not exist on the filesystem.")
    command_result = subprocess.run(
        [get_grub2_mkrelpath_executable(), path],
        encoding=sys.getdefaultencoding(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    if command_result.returncode != 0:
        raise RuntimeError("Command executed did return non-zero exit code!")
    return command_result.stdout.strip()
