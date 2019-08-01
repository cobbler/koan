from koan import utils


def test_check_dist():
    res = utils.check_dist()
    assert res in ["debian", "suse", "redhat"]


def test_os_release():
    resname, resnumber = utils.os_release()
    assert resname in ["rhel", "centos", "fedora", "debian", "ubuntu", "suse", "unkown"]
